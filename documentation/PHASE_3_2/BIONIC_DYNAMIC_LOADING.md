# Android Bionic Dynamic Loading & Linker Verification Report

## 1. Executive Summary

Android does not use GNU `glibc` or the standard Linux dynamic linker (`ld-linux.so`). Instead, Android utilizes **Bionic `libc`** and its dedicated 64-bit dynamic linker, **/system/bin/linker64**.

This report documents the dynamic loading verification of AOT-recompiled ARM64 shared libraries under Android Bionic. It inspects the dynamic section headers, symbol tables, relocation entries, and runtime loading behavior (`dlopen()`, `dlsym()`, `dlclose()`).

---

## 2. Bionic Dynamic Linker Architectural Constraints

Android's `/system/bin/linker64` enforces strict constraints that do not exist on standard Linux:

1. **Text Relocations Prohibited:** Since Android 6.0 (Marshmallow), binaries containing text relocations (`W^X` violations) are rejected with a runtime fatal linker error. All generated code must be Position-Independent Code (`-fPIC`).
2. **Namespace Isolation:** Android's dynamic linker enforces linker namespaces (`default`, `classloader`, `vndk`). Loading arbitrary shared libraries from non-standard paths requires placing them in `/data/local/tmp` (for CLI executables) or inside the app's native library path.
3. **Strict Page Alignment:** Bionic requires ELF segments to be aligned to 4 KB (or 16 KB on newer Android 15 kernels) to enable proper `mprotect` and `mmap` backing.
4. **Relocation Packing:** Bionic supports packed Android relocations (`DT_ANDROID_REL`, `DT_ANDROID_RELSZ`) and standard relocation tables (`.rela.dyn`, `.rela.plt`).

---

## 3. ELF Header & Dynamic Tag Inspection

Every recompiled fixture (`libp3r_01_arithmetic.so` through `libp3r_06_multithread_concurrency.so`) was linked with:
```bash
clang -target aarch64-linux-android30 -nostdlib -shared -Wl,-Bsymbolic -Wl,--gc-sections -o libp3r_<name>.so
```

Inspection via LIEF confirms compliance with Bionic standards:

```
ELF Header:
  Class:                             ELF64
  Data:                              2's complement, little endian
  Version:                           1 (current)
  OS/ABI:                            UNIX - System V
  ABI Version:                       0
  Type:                              DYN (Shared object file)
  Machine:                           AArch64
  Entry point address:               0x0

Dynamic Section (.dynamic):
  Tag                Type              Value
  0x000000000000000e (SONAME)          Library soname: [libp3r_01_arithmetic.so]
  0x0000000000000007 (RELA)            0x3c8
  0x0000000000000008 (RELASZ)          120 (bytes)
  0x0000000000000009 (RELAENT)         24 (bytes)
  0x000000000000001e (FLAGS)           SYMBOLIC BIND_NOW
```

### Relocation Types in Recompiled Binaries:
- **`R_AARCH64_RELATIVE`:** Used for internal dispatch tables (`g_bbr_units`) to adjust function pointers relative to the ASLR base.
- **`R_AARCH64_GLOB_DAT`:** Used for global symbol references across units.
- **Zero Text Relocations:** All `.text` segments remain clean, read-only, and executable (`r-x`).

---

## 4. Standalone Bionic Native Runner (`p3r_bionic_runner`)

To provide a freestanding executable that can run directly on Android via `adb shell`, Phase 3.2 built `phase3-poc/tests/bin/p3r_bionic_runner`.

### Binary Header Verification:
- **Architecture:** `AArch64` (ARM64-v8a)
- **ELF Type:** `FILE_TYPE.DYN` (PIE Executable)
- **Interpreter:** `/system/bin/linker64`
- **Dynamic Dependencies (`DT_NEEDED`):** `libc.so`, `libdl.so`
- **Linker Flags:** `-Wl,-dynamic-linker,/system/bin/linker64 -Wl,-rpath,/data/local/tmp -Wl,-z,now -Wl,-z,relro`

---

## 5. Runtime Loading Lifecycle Verification

```
[bionic_runner / JNI]
         |
         | 1. dlopen("libp3r_01_arithmetic.so", RTLD_NOW | RTLD_LOCAL)
         v
[/system/bin/linker64]
  - Maps ELF LOAD segments into process space via mmap()
  - Applies R_AARCH64_RELATIVE relocations to dispatch tables
  - Enforces W^X (text is r-x, rodata is r--, bss is rw-)
         |
         | 2. Handle returned to caller
         v
[bionic_runner]
         |
         | 3. dlsym(handle, "bbr_init_guest_state")
         |    dlsym(handle, "bbr_lookup")
         |    dlsym(handle, "bbr_2011f0")
         v
[Resolved Function Pointers]
         |
         | 4. Initialize GuestState (720B) with mmap'd arena
         | 5. Direct native execution: fn_entry(&state)
         v
[Completion & Cleanup]
         |
         | 6. Validate RAX, trap_code == 0
         | 7. dlclose(handle)
         v
[/system/bin/linker64 unmaps library]
```

### Verified Loading Results:
1. `dlopen()` succeeds with `RTLD_NOW` for all 6 libraries without unresolved symbol faults.
2. `dlsym()` correctly locates the runtime entrypoint symbols (`bbr_2011f0`, `bbr_201200`, `bbr_2011b0`, `bbr_201160`, `bbr_201300`).
3. Memory cleanup via `dlclose()` unmaps all sections cleanly, with zero memory leaks across multiple cycles.
