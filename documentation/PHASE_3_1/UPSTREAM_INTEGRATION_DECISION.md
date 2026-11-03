# Phase 3.1: Upstream Integration & Architecture Decision

## Executive Summary

Phase 3 and Phase 3.1 established that Ahead-of-Time (AOT) recompilation from x86-64 to AArch64 is technically viable and achieves $100\%$ bit-exact execution on synthetic C test suites.

However, scaling from synthetic test fixtures (5 functions, $\approx 500$ instructions) to a full commercial release of **Persona 3 Reload** (an Unreal Engine 4.27 title comprising over $100,000$ functions, millions of x86-64 instructions, complex thread fibers, and specialized SIMD vectors) presents an enormous leap in architectural complexity.

This document evaluates the three viable technical trajectories:
- **Option A:** Continue expanding this custom prototype recompiler.
- **Option B:** Integrate an existing production-grade IR lifter (FEXCore) or the upstream Bloodborne rebuild tool.
- **Option C:** Develop a clean-sheet, dedicated P3R recompiler from scratch.

A definitive architectural recommendation is established based on technical feasibility, coverage, maintenance overhead, and performance on the Snapdragon 7s Gen 2 platform.

---

## Evaluation of Strategic Options

### Option A: Expand Custom Prototype Recompiler
- **Description:** Incrementally add x86-64 instruction lowering rules to `lower.py` and expand `p3r_recomp.py` to lift commercial game binaries.
- **Advantages:**
  - Complete control over the LLVM IR representation and code generation pipeline.
  - Zero external dependency bloat; straightforward Python/llvmlite codebase.
  - Custom tailoring to P3R-specific calling conventions and data structures.
- **Disadvantages:**
  - **Massive Instruction Set Burden:** x86-64 contains over 1,500 instruction encodings and thousands of subtle edge cases (e.g. precise condition code flags on bit tests, partial register stalls, complex address modes). Hand-authoring these in Python requires tens of thousands of developer hours.
  - **Maintenance Overhead:** High probability of latent semantic bugs (e.g. condition code differences, floating-point rounding modes) that cause silent game logic desynchronization.
  - **Low Recompilation Throughput:** Python-based AST lowering achieves $\approx 10,000$ instructions/sec. Recompiling P3R's $\approx 35\text{ MB}$ `.text` section ($\approx 8\text{ million}$ instructions) would take over 15 minutes per build.
- **Verdict:** **UNSUITABLE FOR PRODUCTION**. Acceptable as an educational prototype and validation testbed, but inadequate for a multi-gigabyte UE4 commercial binary.

---

### Option B: Integrate Production-Grade Lifter (FEXCore / Bloodborne-Rebuild Upstream)
- **Description:** Adapt an established, battle-tested x86-64 lifting engine—specifically **FEXCore** (from the FEX-Emu project) or the **Bloodborne-android-rebuild-tool** (which leverages FEX-derived lifting into an LLVM backend).
- **Advantages:**
  - **Comprehensive Instruction Coverage:** FEXCore already supports virtually the entire x86-64 ISA, including SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2, AVX, and basic AVX2.
  - **Flag Synthesis:** FEXCore has optimized algorithms to defer and lazily evaluate x86 condition flags (RFLAGS), drastically reducing redundant flag computations compared to naïve lowering.
  - **Native C++ Performance:** Compiles in native C++, processing hundreds of thousands of instructions per second.
  - **Proven Precedent:** The Bloodborne Android project demonstrated that FEXCore lifting + LLVM AArch64 code generation successfully runs a complex commercial PS4 game on Android.
- **Disadvantages:**
  - Requires maintaining a C++ toolchain integration.
  - Upstream Bloodborne recompiler is tailored to FromSoftware's proprietary engine (`eboot.bin` layout, specific CRT routines) and requires refactoring for Unreal Engine 4.
- **Verdict:** **RECOMMENDED STRATEGY**. Leverages mature upstream compiler engineering while allowing customization for UE4.

---

### Option C: Clean-Sheet Dedicated P3R Recompiler
- **Description:** Build a brand new native C++ compiler tailored exclusively to Persona 3 Reload's executable and Unreal Engine 4.
- **Advantages:**
  - Can exploit UE4-specific engine invariants (e.g. known standard allocator patterns, known threading models).
