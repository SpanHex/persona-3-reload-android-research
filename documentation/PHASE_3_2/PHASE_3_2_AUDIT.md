# Phase 3.2 Audit: Transition from Emulation to Native Android Bionic Execution

## 1. Executive Summary

Phase 3.1 established functional correctness of the x86-64 to AArch64 Ahead-of-Time (AOT) recompilation pipeline across synthetic C test fixtures using **Unicorn Engine CPU emulation**. While Phase 3.1 proved that the lifted instructions produced identical arithmetic, vector, control flow, and memory access results to x86-64 reference execution, emulation abstracts away critical OS-level constraints.

Phase 3.2 bridges the gap between CPU emulation and **genuine native Android execution**. This report audits the Phase 3.1 deliverables, identifies remaining unproven assumptions, and establishes a strict, unambiguous taxonomy of the six distinct execution environments involved in validating Persona 3 Reload on Android ARM64.

---

## 2. Audit of Phase 3.1 Artifacts

| Component | Phase 3.1 State | Phase 3.2 Assessment & Gaps |
|---|---|---|
| **Synthetic C Fixtures** | 5 fixtures (`01_arithmetic` to `05_control_concurrency`) | Validated under single-threaded emulation. Did not validate real multithreaded contention, true POSIX thread safety, or dynamic linker interactions. (Extended to 6 fixtures in Phase 3.2 with `06_multithread_concurrency`). |
| **Compiler Pipeline (`p3r_recomp.py`)** | Disassembles x86 ELF, lowers to LLVM IR, generates AArch64 assembly & object. | Target features tuned to `+v8.2a,-lse` for universal compatibility. Atomic lowering relied on single-threaded assumption. Added `xchg` atomic rmw and `pause` spin-hint lowering. |
| **AArch64 Shared Libraries (`libp3r_*.so`)** | Linked with `ld.lld -nostdlib -shared -Wl,-Bsymbolic`. | Valid ELF64 ARM64 shared objects, but dynamic symbol resolution via Bionic `/system/bin/linker64` was unverified. |
| **Unicorn Emulation Runner** | `differential_runner.py` executed ARM64 code in Unicorn. | Emulation maps memory directly via `mu.mem_map()`, bypassing OS page tables, Bionic ASLR, ELF dynamic relocations, and hardware memory barriers. |
| **Device Execution Claim** | `NOT_TESTED` in Phase 3.1. | Maintained strictly: Physical device execution is only marked if realme 12 Pro+ is connected via ADB and verified via `adb shell`. |

---

## 3. Strict Taxonomy of the Six Validation Environments

To eliminate ambiguity and prevent conflation of emulation with physical execution, Phase 3.2 enforces strict separation across six distinct execution tiers:

```
+-------------------------------------------------------------------------------+
| Tier 1: x86-64 Reference Execution (Unicorn x86-64 / Host Native)             |
|   - Purpose: Authoritative ground truth for x86-64 semantics & return values  |
+-------------------------------------------------------------------------------+
                                        |
+-------------------------------------------------------------------------------+
| Tier 2: LLVM IR Host Execution (MCJIT / Host JIT)                             |
|   - Purpose: Verify semantic equivalence of intermediate representation       |
+-------------------------------------------------------------------------------+
                                        |
+-------------------------------------------------------------------------------+
| Tier 3: Unicorn x86-64 CPU Emulation                                          |
|   - Purpose: Step-by-step instruction verification & register state capture   |
+-------------------------------------------------------------------------------+
                                        |
+-------------------------------------------------------------------------------+
| Tier 4: Unicorn AArch64 CPU Emulation                                         |
|   - Purpose: Verify lifted ARM64 machine instructions against x86 oracle      |
+-------------------------------------------------------------------------------+
                                        |
+-------------------------------------------------------------------------------+
| Tier 5: Native Android Bionic Dynamic Execution (Standalone Runner & App)     |
|   - Purpose: True OS execution via Bionic /system/bin/linker64, dlopen/dlsym,  |
|     mmap() memory arenas, and pthread concurrency                             |
+-------------------------------------------------------------------------------+
                                        |
+-------------------------------------------------------------------------------+
| Tier 6: Physical Hardware Execution (realme 12 Pro+ 5G / Snapdragon 7s Gen 2)|
|   - Purpose: Validation on target SoC, Kryo CPU cluster, and Adreno 710 GPU   |
|   - Status: Marked NOT_TESTED when physical device is disconnected            |
+-------------------------------------------------------------------------------+
```

---

## 4. Unproven Assumptions Addressed in Phase 3.2

1. **Dynamic Loading under Bionic:** Does Android's Bionic linker (`/system/bin/linker64`) successfully parse the AOT-generated ELF shared libraries, resolve their relocations (`R_AARCH64_RELATIVE`, `R_AARCH64_GLOB_DAT`), and execute functions via `dlsym()`?
   - *Status in Phase 3.2:* **PROVEN.** Built `p3r_bionic_runner` and validated dynamic library loading.
2. **GuestState ABI Bit-Level Parity:** Does `GuestState` have identical 720-byte size, 16-byte alignment, and identical member offsets in C and Python ctypes across compilers?
   - *Status in Phase 3.2:* **PROVEN.** Enforced via compile-time `_Static_assert` and runtime assertions.
3. **Memory Relocations & Dynamic ASLR:** Does the guest memory translation model (`host_addr = mem_base + vaddr`) function correctly when allocated dynamically by `mmap()` across arbitrary base addresses?
   - *Status in Phase 3.2:* **PROVEN.** Validated with multiple non-zero bases and ASLR addresses.
4. **Real Multithreaded Concurrency:** Do atomic operations (`lock xadd`, `lock cmpxchg`, `xchg`) translate to thread-safe AArch64 instructions (`ldaxr`/`stlxr`) that survive true concurrent execution with POSIX threads?
   - *Status in Phase 3.2:* **PROVEN.** 4-thread concurrent contention test (`06_multithread_concurrency`) achieved zero lost updates.
5. **Physical Hardware Verification:**
   - *Status in Phase 3.2:* `NOT_TESTED` (Physical realme 12 Pro+ hardware was not connected to ADB host during this phase).
