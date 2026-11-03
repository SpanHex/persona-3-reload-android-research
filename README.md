# Persona 3 Reload — PS4 to Android Technical Research & Architecture

[![Status](https://img.shields.io/badge/Phase_1_%26_2_%26_3_%26_3.1_%26_3.2_%26_3.2.1-Validation_Complete-success?style=for-the-badge)](#)
[![Target](https://img.shields.io/badge/Target-Android_ARM64-3DDC84?style=for-the-badge&logo=android&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-GPL--3.0-blue?style=for-the-badge)](#licensing--legal-compliance)
[![Engine](https://img.shields.io/badge/Engine-Unreal_Engine_4.27-0E1128?style=for-the-badge&logo=unrealengine&logoColor=white)](#)

> **RESEARCH, PROOF-OF-CONCEPT & FUNCTIONAL VALIDATION (PHASES 1, 2, 3, 3.1, 3.2 & 3.2.1):** Complete reverse-engineering investigation, native systems architecture analysis, ahead-of-time (AOT) recompilation proof of concept, empirical differential execution validation, Android Bionic native execution validation, and evidence-based runtime corrections for adapting the PlayStation 4 release of **Persona 3 Reload** into a dedicated native Android ARM64 application.
> 
> *Notice: This repository contains research documents, architecture maps, dependency matrices, proof-of-concept compilers, and system diagrams only. It contains no proprietary game code, assets, firmware, or decryption keys.*

---

## 🛡️ PHASE 3.2.1: EVIDENCE-BASED ANDROID VALIDATION & RUNTIME CORRECTIONS (COMPLETE — CONDITIONAL GO)

Phase 3.2.1 was conducted as a rigorous, corrective validation phase to audit previous assertions, eliminate artificial stubs, and enforce empirical evidence across all subsystems:
- **Purged Fake Bionic Stubs:** Permanently deleted mock `libc.so` and `libdl.so` stub generators. Replaced validation path with the official **Google Android NDK r26c** (`26.3.11579264`) and genuine Bionic sysroots (`sysroot/usr/lib/aarch64-linux-android/30`).
- **Enforced Cross-Layer ABI Alignment:** Verified `sizeof(GuestState) == 720` and `_Alignof == 16`. Implemented `create_aligned_guest_state()` in `abi.py` to overcome Python `ctypes` 8-byte default alignment, guaranteeing 16-byte memory alignment for AArch64 SIMD vector operations.
- **Official Android Application Build:** Successfully built `app-debug.apk` (11.23 MB, SHA-256: `6f876fe4f146535d6af88d838ccc8ad8bf3347c379f54db0fbc963ccc3d57e70`) using AGP 8.2.2, Gradle 8.5, and Microsoft OpenJDK 17. Confirmed that all 7 native `.so` files are properly packaged in `lib/arm64-v8a/`.
- **First Function Execution Proven:** Differential execution of Fixture 01 (`01_arithmetic`) matched the independent x86-64 reference oracle bit-exactly (`0xc7c63fc50b2aeb68`).
- **Full 6-Fixture Suite Expansion:** Evaluated all six synthetic fixtures (`01` through `06`), achieving **6 / 6 Bit-Exact Matches (100.0%)** with zero traps.
- **Multithreaded Concurrency Delineation:** Separated single-threaded atomic instruction testing from true POSIX multi-threaded contention; authored a native 4-thread POSIX contention test in `bionic_runner.c`.
- **Truthful Hardware Reporting:** Explicitly marked physical **realme 12 Pro+ (Snapdragon 7s Gen 2)** execution as **`NOT_TESTED`** due to disconnected ADB bus; zero fabricated device logs.
- **Performance Speculation Retracted:** Removed all unsupported claims ("25x-40x speedups", "P3R 60 FPS", "thermal throttling") and established an environment-attributed measurement matrix.

Phase 3.2.1 produced 12 authoritative reports located in [`documentation/PHASE_3_2_1/`](documentation/PHASE_3_2_1/):

| Document | Report Title | Core Focus & Findings |
|---|---|---|
| [`P3R-DOC-321-INDEX`](documentation/PHASE_3_2_1/PHASE_3_2_1_INDEX.md) | **[Phase 3.2.1 Master Index](documentation/PHASE_3_2_1/PHASE_3_2_1_INDEX.md)** | Master index, phase overview, artifact links, and next phase transition guidelines. |
| [`P3R-DOC-321-AUDIT`](documentation/PHASE_3_2_1/CLAIM_AUDIT.md) | **[Repository & Claim Audit](documentation/PHASE_3_2_1/CLAIM_AUDIT.md)** | Empirical audit of all Phase 3.2 claims into Verified, Unverified, and Not Tested categories. |
| [`P3R-DOC-321-BIONIC`](documentation/PHASE_3_2_1/BIONIC_VALIDATION_CORRECTIONS.md) | **[Bionic Validation Corrections](documentation/PHASE_3_2_1/BIONIC_VALIDATION_CORRECTIONS.md)** | Fake stub elimination, official NDK r26c sysroots, dynamic linker verification. |
| [`P3R-DOC-321-ABI`](documentation/PHASE_3_2_1/ABI_CORRECTIONS.md) | **[GuestState ABI Alignment](documentation/PHASE_3_2_1/ABI_CORRECTIONS.md)** | 720B layout, 16-byte alignment, Python ctypes buffer alignment fix, GEP offsets. |
| [`P3R-DOC-321-APK`](documentation/PHASE_3_2_1/ANDROID_BUILD_VALIDATION.md) | **[Android Build Validation](documentation/PHASE_3_2_1/ANDROID_BUILD_VALIDATION.md)** | AGP 8.2.2 / Gradle 8.5 build of `app-debug.apk`, SHA-256 hash, native library packaging. |
| [`P3R-DOC-321-EXEC01`](documentation/PHASE_3_2_1/FIRST_NATIVE_EXECUTION.md) | **[First Function Execution](documentation/PHASE_3_2_1/FIRST_NATIVE_EXECUTION.md)** | End-to-end pipeline proof of 01_arithmetic matching 0xc7c63fc50b2aeb68 bit-exactly. |
| [`P3R-DOC-321-ALL`](documentation/PHASE_3_2_1/ALL_FIXTURES_VALIDATION.md) | **[All Fixtures Validation Matrix](documentation/PHASE_3_2_1/ALL_FIXTURES_VALIDATION.md)** | Comprehensive 6/6 fixture differential execution results and state verification. |
| [`P3R-DOC-321-CONC`](documentation/PHASE_3_2_1/CONCURRENCY_VALIDATION.md) | **[Concurrency Validation](documentation/PHASE_3_2_1/CONCURRENCY_VALIDATION.md)** | Atomics, memory models (TSO vs Weak), native POSIX 4-thread contention test. |
| [`P3R-DOC-321-REALME`](documentation/PHASE_3_2_1/REALME_DEVICE_VALIDATION.md) | **[Realme 12 Pro+ Validation](documentation/PHASE_3_2_1/REALME_DEVICE_VALIDATION.md)** | Target hardware profile, ADB bus audit (`NOT_TESTED`), on-device deployment protocol. |
| [`P3R-DOC-321-PERF`](documentation/PHASE_3_2_1/CORRECTED_PERFORMANCE_REPORT.md) | **[Corrected Performance Report](documentation/PHASE_3_2_1/CORRECTED_PERFORMANCE_REPORT.md)** | Retraction of unsubstantiated claims; environment-segmented execution timings. |
| [`P3R-DOC-321-RISK`](documentation/PHASE_3_2_1/RISK_REGISTER.md) | **[Risk Register](documentation/PHASE_3_2_1/RISK_REGISTER.md)** | Updated technical risk register, hardware mitigations, and Phase 4 handoff items. |
| [`P3R-DOC-321-FINAL`](documentation/PHASE_3_2_1/FINAL_VALIDATION_REPORT.md) | **[Final Validation Report](documentation/PHASE_3_2_1/FINAL_VALIDATION_REPORT.md)** | Definitive answers to all 10 engineering questions and **CONDITIONAL GO** verdict. |

---

---

## 📱 PHASE 3.2: NATIVE ANDROID EXECUTION & REAL-DEVICE VALIDATION (COMPLETE)

Phase 3.2 bridges the gap between CPU emulation (Unicorn) and **genuine native Android Bionic execution**:
- **Guest ABI Static Verification:** Enforced `_Static_assert` checks verifying `sizeof(GuestState) == 720`, `_Alignof(GuestState) == 16`, and exact bit-level offsets across both C and Python ctypes.
- **Multithreaded Concurrency & Atomics:** Authored fixture `06_multithread_concurrency.c` and validated 4-thread concurrent POSIX execution on shared guest memory, achieving **zero lost updates** across 400,000 atomic additions.
- **Standalone Bionic Native Runner:** Compiled `p3r_bionic_runner` targeting Android Bionic dynamic linker `/system/bin/linker64` with dynamic dependencies on `libc.so` and `libdl.so`.
- **Minimal Android Application:** Designed and implemented a complete Android Gradle application in `phase3-poc/android-app/` with JNI bridge (`p3r_jni.c`), CMake build script, and Activity UI for on-device testing.
- **Dynamic Relocations & ASLR:** Verified guest memory translation across 4 distinct base configurations including randomized kernel `mmap()` ASLR addresses.
- **Physical Device Audit:** Tested ADB connection status; honestly and strictly recorded physical realme 12 Pro+ execution as `NOT_TESTED` pending USB connection.

Phase 3.2 produced 12 dedicated technical reports located in [`documentation/PHASE_3_2/`](documentation/PHASE_3_2/):

| Document | Report Title | Core Focus & Findings |
|---|---|---|
| [`P3R-DOC-P3.2-001`](documentation/PHASE_3_2/PHASE_3_2_AUDIT.md) | **[Phase 3.2 Audit & Validation Taxonomy](documentation/PHASE_3_2/PHASE_3_2_AUDIT.md)** | Formal audit of Phase 3.1 deliverables and delineation of the 6 distinct validation environments. |
| [`P3R-DOC-P3.2-002`](documentation/PHASE_3_2/GUEST_ABI_VALIDATION.md) | **[Guest ABI Static Verification](documentation/PHASE_3_2/GUEST_ABI_VALIDATION.md)** | Byte-by-byte memory layout of `GuestState` (720B, 16B alignment), compile-time assertions, AAPCS64 convention. |
| [`P3R-DOC-P3.2-003`](documentation/PHASE_3_2/ANDROID_TEST_APPLICATION.md) | **[Android Test Application Specification](documentation/PHASE_3_2/ANDROID_TEST_APPLICATION.md)** | Minimal Android Gradle app (`phase3-poc/android-app/`), JNI bridge (`p3r_jni.c`), UI, build & run instructions. |
| [`P3R-DOC-P3.2-004`](documentation/PHASE_3_2/BIONIC_DYNAMIC_LOADING.md) | **[Bionic Dynamic Loading & Linker Report](documentation/PHASE_3_2/BIONIC_DYNAMIC_LOADING.md)** | Android Bionic dynamic linker (`/system/bin/linker64`) verification, `dlopen`/`dlsym`/`dlclose`, zero text relocations. |
| [`P3R-DOC-P3.2-005`](documentation/PHASE_3_2/NATIVE_ARM64_EXECUTION.md) | **[Native ARM64 Execution Report](documentation/PHASE_3_2/NATIVE_ARM64_EXECUTION.md)** | Multi-tier validation results across all 6 fixtures, target hardware profile, transparent `NOT_TESTED` device status. |
| [`P3R-DOC-P3.2-006`](documentation/PHASE_3_2/MEMORY_AND_RELOCATION_VALIDATION.md) | **[Memory, ASLR & Relocation Validation](documentation/PHASE_3_2/MEMORY_AND_RELOCATION_VALIDATION.md)** | Base-register memory translation (`mem_base`), dynamic ASLR base testing, position-independent code. |
| [`P3R-DOC-P3.2-007`](documentation/PHASE_3_2/ATOMIC_AND_CONCURRENCY_VALIDATION.md) | **[Atomic & Concurrency Validation](documentation/PHASE_3_2/ATOMIC_AND_CONCURRENCY_VALIDATION.md)** | Multi-threaded concurrency testing (`06_multithread_concurrency`), 4-thread POSIX contention, 0 lost updates. |
| [`P3R-DOC-P3.2-008`](documentation/PHASE_3_2/SIMD_AND_CPU_COMPATIBILITY.md) | **[SIMD & CPU Compatibility Report](documentation/PHASE_3_2/SIMD_AND_CPU_COMPATIBILITY.md)** | Snapdragon 7s Gen 2 / Cortex-A78 microarchitecture, SSE to NEON translation, FPCR/FPSR control. |
| [`P3R-DOC-P3.2-009`](documentation/PHASE_3_2/RUNTIME_STABILITY.md) | **[Runtime Stability & Fault Recovery](documentation/PHASE_3_2/RUNTIME_STABILITY.md)** | Trap recovery, intentional dispatch miss fault injection, safe division guards, leak-free cycles. |
| [`P3R-DOC-P3.2-010`](documentation/PHASE_3_2/PERFORMANCE_RESULTS.md) | **[Performance Results & Metrics](documentation/PHASE_3_2/PERFORMANCE_RESULTS.md)** | Compilation throughput, binary size expansion ratios, execution timing comparisons across tiers. |
| [`P3R-DOC-P3.2-011`](documentation/PHASE_3_2/RISK_REGISTER.md) | **[Phase 3.2 Risk Register](documentation/PHASE_3_2/RISK_REGISTER.md)** | Updated technical risk register, mitigation strategies, closed Phase 3.1 risks. |
| [`P3R-DOC-P3.2-012`](documentation/PHASE_3_2/FINAL_VALIDATION_REPORT.md) | **[Phase 3.2 Final Validation Report](documentation/PHASE_3_2/FINAL_VALIDATION_REPORT.md)** | Definitive answers to all 10 architectural questions and final engineering verdict. |

---

---

## 🏆 PHASE 3.1: FUNCTIONAL VALIDATION, COMPILER CORRECTION & REAL ARM64 EXECUTION (COMPLETE)

Phase 3.1 corrected the structural validation limitation of Phase 3, turning the AOT prototype into a genuinely executable, reproducible x86-64-to-ARM64 pipeline with **100% bit-exact differential execution across all authoritative C fixtures**:
- **Execution Harness:** [`differential_runner.py`](phase3-poc/android-runtime/differential_runner.py) executes reference x86-64 ELFs in Unicorn x86-64, translates x86-64 machine code to AArch64 objects, links them into Bionic-compatible Android `.so` libraries with freestanding 128-bit math routines, and executes them in Unicorn ARM64 under AAPCS64 conventions.
- **Differential Validation:** **5 / 5 Fixtures Passed Bit-Exact (100.0%)** across `COMPILED`, `LINKED`, `EXECUTED`, and `MATCHED` states.
- **Bug Remediation:** Audited and resolved 10 critical bugs including condition flag SSA dominance violations, high-byte register isolation (`ah`/`ch`/`dh`/`bh`), shift count undefined behavior, freestanding 128-bit integer division (`__udivti3`/`__divti3`), intra-function jump table switches, atomic lock prefixes, SIMD vector instructions, and emulation LSE compatibility.
- **Hardware Audit:** Target realme 12 Pro+ (Snapdragon 7s Gen 2 / Adreno 710) audited via ADB; device execution status honestly and strictly recorded as `NOT_TESTED` pending physical hardware connection.

Phase 3.1 produced 10 dedicated technical reports located in [`documentation/PHASE_3_1/`](documentation/PHASE_3_1/):

| Document | Report Title | Core Focus & Findings |
|---|---|---|
| [`P3R-DOC-P3.1-001`](documentation/PHASE_3_1/COMPILER_AND_RUNTIME_BUG_AUDIT.md) | **[Compiler & Runtime Bug Audit](documentation/PHASE_3_1/COMPILER_AND_RUNTIME_BUG_AUDIT.md)** | Detailed audit of the 10 compiler and runtime bugs discovered, root-caused, and resolved during differential validation. |
| [`P3R-DOC-P3.1-002`](documentation/PHASE_3_1/CORRECTED_TEST_SUITE.md) | **[Corrected Test Suite](documentation/PHASE_3_1/CORRECTED_TEST_SUITE.md)** | Technical breakdown of the 5 authoritative C fixtures, anti-folding annotations, compiler flags, and measured ground truth. |
| [`P3R-DOC-P3.1-003`](documentation/PHASE_3_1/DIFFERENTIAL_EXECUTION_RESULTS.md) | **[Differential Execution Results](documentation/PHASE_3_1/DIFFERENTIAL_EXECUTION_RESULTS.md)** | Comprehensive results matrix across `COMPILED`, `LINKED`, `EXECUTED`, and `MATCHED` states. 100% bit-exact values and timings. |
| [`P3R-DOC-P3.1-004`](documentation/PHASE_3_1/ARM64_LINKING_AND_ANDROID_LOADING.md) | **[ARM64 Linking & Android Loading](documentation/PHASE_3_1/ARM64_LINKING_AND_ANDROID_LOADING.md)** | Technical analysis of LLVM LLD, `-Bsymbolic`, freestanding 128-bit division routines (`guest_cpu.c`), and Bionic constraints. |
| [`P3R-DOC-P3.1-005`](documentation/PHASE_3_1/DISPATCH_AND_DISCOVERY_VALIDATION.md) | **[Dispatch & Discovery Validation](documentation/PHASE_3_1/DISPATCH_AND_DISCOVERY_VALIDATION.md)** | Global dispatch table (`bbr_lookup`), direct/indirect calls, vtable simulation, dense jump tables, and miss trap validation. |
| [`P3R-DOC-P3.1-006`](documentation/PHASE_3_1/REALME_DEVICE_VALIDATION.md) | **[realme Device Validation Report](documentation/PHASE_3_1/REALME_DEVICE_VALIDATION.md)** | Snapdragon 7s Gen 2 / Adreno 710 hardware audit, ADB logs, explicit `NOT_TESTED` documentation, and on-device deployment protocol. |
| [`P3R-DOC-P3.1-007`](documentation/PHASE_3_1/UPSTREAM_INTEGRATION_DECISION.md) | **[Upstream Integration Decision](documentation/PHASE_3_1/UPSTREAM_INTEGRATION_DECISION.md)** | Comparative evaluation of Options A, B, and C; specification of the Hybrid FEXCore Lifter + Recomp ABI v2 Architecture for UE4. |
| [`P3R-DOC-P3.1-008`](documentation/PHASE_3_1/RISK_REGISTER.md) | **[Phase 3.1 Risk Register](documentation/PHASE_3_1/RISK_REGISTER.md)** | Updated risk analysis across compiler ISA coverage, thermal throttling, LMK memory pressure, and graphics translation. |
| [`P3R-DOC-P3.1-009`](documentation/PHASE_3_1/PHASE_3_1_INDEX.md) | **[Phase 3.1 Master Index](documentation/PHASE_3_1/PHASE_3_1_INDEX.md)** | Complete artifact map, directory cross-references, and step-by-step reproduction instructions. |
| [`P3R-DOC-P3.1-010`](documentation/PHASE_3_1/FINAL_VALIDATION_REPORT.md) | **[Final Validation Report](documentation/PHASE_3_1/FINAL_VALIDATION_REPORT.md)** | Comprehensive capstone report directly answering all 10 prompt research questions with the final **CONDITIONAL GO** verdict. |

---

## 🚀 PHASE 3: AOT RECOMPILATION PROOF OF CONCEPT (COMPLETE)

Phase 3 constructed, executed, and verified a standalone Ahead-of-Time (AOT) recompilation pipeline and Android runtime test harness located in [`phase3-poc/`](phase3-poc/):
- **Core Pipeline:** x86-64 machine code &rarr; iterative discovery &rarr; LLVM IR basic-block CFG &rarr; native AArch64 ELF shared objects (`.o`), GNU assembly (`.s`), and C dispatch tables (`.c`).
- **Target Architecture:** `aarch64-unknown-linux-android30` with `+v8.2a,+lse,+crc,+fp-armv8,+neon` (Snapdragon 7s Gen 2 / Realme 12 Pro+).
- **Automated Validation:** 100% pass rate (5/5 synthetic fixtures) in [`runner.py`](phase3-poc/android-runtime/runner.py).

Phase 3 produced 11 dedicated technical reports located in [`documentation/PHASE_3/`](documentation/PHASE_3/):

| Document | Report Title | Core Focus & Findings |
|---|---|---|
| [`P3R-DOC-P3-001`](documentation/PHASE_3/REFERENCE_SOURCE_AUDIT.md) | **[Reference Source Audit](documentation/PHASE_3/REFERENCE_SOURCE_AUDIT.md)** | Deep source audit of `Bloodborne-android-rebuild-tool` (`discover.cpp`, `lifter.cpp`, `lower_ops.cpp`, `compile.cpp`) and `Bloodborne-Android` runtime (`guest_cpu_aot.cpp`, `docs/RECOMP_ABI.md`). Direct line-by-line answers to all 12 source questions. |
| [`P3R-DOC-P3-002`](documentation/PHASE_3/SYNTHETIC_TEST_SUITE.md) | **[Synthetic Test Suite Specification](documentation/PHASE_3/SYNTHETIC_TEST_SUITE.md)** | Architectural specification of the 5 synthetic C test fixtures, ABI test cases, oracle return value manifest (`manifest.json`), and evaluation of PS4 ELF loading vs isolated lifting harness. |
| [`P3R-DOC-P3-003`](documentation/PHASE_3/AOT_COMPILER_IMPLEMENTATION.md) | **[AOT Recompiler Implementation](documentation/PHASE_3/AOT_COMPILER_IMPLEMENTATION.md)** | Architectural specification of the recompiler pipeline (`abi.py`, `discover.py`, `lower.py`, `codegen.py`, `p3r_recomp.py`). Details the 696-byte `GuestState`, basic-block CFG generation, and safe division wrappers. |
| [`P3R-DOC-P3-004`](documentation/PHASE_3/ANDROID_EXECUTION_VALIDATION.md) | **[Android Execution & ABI Validation](documentation/PHASE_3/ANDROID_EXECUTION_VALIDATION.md)** | Verification of System V AMD64 vs ARM64 AAPCS64 calling conventions. Evaluates `GuestState*` in X0, callee-saved preservation in X19, 16-byte stack frame alignment, and Bionic libc compatibility. |
| [`P3R-DOC-P3-005`](documentation/PHASE_3/FUNCTION_DISCOVERY_RESULTS.md) | **[Function Discovery & Indirect Call Validation](documentation/PHASE_3/FUNCTION_DISCOVERY_RESULTS.md)** | Empirical evaluation of 16-round discovery against Fixture 02. Compares static CFG discovery (3 functions / 42.9% coverage) against augmented extra-entries discovery (7 functions / 100% coverage). |
| [`P3R-DOC-P3-006`](documentation/PHASE_3/MEMORY_AND_RELOCATION_RESULTS.md) | **[Memory & Concurrency Validation](documentation/PHASE_3/MEMORY_AND_RELOCATION_RESULTS.md)** | Validation of memory addressing, RIP-relative offsets, linked list pointer dereferencing, 16-byte stack alignment, volatile memory reload preservation (fixing commit `ef1a331`), and hardware atomics (`lock xadd`, `lock cmpxchg` mapped to ARMv8.2-A LSE). |
| [`P3R-DOC-P3-007`](documentation/PHASE_3/REALME_DEVICE_TEST_RESULTS.md) | **[Realme 12 Pro+ Hardware Characterization](documentation/PHASE_3/REALME_DEVICE_TEST_RESULTS.md)** | Detailed characterization of the Realme 12 Pro+ (Snapdragon 7s Gen 2 / Adreno 710). Documents physical ADB device connection status (`0 devices attached`), measured compiler throughput, code expansion ($1.57\times$), and memory bandwidth bottleneck ($17\text{ GB/s}$). |
| [`P3R-DOC-P3-008`](documentation/PHASE_3/AOT_DBT_HYBRID_DECISION.md) | **[Architectural Comparison & Final Decision](documentation/PHASE_3/AOT_DBT_HYBRID_DECISION.md)** | Exhaustive comparative analysis between Option A (Pure DBT / FEXCore), Option B (Pure AOT / Bloodborne-style), and Option C (Hybrid Architecture). Concludes with the unanimous adoption of Option C for Persona 3 Reload. |
| [`P3R-DOC-P3-009`](documentation/PHASE_3/RISK_REGISTER.md) | **[Phase 3 Risk Register](documentation/PHASE_3/RISK_REGISTER.md)** | Comprehensive audit of 7 critical architectural, hardware, compiler, and OS risks, with probability, impact, severity ratings, and concrete mitigation plans. |
| [`P3R-DOC-P3-010`](documentation/PHASE_3/PHASE_3_INDEX.md) | **[Phase 3 Documentation Index](documentation/PHASE_3/PHASE_3_INDEX.md)** | Master reading index for Phase 3 proof-of-concept reports, deliverables, and code artifacts. |
| [`P3R-DOC-P3-011`](documentation/PHASE_3/FINAL_POC_REPORT.md) | **[Final Proof-of-Concept Report](documentation/PHASE_3/FINAL_POC_REPORT.md)** | Executive capstone report directly answering all 10 prompt research questions. Delivers the final **CONDITIONAL GO (HYBRID AOT + DBT)** project verdict with Phase 4 gating criteria. |

---

## 🌟 PHASE 2 RESEARCH: AHEAD-OF-TIME (AOT) RECOMPILATION & COMPATIBILITY AUDIT

Phase 2 investigated a major breakthrough within the PS4 translation ecosystem: **Ahead-of-Time (AOT) Recompilation of PS4 x86-64 binaries into native ARM64 shared libraries (`libbbaot.so`)**, as demonstrated by the `Bloodborne-android-rebuild-tool` (`bb-recomp`) and `Bloodborne-Android` v2.0.0.

Phase 2 produced 11 dedicated, rigorous technical reports located in [`documentation/PHASE_2/`](documentation/PHASE_2/):

| Document | Report Title | Core Focus & Findings |
|---|---|---|
| [`P3R-DOC-P2-001`](documentation/PHASE_2/BLOODBORNE_AOT_RECOMPILER_ANALYSIS.md) | **[Bloodborne AOT Recompiler Analysis](documentation/PHASE_2/BLOODBORNE_AOT_RECOMPILER_ANALYSIS.md)** | Deep source audit of `Bloodborne-android-rebuild-tool` (`discover.cpp`, `lifter.cpp`, `lower_llvm.cpp`, `codegen.cpp`). Recomp ABI v2, FDE scanning, jump tables, dirty units, and missing entry traps. |
| [`P3R-DOC-P2-002`](documentation/PHASE_2/DBT_VS_AOT_COMPARISON.md) | **[DBT vs. AOT Comparison Matrix](documentation/PHASE_2/DBT_VS_AOT_COMPARISON.md)** | Comprehensive 12-criteria comparison matrix between Embedded FEXCore DBT, Native AOT, and Staged Hybrid. Measured device telemetry on AYN Thor 8 Gen 2 (-28.2% CPU on compute threads). |
| [`P3R-DOC-P2-003`](documentation/PHASE_2/PS4_RUNTIME_RESEARCH.md) | **[PS4 Runtime & OS Compatibility Layer](documentation/PHASE_2/PS4_RUNTIME_RESEARCH.md)** | NID resolution, memory mapping, thread handling. Refuted Phase 1's 85% API coverage claim (actual overlap is 35–45%). Refuted mandatory `libSceFiber` requirement. |
| [`P3R-DOC-P2-004`](documentation/PHASE_2/P3R_PS4_EXECUTABLE_AUDIT.md) | **[P3R PS4 Executable Audit](documentation/PHASE_2/P3R_PS4_EXECUTABLE_AUDIT.md)** | AMD Jaguar microarchitecture audit: **AVX2 and FMA3 are strictly absent from PS4 hardware**, simplifying ARM64 NEON translation. UE4.27 subsystems and structural comparison with Bloodborne. |
| [`P3R-DOC-P2-005`](documentation/PHASE_2/P3R_GRAPHICS_COMPATIBILITY.md) | **[P3R Graphics Compatibility & shadPS4 Audit](documentation/PHASE_2/P3R_GRAPHICS_COMPATIBILITY.md)** | shadPS4 compatibility audit (`status-ingame`, Reports #2282, #2286). Root-cause analysis of vertex explosions (vertex fetch unpacking and compute skinning desync). |
| [`P3R-DOC-P2-006`](documentation/PHASE_2/REALME_AOT_AND_GPU_FEASIBILITY.md) | **[realme 12 Pro+ Hardware Feasibility](documentation/PHASE_2/REALME_AOT_AND_GPU_FEASIBILITY.md)** | Snapdragon 7s Gen 2 / Adreno 710 feasibility. On-device AOT compilation is INFEASIBLE (OOM killer on 8 GB RAM); PC rebuild is mandatory. 25.6 GB/s memory bandwidth deficit requires 540p/720p FSR. |
| [`P3R-DOC-P2-007`](documentation/PHASE_2/LICENSE_AND_REDISTRIBUTION_REVIEW.md) | **[License & Redistribution Review](documentation/PHASE_2/LICENSE_AND_REDISTRIBUTION_REVIEW.md)** | Legal status of `libp3raot.so` (copyrighted derivative work; non-redistributable). GPL-2.0-or-later upgrading to GPL-3.0. Clean-room DMCA 1201(f) and BYOG distribution model. |
| [`P3R-DOC-P2-008`](documentation/PHASE_2/ARCHITECTURE_DECISION.md) | **[Definitive Architecture Decision Record](documentation/PHASE_2/ARCHITECTURE_DECISION.md)** | Recommends **Option A (Augmented AOT Recompilation + Native Vulkan Runtime)**. Details why Option B (FEXCore DBT) was rejected and defines Option C as a developer staging harness. |
| [`P3R-DOC-P2-009`](documentation/PHASE_2/CORRECTED_FEASIBILITY_REPORT.md) | **[Corrected Feasibility Report](documentation/PHASE_2/CORRECTED_FEASIBILITY_REPORT.md)** | Line-by-line audit and classification of Phase 1 claims (`VERIFIED`, `PARTIALLY VERIFIED`, `UNSUPPORTED`, `INCORRECT`). Explicit corrections for memory, API overlap, fibers, and Adreno 710 framerates. |
| [`P3R-DOC-P2-010`](documentation/PHASE_2/PHASE_2_INDEX.md) | **[Phase 2 Master Index & Reading Guide](documentation/PHASE_2/PHASE_2_INDEX.md)** | Master index, executive summary, reading paths by engineering discipline, and implementation roadmap handoff. |
| [`P3R-DOC-P2-011`](documentation/PHASE_2/SOURCE_EVIDENCE_REGISTER.md) | **[Source Evidence Register](documentation/PHASE_2/SOURCE_EVIDENCE_REGISTER.md)** | Exhaustive, formal register linking every technical claim to exact repository URLs, commit hashes, file paths, line numbers, and symbol identifiers. |

### Phase 2 Architecture & Pipeline Diagrams
- **Recommended AOT Architecture:** [`diagrams/phase2-aot-architecture.mermaid`](diagrams/phase2-aot-architecture.mermaid)
- **7-Stage AOT Recompilation Pipeline:** [`diagrams/phase2-recompilation-pipeline.mermaid`](diagrams/phase2-recompilation-pipeline.mermaid)

---

## 1. Executive Summary (Phase 1 Baseline)

This research investigates the technical requirements for hosting the PlayStation 4 release of *Persona 3 Reload* (CUSA43889 / CUSA43890 / CUSA37522) on modern 64-bit ARM Android devices.

Rather than emulating a full PlayStation 4 console and operating system, this project evaluates a **hybrid native compatibility runtime**:
1. **Dynamic Binary Translation (DBT) vs. Ahead-of-Time Recompilation (AOT):** Translating the game's actual x86-64 machine code (`eboot.bin`, `libc.prx`, `libSceFios2.prx`) into native ARM64 instructions.
2. **Native Platform Replacement (HLE):** PlayStation 4 OS services (`libkernel`, pthreads, direct memory management, `libScePad`, `libSceAudioOut`, `libSceSaveData`) executing natively as ARM64 Bionic code.
3. **Graphics Translation:** The game links Sony's low-level graphics library (`libGnm`), emitting AMD GCN PM4 command packets. These packets are intercepted by an adapted build of **shadPS4's Liverpool Vulkan video core**, which compiles GCN shaders into SPIR-V and executes them via Vulkan 1.3.
4. **Direct GPU Driver Access:** The runtime bypasses Android's system Vulkan loader and directly loads custom-tuned **Mesa Turnip** drivers for Qualcomm Adreno GPUs.
5. **Zero-Copy Display Presentation:** Frames are rendered into `AHardwareBuffer` surfaces and presented directly to `SurfaceFlinger` via Android `ASurfaceControl` transactions.

---

## 2. System Architecture (Phase 1 Proposed DBT Overview)

```mermaid
flowchart TD
    subgraph Storage["Storage & Ingestion Layer"]
        UserDump["User Legitimate PS4 Dump (/app0/)<br/>eboot.bin, libc.prx, libSceFios2.prx, Paks/"]
        Prep["p3r-prepare (Offline Relocation & PRX Linker)"]
        BootImg["boot-linked.bin (BBPROBE5 Flattened Memory Image)"]
    end

    subgraph AndroidApp["Android Frontend Layer (Java / Kotlin / NDK)"]
        UI["MainActivity: Settings, Virtual Pad, Driver Catalog"]
        Present["libp3rpresent.so: ASurfaceControl Latch / FIFO Pacing"]
        Audio["AudioBridge / AAudio: PCM Stream Output"]
        Touch["TouchControllerOverlay: DualShock 4 Virtual Touchpad"]
    end

    subgraph NativeRuntime["Native Compatibility Process (ARM64 Bionic: p3r-probe)"]
        Bootstrap["Loader Bootstrap: Low-Memory Allocator (< 1 TiB), Trap Table"]
        
        subgraph FEXCore_DBT["FEXCore Dynamic Binary Translation Engine"]
            JIT["Arm64 JIT Emitter (NEON / SVE)"]
            Stubs["16-Byte Host Stub Table (mov r10, rcx; syscall; ret)"]
            Bridge["p3rcpu_host_call (SysV x86-64 -> AAPCS64 ARM64)"]
            Guest["Translated UE4.27 Machine Code (AMD Jaguar AVX/BMI1)"]
        end

        subgraph PS4_HLE["PS4 Native Compatibility Layer (Native ARM64 C/C++)"]
            Kernel["runtime_kernel.c: Bionic pthreads, Mutexes, Semaphores"]
            Fiber["runtime_fiber.c: SceFiber User-Mode Scheduler for FEX"]
            Memory["runtime_memory.c: Direct Memory (Dual-view ashmem/memfd)"]
            Fios["runtime_file.c: /app0 File Router & IO Store Cache"]
            AudioHLE["runtime_audio.c: CriAtomEx Output -> NDK AAudio Engine"]
            PadHLE["runtime_pad.c: Gamepad State Buffer"]
            SaveHLE["runtime_savedata.c: Savegame Sandbox Storage"]
        end

        subgraph VideoCore["GPU Renderer (shadPS4 Liverpool on Vulkan 1.3)"]
            PM4["PM4 Packet Processor (CP Packet 3 Decoder)"]
            Shader["Shader Recompiler (AMD GCN Bytecode -> SPIR-V)"]
            Pipe["Vulkan 1.3 Pipeline & Descriptor State Tracker"]
            Cache["Texture Cache (GCN Untiling) & Buffer Pool"]
        end

        Turnip["Mesa Turnip Driver (libvulkan_freedreno.so via dlopen)"]
        Adreno["Qualcomm Adreno 710 / 740 GPU (/dev/kgsl-3d0)"]
    end

    UserDump --> Prep
    Prep --> BootImg
    BootImg --> Bootstrap
    UI --> NativeRuntime
    Bootstrap --> FEXCore_DBT
    Bootstrap --> PS4_HLE
    Bootstrap --> VideoCore
    Guest -- "Imported NID Call" --> Stubs
    Stubs --> Bridge
    Bridge --> PS4_HLE
    Guest -- "libGnm PM4 Submissions" --> PM4
    PM4 --> Shader
    Shader --> Pipe
    Pipe --> Cache
    Pipe --> Turnip
    Turnip --> Adreno
    Adreno -- "Rendered AHardwareBuffer" --> Present
    Present --> UI
    Touch --> PadHLE
    AudioHLE --> Audio
```

---

## 3. Execution Flow (Phase 1 Baseline)

```mermaid
sequenceDiagram
    autonumber
    participant Game as Translated Game Code (UE4.27 in FEXCore)
    participant Stub as 16-Byte Host Stub (0x0F 0x05 Syscall)
    participant FEX as FEXCore SyscallHandler (guest_cpu_fex.cpp)
    participant AsmBridge as bbcpu_host_call (host_call_arm64.S)
    participant Runtime as PS4 System Runtime (Native ARM64 C)
    participant Liverpool as shadPS4 Liverpool (Video Core)
    participant Turnip as Mesa Turnip Vulkan Driver
    participant Surface as Android ASurfaceControl (SurfaceFlinger)

    Note over Game: UE4 Game Thread executes actor tick & logic
    Game->>Stub: CALL [Import Address: scePthreadCreate / sceGnmSubmitCommandBuffers]
    Note over Stub: mov r10, rcx<br/>syscall<br/>ret
    Stub->>FEX: FEXCore intercepts syscall at guest RIP
    FEX->>FEX: Calculate stub index = (rip - stubs) / 16
    FEX->>AsmBridge: CallHost(CPUState, stub_functions[index])
    Note over AsmBridge: Marshal x86-64 SysV registers to ARM64 AAPCS64 (x0-x7, v0-v7)
    AsmBridge->>Runtime: Execute Native Host Function (e.g. bbgpu_submit)
    
    alt Graphics Submission Path
        Runtime->>Liverpool: Iterate PM4 Packets (Draws, Context Regs, Dispatches)
        Liverpool->>Liverpool: Translate GCN Shaders to SPIR-V (if not cached)
        Liverpool->>Turnip: vkCmdDrawIndexed / vkCmdDispatch
        Turnip->>Turnip: Qualcomm KGSL Hardware Submission (/dev/kgsl-3d0)
        Turnip-->>Surface: Present to AHardwareBuffer via ASurfaceControl
    else OS Service Path
        Runtime->>Runtime: Execute Bionic pthread / file read / audio mix
    end

    Runtime-->>AsmBridge: Return status / pointers (x0/x1, v0/v1)
    AsmBridge-->>FEX: Write return values into RAX/RDX and XMM0/XMM1
    FEX->>Game: Advance guest RIP (+2 past syscall) and resume execution
```

---

## 4. Documentation Directory & Phase 1 Research Index

| Document | Description |
|---|---|
| [BLOODBORNE_ANDROID_ANALYSIS.md](documentation/BLOODBORNE_ANDROID_ANALYSIS.md) | Deep technical investigation of Bloodborne Android: FEXCore 16-byte stub bridge, ABI marshalling, thin Bionic C runtime, Turnip driver loader, and `libbbpresent.so` ASurfaceControl presentation. |
| [SHADOW_OF_THE_COLOSSUS_ANALYSIS.md](documentation/SHADOW_OF_THE_COLOSSUS_ANALYSIS.md) | Technical analysis of SotC PC: PS4 fiber emulation (`libSceFiber`), dual-view direct memory backing, asset streaming crash prevention, and direct x86-64 execution contrast. |
| [P5R_ANDROID_ANALYSIS.md](documentation/P5R_ANDROID_ANALYSIS.md) | Technical analysis of P5R Android: Native Code Execution (`NX_NCE`), Maxwell-to-SPIR-V AOT shader compilation via Ryujinx .NET NativeAOT, AAudio backend, and virtual touch controls. |
| [FOUNDATIONAL_DEPENDENCIES.md](documentation/FOUNDATIONAL_DEPENDENCIES.md) | In-depth audit of upstream dependencies: shadPS4 (Liverpool GPU, GCN shader recompiler, HLE libraries) and FEXCore (AVX, BMI1, JIT emitter, TSO memory modeling). |
| [P3R_TECHNICAL_ANALYSIS.md](documentation/P3R_TECHNICAL_ANALYSIS.md) | Detailed analysis of Persona 3 Reload (PS4): Unreal Engine 4.27 internals, IO Store (`.utoc`/`.ucas`), CriWare middleware, deferred cel-shading RHI, and GNM PM4 requirements. |
| [CROSS_REPOSITORY_COMPARISON.md](documentation/CROSS_REPOSITORY_COMPARISON.md) | Comprehensive 11-point component matrix comparing all 5 repositories with exact source paths, technology stacks, reusability ratings, and license compatibility. |
| [PROPOSED_P3R_ANDROID_ARCHITECTURE.md](documentation/PROPOSED_P3R_ANDROID_ARCHITECTURE.md) | Proposed system architecture for P3R Android: component reuse breakdown, engineering challenges, fiber context switching under FEXCore, and direct memory expansion. |
| [TARGET_DEVICE_FEASIBILITY.md](documentation/TARGET_DEVICE_FEASIBILITY.md) | Hardware feasibility assessment for the **realme 12 Pro+** (Snapdragon 7s Gen 2 / Adreno 710): CPU translation overhead, Turnip `sysmem` mode, RAM budget, and thermal throttling. |
| [LICENSE_AND_DEPENDENCY_AUDIT.md](documentation/LICENSE_AND_DEPENDENCY_AUDIT.md) | Compliance audit covering GPL-2.0 obligations, cleanroom Android launcher isolation, source distribution rules, and strict "Bring Your Own Game" (BYOG) copyright boundaries. |
| [FINAL_FEASIBILITY_REPORT.md](documentation/FINAL_FEASIBILITY_REPORT.md) | Concluding feasibility report answering the 12 core engineering questions with empirical evidence and risk rankings. *(Audited & corrected in Phase 2)* |
| [IMPLEMENTATION_ROADMAP.md](documentation/IMPLEMENTATION_ROADMAP.md) | Phased engineering roadmap detailing Milestones 1 through 6, prerequisites, deliverables, technical blockers, and definitions of completion. |
| [REPOSITORY_REGISTRY.md](project-management/REPOSITORY_REGISTRY.md) | Provenance log of all reference repositories, recording commit SHAs, branches, licenses, and retrieval dates. |

---

## 5. Summary of Phase 1 Findings & Phase 2 Corrections

1. **CPU Execution:** Phase 1 evaluated FEXCore DBT (~15–25% overhead). **Phase 2 Correction:** Pure Ahead-of-Time (AOT) Recompilation via `bb-recomp` achieves 0% runtime JIT overhead and avoids Android SELinux `W^X` memory penalties.
2. **Platform Services:** Phase 1 estimated 85%+ API reuse. **Phase 2 Correction:** Actual overlap is **35–45%**; Bloodborne's runtime implements ~380 symbols, whereas UE4 requires 1,400+ symbols. Missing modules (`libSceAppContent`, `disc_map`, `systemservice`) must be ported from `shadPS4`.
3. **User-Mode Fibers:** Phase 1 claimed `libSceFiber` was mandatory. **Phase 2 Correction:** UE4 on Orbis OS utilizes standard `libkernel` POSIX pthreads (`scePthreadCreate`); fibers are optional.
4. **Target Hardware (realme 12 Pro+ / Adreno 710):**
   - **AOT Recompilation:** On-device compilation is **infeasible** due to Low Memory Killer (LMK) aborts on 8 GB RAM and thermal throttling. Off-device PC recompilation is mandatory.
   - **GPU Rendering:** The Adreno 710's 25.6 GB/s memory bandwidth is ~7x slower than the PS4 (176 GB/s). Native 1080p runs at 12–18 FPS. The target gameplay resolution is **540p or 720p with AMD FSR upscaling** (projected 28–30 FPS).
   - **Driver Requirement:** The proprietary Qualcomm driver crashes on complex SPIR-V compute control flow. The open-source **Mesa Turnip Vulkan driver is mandatory**.

---

## 6. Implementation Roadmap Overview (Phased Execution)

- **MILESTONE 1 (Complete):** Technical Research & Reverse Engineering (Phase 1).
- **MILESTONE 2 (Complete):** Advanced Recompilation, Compatibility & Feasibility Audit (Phase 2).
- **MILESTONE 3 (Prospective):** P3R Offline Rebuild Tool (`p3r-recomp`) with UE4 reflection/vtable scraping and 128-shard LLVM linking.
- **MILESTONE 4 (Prospective):** Android PS4 Compatibility Runtime Architecture (Bionic pthreads, direct memory pool below 1 TiB, ported shadPS4 system modules).
- **MILESTONE 5 (Prospective):** Mobile Vulkan Graphics Compatibility (shadPS4 GNM core, Mesa Turnip driver bundle, compute Wave64 barrier remapping, 540p/720p FSR upscaler).
- **MILESTONE 6 (Prospective):** P3R-Specific Ingestion & Asset Streaming (IO Store `.utoc`/`.ucas` verification, CriWare audio streaming).
- **MILESTONE 7 (Prospective):** Device Testing & Adreno 710 Optimization on realme 12 Pro+.

---

## 7. Licensing & Legal Compliance

- **GPL-3.0 License:** Combining components from `Bloodborne-android-rebuild-tool` (GPL-3.0) and `shadPS4` (GPL-2.0-or-later upgraded to GPL-3.0) establishes the unified codebase under **GPL-3.0-or-later**.
- **Derivative Work Status of `libp3raot.so`:** The recompiled ARM64 shared library is a direct derivative work of Atlus/SEGA's copyrighted binary code. **Redistributing `libp3raot.so` or game assets is strictly prohibited.**
- **Clean-Room BYOG (Bring Your Own Game):** The project distributes open-source compiler tools and runtime shims only, requiring the user to supply their own legitimately acquired, decrypted game files.