- **Disadvantages:**
  - Re-invents the wheel on x86-64 decoding, IR lifting, and flag synthesis.
  - Longest lead time to an initial playable milestone (estimated 12–18 months for compiler alone).
- **Verdict:** **NOT RECOMMENDED**. High risk of project abandonment due to front-loaded compiler development effort.

---

## Comparative Matrix

| Evaluation Criterion | Option A: Custom Prototype | Option B: Upstream FEX/Bloodborne | Option C: Clean-Sheet C++ |
|---|:---:|:---:|:---:|
| **ISA Completeness** | Low ($< 10\%$ of ISA) | **Very High ($> 95\%$ of ISA)** | Low initially |
| **Development Velocity** | Slow (manual rule writing) | **Rapid (mature lifter available)** | Very slow |
| **Recompilation Throughput** | $\approx 10\text{k insns/s}$ (Python) | **$> 200\text{k insns/s}$ (Native C++)** | High |
| **Unreal Engine 4 Suitability** | Poor (insufficient ISA) | **High (handles UE4 SIMD/Atomics)** | Medium |
| **Snapdragon 7s Gen 2 Optimization**| Basic LLVM -O2 | **Advanced (tuned vectorization)** | High |
| **Project Risk** | High | **Low–Medium** | Extreme |

---

## Unreal Engine 4.27 Architectural Requirements for P3R

Persona 3 Reload is developed on a modified fork of **Unreal Engine 4.27**. Transitioning the AOT recompiler to P3R requires addressing four engine-specific subsystems:

### 1. TaskGraph & Fiber Threading
- Unreal Engine 4 implements a user-mode task scheduler (`TaskGraph`) that dynamically distributes rendering, physics, and gameplay tasks across worker threads.
- **Recomp Requirement:** Guest thread stacks must be cleanly swappable. Our Phase 3.1 `GuestState` model (with explicit `RSP`/`RBP` registers in memory) provides the necessary context-switching primitives.

### 2. Virtual Memory Management (`FVirtualMemory`)
- UE4 relies heavily on virtual memory address reservation (`mmap` / `VirtualAlloc`) for its custom Bink video, sound streaming, and level chunk allocators.
- **Recomp Requirement:** The recompiled runtime must provide a 64-bit virtual memory mapping layer that preserves 4GB–16GB guest address ranges on Android without colliding with host Bionic allocations.

### 3. SIMD & Math Libraries (UnrealMath)
- UE4 heavily utilizes SSE/SSE4 vector intrinsics for 3D matrix transformations, bounding box frustum culling, and vertex skinning.
- **Recomp Requirement:** Full support for `_mm_add_ps`, `_mm_mul_ps`, `_mm_shuffle_ps`, and dot products (`dpps`). Option B provides these out of the box.

### 4. Garbage Collection Stack Scanning
- Unreal Engine's Garbage Collector scans the CPU call stack to identify live `UObject` references.
- **Recomp Requirement:** If guest return addresses are stored on the guest stack, the GC scanner must be able to read guest stack pointers without triggering host page faults.

---

## Definitive Strategic Recommendation: The Hybrid Architecture

The project shall adopt a **Hybrid Architecture** combining the best aspects of Option B and our Phase 3.1 findings:

```
[ PS4 x86-64 Decrypted ELF ]
              │
              ▼
   [ FEXCore Native Lifter ]  ──► Decodes x86-64, synthesizes flags, produces IR
              │
              ▼
    [ LLVM AArch64 Backend ]  ──► Emits optimized AAPCS64 machine code (PIC, -lse)
              │
              ▼
[ P3R Native Runtime (Phase 3.1) ] ──► Freestanding runtime, bbr_lookup, GuestState
              │
              ▼
   [ Android Target Execution ]  ──► realme 12 Pro+ (Snapdragon 7s Gen 2 / Adreno 710)
```

1. **Frontend:** Adopt the FEXCore instruction lifting frontend for industrial-strength x86-64 decoding, condition code flag optimization, and AVX/SSE vector coverage.
2. **Backend:** Retain the LLVM code generator configured with Phase 3.1's verified AAPCS64 conventions (`-target aarch64-linux-android30`, `-fPIC`, `-Wl,-Bsymbolic`).
3. **Runtime:** Retain Phase 3.1's Recomp ABI v2 `GuestState` layout, freestanding math libraries (`guest_cpu.c`), and memory address translation layer (`mem_base`).
