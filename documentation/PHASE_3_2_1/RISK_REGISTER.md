# PROJECT RISK REGISTER & MITIGATION STRATEGY
**Phase 3.2.1 — Evidence-Based Android Validation & Runtime Corrections**
**Document ID:** `P3R-DOC-321-RISK`
**Date:** 2026-11-04
**Status:** ACTIVE & AUDITED

---

## 1. Executive Summary

This Risk Register documents the technical, architectural, hardware, and operational risks identified during Phase 3.2.1.
Each risk is evaluated using strict evidence standards, eliminating false assumptions of success and detailing actionable mitigation pathways prior to initiating binary analysis on commercial game data.

---

## 2. Risk Classification Matrix

| Risk ID | Title | Category | Severity | Probability | Impact Score | Current Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RSK-321-01** | Physical Realme 12 Pro+ Hardware Disconnection | Hardware | **HIGH** | High (Current) | **HIGH** | `UNRESOLVED / PENDING` |
| **RSK-321-02** | x86 TSO vs ARM64 Weak Memory Model Hazards | Architecture | **HIGH** | Medium | **HIGH** | `MONITORED` |
| **RSK-321-03** | Dynamic Linker Library Count Exhaustion | Android OS | **HIGH** | High (Game Scale) | **HIGH** | `MITIGATION DESIGNED` |
| **RSK-321-04** | Indirect Dispatch Scalability Overhead | Performance | **MEDIUM** | High (Game Scale) | **MEDIUM** | `PROTOTYPED` |
| **RSK-321-05** | Guest Memory Base Relocation & 48-bit ASLR | Systems | **MEDIUM** | Low | **MEDIUM** | `VERIFIED IN POC` |
| **RSK-321-06** | Unreal Engine 4 GNM Shader Translation (Phase 4)| Graphics | **CRITICAL** | High | **CRITICAL** | `OUT OF SCOPE (PHASE 4)`|

---

## 3. Detailed Risk Analysis & Mitigations

### RSK-321-01: Physical Realme 12 Pro+ Hardware Disconnection
- **Description:** No physical Android device is connected to the ADB bus. All tests currently rely on Unicorn CPU emulation and host NDK build verification.
- **Impact:** Cannot observe hardware thermal throttling, Big.LITTLE core migration, hardware cache coherence contention, or Adreno GPU driver quirks.
- **Mitigation:**
  1. The complete Android application (`app-debug.apk`) and standalone Bionic runner (`p3r_bionic_runner`) are pre-compiled and packaged.
  2. Documented step-by-step deployment scripts in `REALME_DEVICE_VALIDATION.md` enable immediate one-command testing once hardware is plugged in.
  3. Physical execution is marked `NOT_TESTED` without fabrication.

### RSK-321-02: x86 TSO vs ARM64 Weak Memory Model Hazards
- **Description:** x86-64 provides Total Store Order (TSO) semantics where stores are committed in-order. ARM64 has a Weak Memory Model that permits aggressive store-store and load-load reordering unless synchronized by explicit barriers.
- **Impact:** Lifted x86-64 code that relies on implicit TSO without explicit `lock` prefixes could exhibit subtle race conditions on multi-core ARM64 hardware.
- **Mitigation:**
  1. All explicit `lock` prefixed operations (`xadd`, `cmpxchg`, `xchg`) are lowered with LLVM `SequentiallyConsistent` ordering, emitting `ldaxr`, `stlxr`, and `dmb ish`.
  2. Persona 3 Reload uses Unreal Engine 4's task graph and threading abstractions (`FCriticalSection`, `FEvent`, `TQueue`), which rely on explicit hardware atomic primitives rather than informal lock-free TSO assumptions.
  3. Contention testing is integrated into `bionic_runner.c` for immediate execution on physical multi-core hardware.

### RSK-321-03: Dynamic Linker Library Count Exhaustion
- **Description:** In synthetic testing, each fixture is linked as an individual `.so`. A commercial game containing 15,000+ functions would exhaust Android Bionic's maximum open library limits (`dlopen` file descriptor limits, internal linker namespace limits).
- **Impact:** Dynamic linking failure or out-of-memory errors in `/system/bin/linker64`.
- **Mitigation:**
  1. For production game recompilation, the compiler will emit unified translation units (e.g. 5–10 large modular shared libraries partitioned by game module: `p3r_core.so`, `p3r_render.so`, `p3r_audio.so`).
  2. Static intra-module function calls will be directly linked via PC-relative branches (`bl`), bypassing `dlopen` entirely.

### RSK-321-04: Indirect Dispatch Scalability Overhead
- **Description:** The synthetic POC uses a linear search in `bbr_lookup` across `g_bbr_units[]`. For a small test with 10 functions, linear search takes < 1 µs. For a commercial binary with 50,000 functions, linear search would cause severe CPU frame stalls.
- **Impact:** Unacceptable CPU overhead during virtual function calls and dynamic dispatch.
- **Mitigation:**
  1. Implement a two-level radix direct page table or perfect hash table for O(1) function lookups.
  2. Implement inline caching at indirect call sites to cache the last-resolved target address.

### RSK-321-05: Guest Memory Base Relocation & 48-bit ASLR
- **Description:** PS4 software expects a 47-bit virtual address space. Android 64-bit kernels allocate virtual addresses in the 48-bit space and employ aggressive Address Space Layout Randomization (ASLR).
- **Impact:** Hardcoded 32-bit or sign-extended pointer offsets could fault if the host allocator places the guest memory arena above $2^{47}$.
- **Mitigation:**
  1. `GuestState` explicitly stores `mem_base` (offset 0x2B8).
  2. All guest memory accesses are lower-computed as `mem_base + guest_vaddr`.
  3. Validated in Fixture 03 (`03_memory_reloc`) across arbitrary base pointers.

### RSK-321-06: Unreal Engine 4 GNM Shader Translation (Phase 4 Handoff)
- **Description:** Persona 3 Reload's graphics backend uses PS4-native GNM/GNMX commands and AMD GCN bytecode. AOT recompilation only addresses the x86-64 CPU instruction set.
- **Impact:** The game cannot render visual frames until the GCN-to-SPIR-V translation and Vulkan descriptor pipeline is developed.
- **Mitigation:**
  1. CPU recompilation is decoupled from graphics translation.
  2. Research findings from Phase 1 and Phase 2 (leveraging shadPS4's Vulkan translation layers) will serve as the architectural foundation for Phase 4.

---

## 4. Risk Review Lifecycle

This Risk Register will be maintained across subsequent phases:
- **Phase 3.2.1:** Resolve ABI alignment, remove fake stubs, build APK, differential test all 6 fixtures.
- **Device Attachment:** Execute `p3r_bionic_runner` and `app-debug.apk` on physical realme 12 Pro+ to close `RSK-321-01`.
- **Phase 4:** Expand into modular binary chunking (`RSK-321-03`) and O(1) dispatch tables (`RSK-321-04`).
