# Phase 3 Documentation Index: AOT Recompilation Proof of Concept

**Branch:** `phase-3-poc`  
**Phase:** 3 — Proof of Concept & Execution Validation  
**Target Architecture:** x86-64 (SysV AMD64) &rarr; LLVM IR &rarr; AArch64 (Android Bionic)  
**Target Hardware:** Realme 12 Pro+ (Qualcomm Snapdragon 7s Gen 2 / Adreno 710)  

---

## Complete Phase 3 Report Directory

| Milestone / Report | Document Link | Summary & Core Findings |
| :--- | :--- | :--- |
| **Milestone 1: Source Audit** | [`REFERENCE_SOURCE_AUDIT.md`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/documentation/PHASE_3/REFERENCE_SOURCE_AUDIT.md) | Exhaustive source audit of `Bloodborne-android-rebuild-tool` (`discover.cpp`, `lifter.cpp`, `lower_ops.cpp`, `compile.cpp`) and `Bloodborne-Android` runtime (`guest_cpu_aot.cpp`, `guest_cpu_atomics.h`, `docs/RECOMP_ABI.md`). Direct line-by-line answers to all 12 architectural questions. |
| **Milestone 2: Test Suite Spec** | [`SYNTHETIC_TEST_SUITE.md`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/documentation/PHASE_3/SYNTHETIC_TEST_SUITE.md) | Specification of the 5 synthetic C test fixtures, ABI test cases, oracle return value manifest (`manifest.json`), and architectural evaluation of PS4 ELF loading vs isolated lifting harness. |
| **Milestone 3: AOT Compiler** | [`AOT_COMPILER_IMPLEMENTATION.md`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/documentation/PHASE_3/AOT_COMPILER_IMPLEMENTATION.md) | Full architectural specification of the recompiler pipeline (`abi.py`, `discover.py`, `lower.py`, `codegen.py`, `p3r_recomp.py`). Details the 696-byte `GuestState`, basic-block CFG generation, safe division wrappers, and LLVM TargetMachine configuration (`+v8.2a,+lse`). |
| **Milestone 4: Android Runtime** | [`ANDROID_EXECUTION_VALIDATION.md`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/documentation/PHASE_3/ANDROID_EXECUTION_VALIDATION.md) | In-depth verification of System V AMD64 vs ARM64 AAPCS64 calling conventions. Evaluates `GuestState*` in X0, callee-saved preservation in X19, 16-byte stack frame alignment, and Bionic libc loader compatibility. |
| **Milestone 5: Discovery & Dispatch** | [`FUNCTION_DISCOVERY_RESULTS.md`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/documentation/PHASE_3/FUNCTION_DISCOVERY_RESULTS.md) | Empirical evaluation of 16-round discovery against Fixture 02. Compares static CFG discovery (3 functions / 42.9% coverage) against augmented extra-entries discovery (7 functions / 100% coverage). Details UE4 dynamic delegate discovery challenges. |
| **Milestone 6: Memory & Atomics** | [`MEMORY_AND_RELOCATION_RESULTS.md`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/documentation/PHASE_3/MEMORY_AND_RELOCATION_RESULTS.md) | Validation of memory addressing, RIP-relative offsets, linked list pointer dereferencing, 16-byte stack alignment, volatile memory reload preservation (fixing commit `ef1a331`), and hardware atomics (`lock xadd`, `lock cmpxchg` mapped to ARMv8.2-A LSE). |
| **Milestone 7: Realme Hardware** | [`REALME_DEVICE_TEST_RESULTS.md`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/documentation/PHASE_3/REALME_DEVICE_TEST_RESULTS.md) | Detailed characterization of the Realme 12 Pro+ (Snapdragon 7s Gen 2 / Adreno 710). Documents physical ADB device connection status (`0 devices attached`), measured compiler throughput, code expansion ($1.57\times$), and memory bandwidth bottleneck ($17\text{ GB/s}$). |
| **Milestone 8: Architecture Decision** | [`AOT_DBT_HYBRID_DECISION.md`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/documentation/PHASE_3/AOT_DBT_HYBRID_DECISION.md) | Exhaustive comparative analysis between Option A (Pure DBT / FEXCore), Option B (Pure AOT / Bloodborne-style), and Option C (Hybrid Architecture). Concludes with the unanimous adoption of Option C for Persona 3 Reload. |
| **Risk Management** | [`RISK_REGISTER.md`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/documentation/PHASE_3/RISK_REGISTER.md) | Comprehensive audit of 7 critical architectural, hardware, compiler, and OS risks, with probability, impact, severity ratings, and concrete mitigation plans. |
| **Final Synthesis & Recommendation**| [`FINAL_POC_REPORT.md`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/documentation/PHASE_3/FINAL_POC_REPORT.md) | Executive capstone report directly answering all 10 prompt research questions. Delivers the final **CONDITIONAL GO (HYBRID AOT + DBT)** project verdict with Phase 4 gating criteria. |

---

## Code Artifacts Directory (`phase3-poc/`)

- [`phase3-poc/compiler/abi.py`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/phase3-poc/compiler/abi.py): Recomp ABI v2 `GuestState` definition (696 bytes).
- [`phase3-poc/compiler/discover.py`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/phase3-poc/compiler/discover.py): 16-round iterative discovery engine.
- [`phase3-poc/compiler/lower.py`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/phase3-poc/compiler/lower.py): Instruction lifter from x86-64 machine code to LLVM IR basic-block CFG.
- [`phase3-poc/compiler/codegen.py`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/phase3-poc/compiler/codegen.py): AArch64 TargetMachine backend emitting ELF `.o`, `.s`, and C dispatch tables.
- [`phase3-poc/compiler/p3r_recomp.py`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/phase3-poc/compiler/p3r_recomp.py): Command-line recompiler driver.
- [`phase3-poc/android-runtime/guest_cpu.h`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/phase3-poc/android-runtime/guest_cpu.h): C runtime header with `GuestState` layout.
- [`phase3-poc/android-runtime/guest_cpu.c`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/phase3-poc/android-runtime/guest_cpu.c): C runtime dispatcher, stack initializer, and missing entry trap handler.
- [`phase3-poc/android-runtime/runner.py`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/phase3-poc/android-runtime/runner.py): Automated test runner verifying all fixtures and ADB status.
- [`phase3-poc/tests/fixtures/`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/phase3-poc/tests/fixtures): Synthetic C test fixtures 01 through 05.
- [`phase3-poc/tests/bin/`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/phase3-poc/tests/bin): Assembled x86-64 `.bin` files and compiled AArch64 `.o`, `.s`, and `_dispatch.c` artifacts.
- [`phase3-poc/tests/expected/manifest.json`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/phase3-poc/tests/expected/manifest.json): Oracle test manifest with pre-calculated expected return values.
