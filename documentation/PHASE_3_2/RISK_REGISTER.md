# Phase 3.2 Technical Risk Register

## 1. Overview

This risk register tracks critical technical risks identified during Phase 3.2 research and prototyping. As the project advances toward full game binary recompilation (Phase 4), these risks govern engineering priorities and architectural safeguards.

---

## 2. Risk Matrix

| Risk ID | Category | Description | Severity | Likelihood | Impact | Mitigation Strategy |
|---|---|---|---|---|---|---|
| **RSK-301** | Compiler | **Large Binary Scalability:** P3R `eboot.bin` exceeds 80 MB with >1.5M basic blocks. Full-program LLVM module compilation may exceed host RAM or take hours. | HIGH | HIGH | HIGH | Modular recompilation: split binary into discrete code units (e.g. 500 functions per module) and compile to separate `.so` libraries loaded on demand. |
| **RSK-302** | Execution | **Indirect Dispatch Misses:** Computed `jmp *%rax` without static jump tables cannot be resolved Ahead-of-Time, causing `BBR_TRAP_MISS`. | HIGH | MEDIUM | CRITICAL | Implement hybrid fallback: pair AOT recompiled libraries with an embedded FEXCore JIT engine to compile missing basic blocks at runtime. |
| **RSK-303** | Graphics | **Adreno 710 Vulkan Driver Quirks:** Qualcomm Adreno proprietary drivers have known Vulkan descriptor indexing and subpass bugs. | HIGH | HIGH | HIGH | Utilize custom Turnip (Mesa) driver layer or adhere strictly to Vulkan 1.1 baseline with conservative pipeline barrier management. |
| **RSK-304** | Memory | **Android 16 KB Page Kernels:** Upcoming Android 15/16 kernels mandate 16 KB page sizes. Binaries linked with 4 KB segment alignment fail to load. | MEDIUM | MEDIUM | HIGH | Link all shared libraries and executables with `-Wl,-z,max-page-size=16384` to guarantee dual 4 KB and 16 KB compatibility. |
| **RSK-305** | Hardware | **Thermal Throttling on Snapdragon 7s Gen 2:** The 4nm SM7435-AB throttles Cortex-A78 cores from 2.40 GHz to ~1.6 GHz under sustained gaming load (>15 mins). | MEDIUM | HIGH | MEDIUM | Target rock-solid 30 FPS cap initially; implement dynamic resolution scaling and frame pacing in the Vulkan compositor. |
| **RSK-306** | Memory | **RAM Headroom on 8 GB Variant:** P3R game assets, textures, and guest address space require ~4.5–5.5 GB RAM. Background Android services may trigger OOM killer. | HIGH | MEDIUM | HIGH | Implement aggressive ASTC texture compression and memory-mapped asset streaming directly from encrypted package archives. |
| **RSK-307** | Audio | **Proprietary Audio Codecs (ATRAC9):** PS4 audio uses Sony ATRAC9 compression. Software decoding must run with low latency on Cortex-A55 cores. | MEDIUM | LOW | MEDIUM | Integrate existing open-source ATRAC9 decoding libraries (FFmpeg / libatrac9) pre-compiled with NEON optimizations. |

---

## 3. Risk Trend Analysis (Phase 3.1 vs Phase 3.2)

- **RSK-201 (ABI Desynchronization):** *Mitigated & Closed.* Static assertions enforce 720-byte layout and 16-byte alignment at compile time.
- **RSK-202 (Unicorn vs Bionic Divergence):** *Mitigated & Closed.* Standalone `p3r_bionic_runner` and Android App structure proved that Bionic dynamic loading and execution work as intended.
- **RSK-203 (Multi-Threaded Race Conditions):** *Mitigated & Closed.* 4-thread POSIX contention tests demonstrated 100% atomic correctness with zero lost updates.
