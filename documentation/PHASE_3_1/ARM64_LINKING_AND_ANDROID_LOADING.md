# Phase 3.1: ARM64 Linking & Android Loading Architecture

## Executive Summary

Translating x86-64 machine code to AArch64 assembly is only half the battle; the generated machine code must be packaged into valid, relocatable ELF shared libraries (`.so`) that satisfy the strict loading constraints of the Android operating system and its Bionic C library runtime.

In Phase 3.1, attempting to run translated code exposed critical linking issues:
1. Unresolved compiler runtime symbols (`__udivti3` for 128-bit division).
2. Dynamic PLT jumps referencing unmapped memory in freestanding execution contexts.
3. PIC relocation violations (`R_AARCH64_ADR_PREL_PG_HI21` on non-PIC symbols).

This document details the toolchain configuration, linker mechanics, symbol resolution strategies, and Bionic runtime constraints required to produce robust Android shared libraries.

---

## Linker Mechanics & Toolchain Configuration

### Toolchain Specification
- **Compiler:** Clang 23.1.4 / LLVM 23.1.4
- **Linker:** LLD 23.1.4 (`ld.lld`)
- **Target Triple:** `aarch64-unknown-linux-android30`
- **ABI Specification:** AAPCS64 (ARM 64-bit Architecture Procedure Call Standard)

### The Command Line Invocation
The shared libraries are linked using the following parameters:
```bash
clang -target aarch64-linux-android30 \
      -nostdlib \
      -shared \
      -Wl,-Bsymbolic \
      -Wl,--gc-sections \
      <fixture>.o <fixture>_dispatch.o guest_cpu.o \
      -o libp3r_<fixture>.so
```

### Deconstructing the Linker Flags

1. `-target aarch64-linux-android30`:
   Specifies the Android API level 30 (Android 11) target. API 30 guarantees modern ELF header layouts and 64-bit Bionic compatibility.

2. `-nostdlib`:
   Excludes the standard host C runtime libraries (`libc`, `libm`, `crtbegin_so.o`, `crtend_so.o`). This ensures the recompiled code is completely freestanding and carries no unwanted dependencies on host system glibc or desktop DLLs.

3. `-shared`:
   Emits an ELF Shared Object (`ET_DYN`) with a `.dynamic` section, symbol hash table (`.gnu.hash`), dynamic symbol table (`.dynsym`), and string table (`.dynstr`).

4. `-Wl,-Bsymbolic`:
   **CRITICAL FLAG.** By default, ELF shared libraries route internal function calls through the Procedure Linkage Table (PLT) to allow symbol interposition by other libraries. In a standalone emulator or low-overhead game runtime, unresolved PLT entries jump to null/unmapped addresses. `-Bsymbolic` instructs the linker to bind internal references to their local definitions directly, eliminating PLT indirection for all internal dispatch and runtime routines.

5. `-Wl,--gc-sections`:
   Instructs the linker to perform dead-stripping on unused code sections, minimizing the final `.so` binary footprint.

6. `-fPIC`:
   All object files (`guest_cpu.o`, `<fixture>.o`, `<fixture>_dispatch.o`) are compiled with Position-Independent Code (`-fPIC`). This enforces that all global variable accesses and branch targets use relative PC-addressing (`ADRP` + `ADD` / `LDR`) rather than absolute 64-bit addresses, preventing text relocations (`DT_TEXTREL`), which are strictly prohibited by Android Bionic.

---

## Resolving 128-bit Integer Division in Freestanding Environments

### The Problem
When x86-64 code executes 64-bit integer division (`idivq` or `divq`), it divides a 128-bit value (`rdx:rax`) by a 64-bit operand. LLVM lowers 128-bit division into compiler runtime helper calls:
- `__udivti3`: Unsigned 128-bit division
- `__umodti3`: Unsigned 128-bit remainder
- `__divti3`: Signed 128-bit division
- `__modti3`: Signed 128-bit remainder

In desktop environments, these functions reside in `libgcc.a` or `libclang_rt.builtins.a`. When compiling with `-nostdlib`, these symbols remained unresolved.

