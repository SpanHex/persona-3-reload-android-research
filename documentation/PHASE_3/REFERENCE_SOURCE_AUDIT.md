# Milestone 1: Exhaustive Reference Source Audit of Bloodborne AOT Compiler & Android Runtime

**Document ID:** `P3R-DOC-P3-001`  
**Research Phase:** Phase 3: AOT Recompilation Proof of Concept  
**Primary Reference Repositories:**
- `ducvd89/Bloodborne-android-rebuild-tool` (`commit 6ebb33b0c729a3942fddaa03965360c699d7d900`, branch `main`)
- `ducvd89/Bloodborne-Android` (`commit f241353e36f46bf183806acd7b79222afff2fd2f`, branch `master`)
- `shadps4-emu/shadPS4` (`commit 2183807e592b36d4440384878165b43d930c1dee`, branch `main`)

---

## 1. Executive Summary & Audit Objectives

Milestone 1 performs a component-by-component, line-by-line engineering audit of the upstream Bloodborne Ahead-of-Time (AOT) compilation toolchain (`bb-recomp`) and native Android execution runtime. 

The goal of this audit is to rigorously delineate **generic, reusable compiler infrastructure** from **Bloodborne-specific heuristics and hardcoded assumptions**, establishing the exact architectural modifications required to compile and execute original synthetic x86-64 test fixtures and, ultimately, a general-purpose PS4 title like Persona 3 Reload.

---

## 2. Component-by-Component Source Code Audit

### 2.1 Static Discovery & Control-Flow Analysis (`src/discover.cpp`, `src/jumptable.cpp`, `src/fde_scan.cpp`)

| Component | Source Path & Lines | Implementation Details | Reusability vs. Hardcoded Coupling |
|---|---|---|---|
| **FDE Scanner** | `src/fde_scan.cpp`<br>`L1–L105` | Scans `.eh_frame` program headers (`PT_GNU_EH_FRAME = 0x6474e550`) for DWARF Call Frame Information. Rapidly identifies function starts (kind 0) and lengths without disassembly. | **GENUINELY REUSABLE**.<br>Standard DWARF parsing. Works on any ELF/SELF compiled with Clang/GCC with unwinding tables enabled. |
| **Iterative Discovery** | `src/discover.cpp`<br>`L49–L181` (`discoverEntries`) | Runs up to 16 iterative lifting rounds over a frontier of functions. Discovers branch/call/LEA targets outside unit boundaries, resolves landing pads, and creates pseudo-functions (kind 3). | **GENUINELY REUSABLE**.<br>Generic fixpoint algorithm. However, does not inspect high-level C++ reflection or dynamic interface tables (e.g., UE4 `UClass`). |
| **Missing Entry Ingestion** | `src/discover.cpp`<br>`L26–L47` (`readEntryList`) | Parses text log files containing missing virtual addresses (`aot-misses.log`), strips `#`, `miss `, and `+`, and seeds the discovery frontier via `--extra-entries`. | **GENUINELY REUSABLE**.<br>Critical feedback mechanism for closing undiscovered control flow gaps. |
| **Jump Table Resolver** | `src/jumptable.cpp`<br>`L1–L199` | Disassembles switch patterns (`jmp [rip + reg*8 + disp]`), inspects `.rodata` tables, and calculates case destination labels. | **GENUINELY REUSABLE**.<br>Handles standard Clang/LLVM switch lowering patterns. |

---

### 2.2 Instruction Lifting & Intermediate Representation (`src/lifter.cpp`)

- **Exact Path:** `src/lifter.cpp` (`L1–L888`)
- **Core Mechanism:** Leverages FEXCore's `OpcodeDispatcher` to decode x86-64 machine instructions into FEX Static Single Assignment (SSA) IR.
- **Instruction Support:**
  - Standard x86-64 integer arithmetic, bitwise, shift, rotates, logical operations.
  - Full System V AMD64 register file (`RAX` through `R15`, flags NZCV, `RSP`, `RBP`, `RIP`).
  - Memory addressing modes (SIB, disp32, RIP-relative).
  - Segment register overrides: `fs:` and `gs:`. (Bloodborne uses `gs:` for thread-local storage, which `bb_prepare` remaps).
- **Hardcoded Assumptions:**
  - In `src/lifter.cpp`, the lift base defaults to `0x3a7700000000` (relocated in commit `c58a088` from `0x200000000` to prevent collisions with 64-bit immediate constants).
  - Assumes a flat unified 39-bit virtual address space.

---

