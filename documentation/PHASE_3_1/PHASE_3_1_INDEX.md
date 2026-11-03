# Phase 3.1: Documentation & Technical Artifact Index

## Overview

Phase 3.1 transitioned the Persona 3 Reload AOT recompilation proof of concept from structural heuristics to **rigorous functional differential validation**, proving bit-exact x86-64 to AArch64 machine code execution across five authoritative C test programs.

This index provides a complete map of all documentation, codebases, scripts, test fixtures, and artifacts created or updated during Phase 3.1.

---

## Documentation Map (`documentation/PHASE_3_1/`)

| Document Name | File Path | Focus Area |
|---|---|---|
| **1. Compiler & Runtime Bug Audit** | [`COMPILER_AND_RUNTIME_BUG_AUDIT.md`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/documentation/PHASE_3_1/COMPILER_AND_RUNTIME_BUG_AUDIT.md) | Audit of 10 compiler and runtime bugs discovered, root-caused, and resolved. |
| **2. Corrected Test Suite** | [`CORRECTED_TEST_SUITE.md`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/documentation/PHASE_3_1/CORRECTED_TEST_SUITE.md) | Technical breakdown of the 5 authoritative C fixtures, anti-folding mechanisms, and ground truth. |
| **3. Differential Execution Results** | [`DIFFERENTIAL_EXECUTION_RESULTS.md`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/documentation/PHASE_3_1/DIFFERENTIAL_EXECUTION_RESULTS.md) | Complete differential results across `COMPILED`, `LINKED`, `EXECUTED`, and `MATCHED` states ($5/5$). |
| **4. ARM64 Linking & Loading** | [`ARM64_LINKING_AND_ANDROID_LOADING.md`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/documentation/PHASE_3_1/ARM64_LINKING_AND_ANDROID_LOADING.md) | Analysis of LLVM LLD, freestanding 128-bit math routines, `-Bsymbolic`, and Bionic constraints. |
| **5. Dispatch & Discovery Validation** | [`DISPATCH_AND_DISCOVERY_VALIDATION.md`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/documentation/PHASE_3_1/DISPATCH_AND_DISCOVERY_VALIDATION.md) | Global dispatch table (`bbr_lookup`), direct/indirect calls, vtables, jump tables, and miss traps. |
| **6. realme Device Validation** | [`REALME_DEVICE_VALIDATION.md`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/documentation/PHASE_3_1/REALME_DEVICE_VALIDATION.md) | Hardware audit (Snapdragon 7s Gen 2 / Adreno 710), ADB log, and explicit `NOT_TESTED` documentation. |
| **7. Upstream Integration Decision** | [`UPSTREAM_INTEGRATION_DECISION.md`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/documentation/PHASE_3_1/UPSTREAM_INTEGRATION_DECISION.md) | Comparative evaluation of Options A, B, and C; hybrid architecture specification for UE4. |
| **8. Risk Register** | [`RISK_REGISTER.md`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/documentation/PHASE_3_1/RISK_REGISTER.md) | Risk analysis across compiler ISA coverage, thermal throttling, LMK memory, and graphics. |
| **9. Phase 3.1 Index** | [`PHASE_3_1_INDEX.md`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/documentation/PHASE_3_1/PHASE_3_1_INDEX.md) | Directory index, cross-references, and build reproduction instructions. |
| **10. Final Validation Report** | [`FINAL_VALIDATION_REPORT.md`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/documentation/PHASE_3_1/FINAL_VALIDATION_REPORT.md) | Definitive Phase 3.1 synthesis answering all 10 core technical questions with GO recommendation. |

---

## Codebase Artifacts (`phase3-poc/`)

### Compiler Engine
- [`phase3-poc/compiler/abi.py`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/phase3-poc/compiler/abi.py): Recomp ABI v2 `GuestState` definition (720 bytes) with `mem_base`, `trap_code`, and `exit_code`.
- [`phase3-poc/compiler/discover.py`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/phase3-poc/compiler/discover.py): Function and basic block discovery engine.
- [`phase3-poc/compiler/lower.py`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/phase3-poc/compiler/lower.py): Instruction lifter translating x86-64 machine instructions into LLVM IR (SSA flag slots, SIMD vector instructions, atomics, intra-function switch jump tables).
- [`phase3-poc/compiler/codegen.py`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/phase3-poc/compiler/codegen.py): AArch64 code generator configured with `-lse` for universal hardware/emulator compatibility.
- [`phase3-poc/compiler/p3r_recomp.py`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/phase3-poc/compiler/p3r_recomp.py): CLI compiler driver supporting raw binaries and static ELF executables.

### Android Runtime Subsystem
- [`phase3-poc/android-runtime/guest_cpu.h`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/phase3-poc/android-runtime/guest_cpu.h): C runtime interface, trap codes, and register enumerations.
- [`phase3-poc/android-runtime/guest_cpu.c`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/phase3-poc/android-runtime/guest_cpu.c): Freestanding runtime implementation including 128-bit division routines (`__udivti3`, `__umodti3`, `__divti3`, `__modti3`), dispatch lookup, and trap handlers.
- [`phase3-poc/android-runtime/differential_runner.py`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/phase3-poc/android-runtime/differential_runner.py): Authoritative differential validation runner executing both x86-64 and AArch64 in Unicorn Engine.
- [`phase3-poc/android-runtime/execution_report.json`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/phase3-poc/android-runtime/execution_report.json): Machine-readable execution logs, timings, return values, and pass/fail states.

### Authoritative Test Suite
- `phase3-poc/tests/fixtures/01_arithmetic.c`
- `phase3-poc/tests/fixtures/02_dispatch.c`
- `phase3-poc/tests/fixtures/03_memory_reloc.c`
- `phase3-poc/tests/fixtures/04_vector_simd.c`
- `phase3-poc/tests/fixtures/05_control_concurrency.c`
- `phase3-poc/tests/expected/manifest.json`

### Build Scripts
- [`phase3-poc/tests/scripts/build_c_fixtures.py`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/phase3-poc/tests/scripts/build_c_fixtures.py): Compiles C fixtures into static x86-64 ELFs and disassembles them.
- [`phase3-poc/tests/scripts/recompile_and_link_all.py`](file:///e:/persona%203%20reload%20android%20port/research/P3R-Android-Research/phase3-poc/tests/scripts/recompile_and_link_all.py): Recompiles all ELFs to AArch64 objects and links them into Android shared libraries.

---

## Step-by-Step Reproduction Instructions

To reproduce the complete Phase 3.1 pipeline from scratch:

```bash
# 1. Navigate to workspace
cd "E:\persona 3 reload android port\research\P3R-Android-Research"

# 2. Build Authoritative x86-64 C Fixtures
python phase3-poc/tests/scripts/build_c_fixtures.py

# 3. Recompile x86-64 ELFs to AArch64 & Link Android Shared Libraries
python phase3-poc/tests/scripts/recompile_and_link_all.py

# 4. Run Differential Execution Suite (Unicorn x86 vs Unicorn ARM64)
python phase3-poc/android-runtime/differential_runner.py
```
*Expected Output:* `5/5 Fixtures Matched Bit-Exact (PASS)`.
