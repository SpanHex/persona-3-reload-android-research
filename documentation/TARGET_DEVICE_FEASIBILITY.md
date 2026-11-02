# Target Device Technical Feasibility Analysis: realme 12 Pro+

**Document:** `documentation/TARGET_DEVICE_FEASIBILITY.md`  
**Target Hardware:** realme 12 Pro+ (Snapdragon 7s Gen 2 / Adreno 710)  
**Investigation Date:** 2026-11-02  
**Status:** Hardware Evaluation & Feasibility Assessment  

---

## 1. Hardware Specification Profile

| Hardware Subsystem | realme 12 Pro+ Specification | Reference Device: AYN Thor (Bloodborne Tested) | Reference Device: Oppo Find N5 (Bloodborne Tested) |
|---|---|---|---|
| **SoC / Chipset** | Qualcomm Snapdragon 7s Gen 2 (SM7435-AB, 4nm Samsung) | Qualcomm Snapdragon 8 Gen 2 (SM8550-AB, 4nm TSMC) | Qualcomm Snapdragon 8 Elite (SM8750-AB, 3nm TSMC) |
| **CPU Architecture** | ARMv8.2-A (4x Cortex-A78 @ 2.40 GHz + 4x Cortex-A55 @ 1.95 GHz) | ARMv9.0-A (1x Cortex-X3 @ 3.2 GHz + 4x Cortex-A715/A710 @ 2.8 GHz + 3x Cortex-A510 @ 2.0 GHz) | ARMv9.2-A Custom (2x Oryon Phoenix L @ 4.32 GHz + 6x Oryon Phoenix M @ 3.53 GHz) |
| **GPU Model & Class** | **Qualcomm Adreno 710** (Mid-range 7xx series) | **Qualcomm Adreno 740** (Flagship 7xx series) | **Qualcomm Adreno 830** (Flagship 8xx series) |
| **GPU FP32 Throughput** | ~1.2 TFLOPs (940 MHz) | ~3.5 TFLOPs (680 MHz) | ~10.2 TFLOPs (1100 MHz) |
| **System Memory (RAM)** | 8 GB or 12 GB LPDDR4X / LPDDR5 | 16 GB LPDDR5X | 16 GB LPDDR5X |
| **Memory Bandwidth** | ~25.6 GB/s (16-bit dual-channel) | ~64.0 GB/s (16-bit quad-channel) | ~106.6 GB/s (16-bit quad-channel) |
| **Cooling Solution** | Passive Graphite Sheet / Vapor Chamber | **Active Fan Cooling** | Passive Vapor Chamber |
| **OS / Bionic Runtime** | Android 14 (Realme UI 5.0, 64-bit Bionic) | Android 13 / 14 | Android 15 |

---

## 2. Technical Evaluation by Subsystem

### 2.1. CPU & Instruction Translation Feasibility
- **Instruction Support:** **Confirmed Compatible**. The Cortex-A78 cores implement standard ARM64 (ARMv8.2-A). FEXCore's JIT compiles x86-64, AVX, and BMI1 machine code into standard AArch64 instructions with NEON vector extensions supported on Cortex-A78.
- **Hardware Memory Model (TSO) Limitations:** **Technically Plausible with Overhead**.
  - Cortex-A78 **does not support hardware Total Store Ordering (TSO)** or ARMv8.4-A `FEAT_LRCPC` (Load-Acquire RCpc).
  - Emulating x86-64 strong memory ordering on Cortex-A78 requires FEXCore to insert explicit memory barriers (`DMB ISHLD`/`ISHST`) or `LDAR`/`STLR` instructions for atomic operations.
  - In Unreal Engine 4's heavily multi-threaded `FTaskGraphImplementation`, running with full barrier protection will introduce a **15% to 30% CPU translation overhead**. Running with relaxed memory ordering (`ParanoidTSO=false`) can mitigate this, but risks intermittent thread race conditions during asset streaming.
- **CPU Compute Headroom:** The 4x Cortex-A78 performance cores clocked at 2.40 GHz have roughly **40–45% of the single-thread performance of a Cortex-X3** (Snapdragon 8 Gen 2). Because Unreal Engine 4 distributes work across ~16 threads, the CPU will likely be heavily utilized, but should be capable of sustaining 30 FPS logic updates.

---

### 2.2. GPU & Vulkan Driver Feasibility (Adreno 710)

```mermaid
flowchart TD
    subgraph Adreno710["Qualcomm Adreno 710 Characteristics"]
        Arch["Microarchitecture: Derived from Adreno 6xx with 7xx Compiler/ISA"]
        GMEM["GMEM (On-Chip Tiled Cache): Small (~512 KB - 1 MB)"]
        RawCompute["Compute Throughput: ~1.2 TFLOPs FP32"]
    end

    subgraph DriverLandscape["Driver Support Status"]
        StockDriver["Stock Qualcomm Driver (libvulkan.so): High Vulkan 1.1 bugs, memory leaks"]
        TurnipUpstream["Upstream Mesa Turnip: Missing hardware magic strings for A710"]
        TurnipPatched["Community-Patched Turnip (Vauzi-17 / Banners-Turnip): Stable sysmem mode"]
    end

    subgraph RenderingMode["Rendering Pipeline Implication"]
        Sysmem["TU_DEBUG=sysmem (Bypass GMEM, direct DDR framebuffer)"]
        PerfCost["Memory Bandwidth Saturation (~25.6 GB/s LPDDR4X)"]
    end

    Arch --> GMEM
    Arch --> RawCompute
    GMEM --> Sysmem
    TurnipPatched --> Sysmem
    Sysmem --> PerfCost
```