### 2.3 LLVM IR Lowering & Opcode Coverage (`src/lower_llvm.cpp`, `src/lower_ops.cpp`, `src/lower_vector.cpp`)

#### Scalar Operations (`src/lower_ops.cpp`, 126 Opcodes)
- **Lines 13–32 (`sdivSafe`, `udivSafe`):** Handles x86 division semantics on ARM64 hardware:
  - On x86, division by zero triggers `#DE` (Divide Error interrupt), and `INT_MIN / -1` triggers overflow fault.
  - On ARM64, `sdiv` by zero yields `0`, and `INT_MIN / -1` yields `INT_MIN`.
  - The lowering pipeline synthesizes explicit conditional selects (`B.CreateSelect`) to enforce correct x86 wrapping and prevent LLVM undefined behavior.
- **Lines 46–57 (`loadVal` Volatile Spin-Waits):** Enforces `volatile` memory loads for loops lacking stores, atomics, or function calls (commit `ef1a331`), preventing LLVM from hoisting spin-wait reads outside loops.
- **Supported Opcode Families:** `OP_ADD`, `OP_SUB`, `OP_MUL`, `OP_UMUL`, `OP_SMULL`, `OP_UMULL`, `OP_DIV`, `OP_UDIV`, `OP_AND`, `OP_OR`, `OP_XOR`, `OP_LSHL`, `OP_LSHR`, `OP_ASHR`, `OP_ROR`, `OP_POPCOUNT`, `OP_FINDLSB`, `OP_CYCLECOUNTER` (`rdtsc`).

#### Vector & SIMD Operations (`src/lower_vector.cpp`, 217 Opcodes)
- **Supported SIMD Extensions:**
  - SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2 (128-bit vector arithmetic, packed float/double, dot products, blends, pack/unpack).
  - Basic AVX (128-bit and 256-bit floating point math split into 128-bit low/high halves).
- **Unsupported Instructions in AOT Pipeline:**
  - **AVX2 256-bit Integer Vector Instructions:** Unhandled in `lower_vector.cpp` (not needed for PS4 Jaguar binaries!).
  - **FMA3 / FMA4:** Unhandled (not present on PS4 Jaguar CPU).
  - **x87 Legacy Floating-Point Stack (`fld`, `fstp`, `fadd`):** Stubs trigger unsupported traps (`BBR_TRAP_UNSUPPORTED`).
  - **Privileged / Ring 0 Opcodes:** `in`, `out`, `cli`, `sti`, `invlpg` trigger traps.

---

### 2.4 Code Generation & Optimization (`src/codegen.cpp`, `src/compile.cpp`)

- **Target Triple:** Explicitly configured as `aarch64-unknown-linux-android30` (`src/codegen.cpp` line 43).
- **Target Features:** `+v8.2a,+lse,+crc,+fp-armv8,+neon` (line 54).
- **Relocation Model:** `Reloc::PIC_` (Position Independent Code).
- **Multi-Threaded Sharding (`src/compile.cpp`):**
  - Shards compilation across **64 independent ELF object files** (`game.000.o` ... `game.063.o`).
  - Emits in-memory using `legacy::PassManager` and `raw_svector_ostream`.
- **Dirty Unit Tracking (`bbr_dirty`):**
  - Inserts dirty unit test at the beginning of each unit (`src/lower_llvm.cpp` line 720):
    ```c
    if (__builtin_expect(bbr_dirty[i], 0)) { bbr_dirty_entry(s, vaddr); return; }
    ```
  - Enables taking a unit out of service when hooked/patched without modifying executable text pages (avoiding Android SELinux `execmod`).

---

### 2.5 Binary Ingestion & Bloodborne-Specific Hardcoding (`shared/prepare/bb_prepare.cpp`, `src/elf_image.cpp`)

This is the **most tightly coupled component** in the upstream repository:
1. **Game Hash Enforcement (`shared/prepare/bb_prepare.cpp` line 61–64):**
   ```cpp
   if (!game_check_skipped()) {
       std::string hash = sha256_hex(view(boot.image));
       if (auto found = game_problem(game, hash)) raise("prepare.GameCheckError", game_explain(*found));
   }
   ```
   Directly computes the SHA-256 of `eboot.bin` and rejects any binary that is not Bloodborne v1.09!
2. **Hardcoded Module Addresses (`bb_prepare.cpp`, `docs/RECOMP_ABI.md` line 68):**
   - Statically maps `libc.prx` at `+0x56e0000`.
   - Statically maps `libSceFios2.prx` at `+0x57c0000`.