### The Freestanding Solution
To maintain a 100% self-contained binary, we embedded freestanding, bit-accurate 128-bit division algorithms directly into `phase3-poc/android-runtime/guest_cpu.c`:

```c
typedef unsigned __int128 uint128_t;
typedef __int128 int128_t;

uint128_t __udivti3(uint128_t n, uint128_t d) {
    if (d == 0) return 0; // Division by zero guard
    uint128_t q = 0, r = 0;
    for (int i = 127; i >= 0; i--) {
        r = (r << 1) | ((n >> i) & 1);
        if (r >= d) {
            r -= d;
            q |= ((uint128_t)1 << i);
        }
    }
    return q;
}

uint128_t __umodti3(uint128_t n, uint128_t d) {
    if (d == 0) return 0;
    uint128_t r = 0;
    for (int i = 127; i >= 0; i--) {
        r = (r << 1) | ((n >> i) & 1);
        if (r >= d) {
            r -= d;
        }
    }
    return r;
}

int128_t __divti3(int128_t n, int128_t d) {
    int neg = 0;
    if (n < 0) { n = -n; neg = !neg; }
    if (d < 0) { d = -d; neg = !neg; }
    uint128_t q = __udivti3((uint128_t)n, (uint128_t)d);
    return neg ? -((int128_t)q) : (int128_t)q;
}

int128_t __modti3(int128_t n, int128_t d) {
    int neg = 0;
    if (n < 0) { n = -n; neg = 1; }
    if (d < 0) { d = -d; }
    uint128_t r = __umodti3((uint128_t)n, (uint128_t)d);
    return neg ? -((int128_t)r) : (int128_t)r;
}
```

Combined with `-Wl,-Bsymbolic`, LLVM's division calls bind directly to these local functions, resolving all dynamic PLT traps.

---

## Android Bionic Dynamic Loader Compatibility

The Android dynamic linker (`/system/bin/linker64`) enforces several strict security and architectural requirements that our recompilation pipeline respects:

### 1. Zero Text Relocations
Starting with Android 6.0 (Marshmallow), Bionic refuses to load any shared library containing text relocations (`DT_TEXTREL`).
- **Audit:** Inspection of our generated `.so` files confirms zero text relocations. All code segments are strictly read-only and executable (`r-x`).

### 2. Page Alignment Requirements
- **realme 12 Pro+ (Snapdragon 7s Gen 2):** Uses the standard 4KB virtual memory page size (`PAGE_SIZE = 4096`).
- **Android 15 16KB Compatibility:** Android 15 introduces support for 16KB pages. Our linker scripts can specify `-Wl,-z,max-page-size=16384` to ensure future compatibility with 16KB kernel configurations.

### 3. AAPCS64 ABI Adherence
In AAPCS64:
- Function argument 0 is passed in register `X0` (points to `GuestState`).
- Registers `X19`–`X28`, `X29` (`FP`), and `X30` (`LR`) are callee-saved.
- Stack pointer `SP` must remain 16-byte aligned at all external function boundaries.
- Recompiled functions preserve `X19`–`X30` in their prologs/epilogs:
  ```assembly
  str    x30, [sp, #-16]!
  ...
  ldr    x30, [sp], #16
  ret
  ```

---

## Integration with Android Native Applications

In the full game runtime, the recompiled shared library (`libp3r_recompiled.so`) will be loaded via standard JNI or Native Activity mechanisms:

```c
// Native Runtime Loader (Android NDK)
void* handle = dlopen("libp3r_recompiled.so", RTLD_NOW | RTLD_LOCAL);
if (!handle) {
    LOGE("Failed to load recompiled library: %s", dlerror());
    return;
}

// Resolve guest entrypoint
bbr_func_t entry_func = (bbr_func_t)dlsym(handle, "bbr_2013d0");

// Initialize guest CPU state
GuestState guest_state;
bbr_init_guest_state(&guest_state, allocated_stack, stack_size, guest_memory_base);

// Execute native recompiled code
entry_func(&guest_state);
```

This guarantees seamless integration with standard Android NDK game frameworks.

