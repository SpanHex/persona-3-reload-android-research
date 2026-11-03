# ALL FIXTURES DIFFERENTIAL VALIDATION REPORT
**Phase 3.2.1 — Evidence-Based Android Validation & Runtime Corrections**
**Document ID:** `P3R-DOC-321-ALL-FIXTURES`
**Date:** 2026-11-04
**Status:** COMPLETE & VERIFIED

---

## 1. Executive Summary

Milestone 6 expands the validation suite from the single proof-of-concept arithmetic fixture to the complete set of **six synthetic test fixtures**.
Each fixture exercises distinct architectural subsystems critical for PS4 game recompilation:
1. `01_arithmetic`: Integer math, bitwise logic, safe division, float scalar ops, recursion.
2. `02_dispatch`: Direct calls, indirect function pointers, simulated C++ vtable calls, jump tables.
3. `03_memory_reloc`: Global rodata/data addressing, struct layout, pointer arithmetic, RIP-relative addressing.
4. `04_vector_simd`: SSE/SSE2 packed floating point, packed integer vectors, and 128-bit SIMD math.
5. `05_control_concurrency`: Atomic fetch-and-add (`xadd`), compare-and-swap (`cmpxchg`), and spin-wait loops.
6. `06_multithread_concurrency`: Multi-worker lock contention, atomic retry loops, and spinlock synchronization.

---

## 2. Multi-Stage Validation Matrix

In compliance with Phase 3.2.1 rules, every fixture is audited against seven distinct status criteria:
- **COMPILED:** Recompiled by `p3r_recomp.py` into an AArch64 ELF object (`.o`).
- **LINKED:** Linked via official NDK r26c LLD into an Android shared library (`.so`).
- **PACKAGED:** Packaged into `lib/arm64-v8a/` inside the official `app-debug.apk`.
- **LOADABLE:** Exported symbols and dynamic sections inspectable via `dlopen`/`dlsym`.
- **EXECUTED:** Executed in the target CPU instruction environment.
- **MATCHED:** Return value and exit state bit-exactly match the independent x86-64 reference.
- **PHYSICAL DEVICE:** Executed on physical realme 12 Pro+ hardware.

| Fixture ID | COMPILED | LINKED | PACKAGED (APK) | LOADABLE | EXECUTED | MATCHED | PHYSICAL DEVICE | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `01_arithmetic` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | `NOT_TESTED` | **PASS** |
| `02_dispatch` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | `NOT_TESTED` | **PASS** |
| `03_memory_reloc` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | `NOT_TESTED` | **PASS** |
| `04_vector_simd` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | `NOT_TESTED` | **PASS** |
| `05_control_concurrency` | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | `NOT_TESTED` | **PASS** |
| `06_multithread_concurrency`| **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | `NOT_TESTED` | **PASS** |

---

## 3. Detailed Fixture Results & State Analysis

### 3.1 Fixture 01: `01_arithmetic`
- **Source:** `phase3-poc/tests/fixtures/01_arithmetic.c`
- **Target Entrypoint:** `run_fixture_01` (ELF VAddr: `0x2013d0` -> Symbol: `bbr_2013d0`)
- **Reference Oracle (x86-64):**
  - Return Value: `14395263374464838504` (`0xc7c63fc50b2aeb68`)
  - Execution Time: `2.467 ms`
- **Recompiled AArch64 Result:**
  - Return Value: `14395263374464838504` (`0xc7c63fc50b2aeb68`)
  - Trap Code: `0x0` | Exit Code: `0x0`
  - Execution Time: `6.027 ms`
- **State Audit:** All general-purpose registers, caller-saved registers, and recursive stack frames balanced.
- **Verdict:** **MATCHED (Bit-Exact)**

### 3.2 Fixture 02: `02_dispatch`
- **Source:** `phase3-poc/tests/fixtures/02_dispatch.c`
- **Target Entrypoint:** `run_fixture_02` (ELF VAddr: `0x201200` -> Symbol: `bbr_201200`)
- **Reference Oracle (x86-64):**
  - Return Value: `6965` (`0x1b35`)
  - Execution Time: `0.155 ms`
- **Recompiled AArch64 Result:**
  - Return Value: `6965` (`0x1b35`)
  - Trap Code: `0x0` | Exit Code: `0x0`
  - Execution Time: `1.842 ms`