3. **Sony-Specific Dynamic Tags:**
   - Relocation parsing (`bb_prepare.cpp` lines 82–120) expects Sony Orbis dynamic tags:
     `DT_SCE_RELA` (`0x61000029`), `DT_SCE_RELASZ` (`0x6100002d`), `DT_SCE_PLTRELA` (`0x6100002f`), `DT_SCE_PLTRELASZ` (`0x61000031`).
   - A standard Linux x86-64 ELF uses standard ELF dynamic tags (`DT_RELA=7`, `DT_RELASZ=8`, `DT_JMPREL=23`). Feeding an ordinary Linux ELF directly into `bb-prepare` causes immediate failure!

---

### 2.6 Android Native Runtime (`cpu/guest_cpu_aot.cpp`, `cpu/guest_cpu_atomics.h`)

1. **Strict AOT Execution Model (`guest_cpu_aot.cpp` lines 1–10):**
   - Loads `libbbaot.so` via `dlopen()`.
   - Resolves `bbr_units[]`, `bbr_unit_count`, `bbr_image_hash`, `bbr_abi_version`.
   - **Zero JIT or interpreter fallback.**
2. **Unit Dispatcher (`Lookup(offset)` lines 224–233):**
   - Open-addressing hash table using the Golden Ratio multiplier `0x9E3779B1u`.
   - Provides sub-nanosecond dispatch for indirect branches.
3. **Missing Function Handling (`NoteMiss()` lines 454–470):**
   - If an indirect call target is missing from `bbr_units[]` and fails `GranularEntry()`:
   - Appends virtual address to `logs/aot-misses.log`.
   - Dumps guest return address backtrace.
   - Halts the process with `STOP: AOT: native code is missing an entry at +0x...` via `_exit(21)`.
4. **Engine Panic Pattern Check (`guest_cpu_aot.cpp` line 428):**
   - Hardcoded check for FromSoftware's **Dantelion2** engine `DL_PANIC` pattern (`movl $0xdeadba, 0x0`).
5. **Unaligned Atomics Emulation (`cpu/guest_cpu_atomics.h`):**
   - Traps ARM64 `SIGBUS` caused by unaligned LSE atomics.
   - Emulates LDADD, CAS, SWP byte-wise under a global mutex and resumes execution.

---

## 3. Systematic Answers to the 12 Audit Questions

### 1. What functionality is genuinely reusable?
- The FEXCore instruction lifting frontend (`lifter.cpp`).
- The LLVM IR lowering logic and AArch64 PIC code generator (`lower_llvm.cpp`, `lower_ops.cpp`, `lower_vector.cpp`, `codegen.cpp`).
- The DWARF `.eh_frame` FDE scanner and exception unwinding analyzer (`fde_scan.cpp`, `eh_frame.cpp`).
- The iterative discovery engine and jump table analyzer (`discover.cpp`, `jumptable.cpp`).
- The Recomp ABI v2 specification, `GuestState` layout, and callee-saved register optimizations (`docs/RECOMP_ABI.md`).
- The `SIGBUS` unaligned atomic handler (`guest_cpu_atomics.h`).
- The Bionic POSIX threading, memory mapping, and AAudio shims (`src/runtime_*.c`).

### 2. What functionality is hardcoded for Bloodborne?
- Game SHA-256 integrity verification (`bb_prepare.cpp`).
- Hardcoded module placement offsets (`+0x56e0000` for libc, `+0x57c0000` for fios2).
- Dantelion2 engine panic pattern detection (`DL_PANIC` `0xdeadba`).
- 45 game-specific patch variants in `variants/` (60 FPS pacer, Havok timestep, FMOD redirects).
- CRT startup routine at `image + 0x20`.
- Sony Orbis dynamic relocation tag parsing (`DT_SCE_RELA` vs standard `DT_RELA`).

### 3. What assumptions does the compiler make about executable layout?
- The binary is mapped at base address `0x3a7700000000` within a 39-bit virtual address space.
- The binary is a Position-Independent Executable (PIE) with continuous code segments.
- Page alignment is 16 KB (`0x4000`), matching PS4 and modern Android kernels.

### 4. What x86-64 instruction families are supported?
- Complete baseline x86-64 integer arithmetic, bit manipulation (BMI1), shifts, rotates, and logical operations.
- Full SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2 (128-bit vector math).
- Basic AVX (split into 128-bit halves).
- SIB and RIP-relative memory addressing.
- Atomics: `LOCK CMPXCHG`, `LOCK XADD`, `LOCK BTS/BTR/BTC`, `MFENCE`, `SFENCE`, `LFENCE`.