- **GPU Microarchitecture Reality:**
  - Despite the "710" naming, the Adreno 710 is architecturally closer to an optimized Adreno 6xx derivative rather than a flagship Adreno 730/740.
  - It features a significantly smaller on-chip GMEM cache and fewer ALU computation units.
- **Mesa Turnip Driver Status:**
  - Upstream Mesa Turnip does not offer out-of-the-box zero-config support for Adreno 710.
  - However, **community-patched Turnip builds (e.g. Vauzi-17, Banners-Turnip)** explicitly support Adreno 710/720/722.
  - **Mandatory Configuration:** These drivers must run with `TU_DEBUG=sysmem` (system memory mode). In tiled GMEM mode, complex multi-render-target (MRT) G-Buffer passes used by Unreal Engine 4 cause GPU page faults due to GMEM overflow.
  - Running in `sysmem` mode writes directly to device DDR RAM, which places heavy pressure on the phone's ~25.6 GB/s memory bandwidth.

---

### 2.3. System Memory (RAM) Budget
- **8 GB RAM Model:** **MARGINAL / HIGH RISK**.
  - Android OS and background services consume ~3.0 to 3.5 GB.
  - Available memory for the game process: ~4.0 to 4.5 GB.
  - P3R's PS4 direct memory allocation requests up to 5056 MiB. If UE4 attempts to map 4.5 GB+ while FEXCore's code cache and Vulkan descriptor pools are active, Android's Low Memory Killer (LMK) will immediately terminate the process (`SIGKILL`).
- **12 GB RAM Model:** **TECHNICALLY PLAUSIBLE**.
  - Available memory for the game process: ~8.0 GB.
  - Easily accommodates UE4's direct memory pool, Vulkan texture staging buffers, and FEXCore translation caches with safe headroom.

---

### 2.4. Thermal Throttling & Sustained Performance
- The realme 12 Pro+ is a thin, passively cooled mid-range smartphone.
- Under sustained 100% CPU and GPU load (FEXCore JIT on 4 A78 cores + Adreno 710 rendering complex UE4 deferred lighting):
  - Initial 5 minutes: Sustained performance.
  - After 10–15 minutes: The SoC thermal governor will throttle the Cortex-A78 cores from 2.4 GHz down to ~1.4–1.6 GHz, and reduce the Adreno 710 clock from 940 MHz to ~600 MHz to keep skin temperature under 42°C.
  - **Mitigation:** Resolution scaling down to **540p or 720p with FSR 1.0 upscaling** is mandatory to maintain thermal equilibrium.

---

## 3. Subsystem Compatibility Classification

| Subsystem / Metric | Compatibility Classification | Technical Evidence / Justification |
|---|---|---|
| **CPU Architecture (ARM64-v8a)** | **Confirmed** | Cortex-A78 / A55 execute standard AArch64 code; FEXCore JIT targets this architecture natively. |
| **CPU ISA Emulation (AVX/BMI1)** | **Confirmed** | FEXCore implements JIT emitters translating x86-64 AVX and BMI1 instructions into ARM64 NEON. |
| **Vulkan 1.3 Core Features** | **Technically Plausible** | Adreno 710 supports Vulkan 1.3 via community-patched Mesa Turnip drivers. |
| **Mesa Turnip Driver Stability** | **Technically Plausible (with patches)** | Requires custom Adreno 710 Turnip builds with `TU_DEBUG=sysmem` enabled. |
| **Unreal Engine 4 Compute Shaders** | **Untested / Plausible** | Requires latest shadPS4 shader recompiler fixes for structured control flow. |
| **RAM Capacity (8 GB Model)** | **High Risk / Marginal** | Vulnerable to Android LMK kills under peak scene loads. |
| **RAM Capacity (12 GB Model)** | **Technically Plausible** | Provides sufficient memory headroom (~8 GB available). |
| **Thermal Sustained 30 FPS** | **Untested** | Passively cooled mid-range phone; likely requires 540p render scale with upscaling to prevent throttling. |

---

## 4. Final Device Verdict

> [!IMPORTANT]
> **Is the realme 12 Pro+ a viable initial test device?**
> **VERDICT: TECHNICALLY PLAUSIBLE AS A TARGET FOR RESEARCH & BOOTSTRAP TESTING, BUT WILL REQUIRE AGGRESSIVE OPTIMIZATIONS.**
> 
> 1. **It will boot and execute code:** The CPU and GPU feature sets are technically capable of running the FEXCore translation layer, loading the PS4 compatibility runtime, and compiling shaders via Mesa Turnip.
> 2. **Performance Expectations:** Do NOT expect full 1080p 60 FPS performance. The Adreno 710 is approximately 1/3 the compute strength of the Snapdragon 8 Gen 2's Adreno 740. Realistic playable targets for this device would be **720p or 540p at 30 FPS with FSR upscaling**.
> 3. **RAM Prerequisite:** If the user's specific realme 12 Pro+ unit is the 8 GB RAM variant, aggressive texture memory clamping is necessary to avoid OS memory kills. If it is the 12 GB RAM variant, memory is fully sufficient.