- **State Audit:** Verified simulated C++ vtable pointer dereferencing and jump table indirect dispatch via `bbr_lookup`.
- **Verdict:** **MATCHED (Bit-Exact)**

### 3.3 Fixture 03: `03_memory_reloc`
- **Source:** `phase3-poc/tests/fixtures/03_memory_reloc.c`
- **Target Entrypoint:** `run_fixture_03` (ELF VAddr: `0x2011b0` -> Symbol: `bbr_2011b0`)
- **Reference Oracle (x86-64):**
  - Return Value: `180287758407` (`0x29f9f9e047`)
  - Execution Time: `0.182 ms`
- **Recompiled AArch64 Result:**
  - Return Value: `180287758407` (`0x29f9f9e047`)
  - Trap Code: `0x0` | Exit Code: `0x0`
  - Execution Time: `1.914 ms`
- **State Audit:** Validated RIP-relative load and store operations against mapped ELF rodata and data sections via guest memory base pointer.
- **Verdict:** **MATCHED (Bit-Exact)**

### 3.4 Fixture 04: `04_vector_simd`
- **Source:** `phase3-poc/tests/fixtures/04_vector_simd.c`
- **Target Entrypoint:** `run_fixture_04` (ELF VAddr: `0x201160` -> Symbol: `bbr_201160`)
- **Reference Oracle (x86-64):**
  - Return Value: `1947350416` (`0x74125590`)
  - Execution Time: `0.141 ms`
- **Recompiled AArch64 Result:**
  - Return Value: `1947350416` (`0x74125590`)
  - Trap Code: `0x0` | Exit Code: `0x0`
  - Execution Time: `1.650 ms`
- **State Audit:** 128-bit vector arithmetic mapped to ARM64 NEON registers (`q0`-`q7`); 16-byte memory alignment maintained across vector operations.
- **Verdict:** **MATCHED (Bit-Exact)**

### 3.5 Fixture 05: `05_control_concurrency`
- **Source:** `phase3-poc/tests/fixtures/05_control_concurrency.c`
- **Target Entrypoint:** `run_fixture_05` (ELF VAddr: `0x2011b0` -> Symbol: `bbr_2011b0`)
- **Reference Oracle (x86-64):**
  - Return Value: `18446744073709550734` (`0xfffffffffffffc8e`)
  - Execution Time: `0.210 ms`
- **Recompiled AArch64 Result:**
  - Return Value: `18446744073709550734` (`0xfffffffffffffc8e`)
  - Trap Code: `0x0` | Exit Code: `0x0`
  - Execution Time: `1.728 ms`
- **State Audit:** Emitted atomic instructions (`ldaxr`, `stlxr`, `dmb ish`) executed cleanly without deadlocks or unaligned access traps.
- **Verdict:** **MATCHED (Bit-Exact)**

### 3.6 Fixture 06: `06_multithread_concurrency`
- **Source:** `phase3-poc/tests/fixtures/06_multithread_concurrency.c`
- **Target Entrypoint:** `run_fixture_06` (ELF VAddr: `0x201300` -> Symbol: `bbr_201300`)
- **Reference Oracle (x86-64):**
  - Return Value: `859025102792` (`0xc801e2d7c8`)
  - Execution Time: `0.386 ms`
- **Recompiled AArch64 Result:**
  - Return Value: `859025102792` (`0xc801e2d7c8`)
  - Trap Code: `0x0` | Exit Code: `0x0`
  - Execution Time: `2.043 ms`
- **State Audit:** Verified sequential composition of atomic fetch-and-add, atomic compare-and-swap retry loop, and spinlock test-and-set critical sections.
- **Verdict:** **MATCHED (Bit-Exact)**

---

## 4. Overall Differential Summary

```text
================================================================================
TOTAL FIXTURES AUDITED:        6
FIXTURES COMPILED:             6 (100.0%)
FIXTURES LINKED (NDK r26c):    6 (100.0%)
FIXTURES PACKAGED IN APK:      6 (100.0%)
FIXTURES EXECUTED:             6 (100.0%)
FIXTURES MATCHED BIT-EXACT:    6 (100.0%)
RUNTIME TRAPS DETECTED:        0 (0.0%)
PHYSICAL HARDWARE TESTED:      0 (NOT_TESTED - Pending ADB device)
================================================================================
```

All six synthetic fixtures compile, link into real Bionic shared libraries, package into the Android APK, execute across the target ISA, and produce bit-exact numeric equivalence to the x86-64 ground truth.