### 5. What instructions are unsupported?
- AVX2 256-bit integer operations (unhandled in `lower_vector.cpp`).
- FMA3 / FMA4 fused multiply-add.
- Legacy x87 80-bit floating-point instructions (`fld`, `fstp`, `fadd`).
- Privileged system instructions (`in`, `out`, `cli`, `sti`, `invlpg`).

### 6. How are function boundaries discovered?
- Primary: DWARF `.eh_frame` FDE entries (`fde_scan.cpp`).
- Secondary: Relocation pointers (`.rela.dyn`, `.rela.plt`) pointing into code.
- Tertiary: Iterative 16-round branch target collection (`CALL`, `JMP`, `Jcc`, `LEA`).
- Quaternary: Offline feedback via `logs/aot-misses.log` fed into `--extra-entries`.

### 7. How are indirect calls handled?
- Indirect calls (`call rax`) are compiled as dispatch queries against `bbr_units[]` via `Lookup(offset)` in `guest_cpu_aot.cpp`.
- If found, execution transfers directly to the translated unit `bbr_<vaddr>(GuestState*)`.
- If missing, it checks `GranularEntry()`. If unhandled, it triggers `NoteMiss()` and aborts.

### 8. How are relocations resolved?
- Base-relative relocations (`R_X86_64_RELATIVE` / PS4 kind 8) are applied directly to image memory.
- Jump slot relocations (`R_X86_64_JUMP_SLOT`) are mapped to host function stubs.
- In translated AArch64 code, memory references within the image are relocated dynamically against `bbr_image_base`.

### 9. How are generated functions registered?
- Functions are exported in a master sorted array `bbr_units[]` containing `{ uint64_t vaddr; void (*fn)(GuestState*); }`.
- Accompanied by `bbr_unit_count`, `bbr_image_hash`, `bbr_abi_version=2`, `bbr_dirty[]`, and `bbr_funcs[]`.

### 10. How does the Android runtime dispatch to translated functions?
- Initial entry is called via `guest_cpu_call(entry_vaddr, s)` on the main thread.
- Unit-to-unit direct calls execute as direct native ARM64 function calls (`bl` / `b`).
- Indirect branches query the open-addressing hash table `Lookup(target)` in `guest_cpu_aot.cpp`.

### 11. What happens when a function is missing?
- In Bloodborne v2.0.0 (strict mode), the runtime does NOT fall back to JIT.
- `NoteMiss()` logs the missing offset and guest backtrace to `logs/aot-misses.log`.
- Execution immediately terminates with `STOP: AOT: native code is missing an entry at +0x...` (`_exit(21)`).

### 12. What assumptions exist about stack layout, registers, TLS, exceptions, and memory mapping?
- **Stack:** Each thread has a dedicated 4 MB stack; RSP is 16-byte aligned before calls; System V red zone (128 bytes) is preserved.
- **Registers:** SysV callee-saved registers (`rbx, rbp, r12-r15`) remain in host ARM64 registers across calls; caller-saved registers are restored from stack.
- **TLS:** Thread-local storage is accessed via `gs:` base offset stored in `GuestState`.
- **Exceptions:** DWARF unwinding tables (`.eh_frame`) map landing pads as sub-unit entries.
- **Memory Mapping:** Requires anonymous memory mapping (`mmap`) below 1 TiB (typically at `0x3a7700000000`).

---

## 4. Architectural Requirements for the Phase 3 Proof of Concept

Based on this audit, our Phase 3 Proof of Concept (`phase3-poc`) must:
1. **Decouple from `bb_prepare.cpp`:** Avoid requiring Sony-specific dynamic relocation tags or Bloodborne SHA-256 hashes.
2. **Build a Clean-Room POC Compiler (`phase3-poc/compiler`):**
   - Parse standard x86-64 ELF fixtures or raw instruction buffers.
   - Implement function discovery for direct and indirect targets.
   - Lower to LLVM IR matching the Recomp ABI v2 `void bbr_<vaddr>(GuestState* s)` convention.
   - Compile to native AArch64 ELF objects via LLVM (`llvmlite` TargetMachine with `aarch64-unknown-linux-android30`).
3. **Build a Native Execution Verification Runtime (`phase3-poc/android-runtime`):**
   - Allocate `GuestState`, setup registers and stack.
   - Dispatch to recompiled units.
   - Verify argument passing, return values, arithmetic, indirect calls, and memory access.
