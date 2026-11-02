# Final Technical Feasibility Report: Persona 3 Reload (PS4 to Android)

**Document:** `documentation/FINAL_FEASIBILITY_REPORT.md`  
**Project:** Persona 3 Reload — PS4 to Android Research (Phase 1)  
**Author:** Senior Reverse-Engineering Researcher & Native Systems Architect  
**Investigation Date:** 2026-11-02  
**Status:** Complete Technical Feasibility Assessment  

---

## 1. Executive Feasibility Statement

An Android compatibility runtime capable of executing the PlayStation 4 version of *Persona 3 Reload* on high-end ARM64 Android devices is **TECHNICALLY PLAUSIBLE, BUT REPRESENTS A HIGH-DIFFICULTY GRAPHICS & MEMORY ENGINEERING EFFORT.**

The project is **not** an emulator of the complete PS4 console; rather, it is a **dedicated game-porting compatibility runtime** combining:
- **Dynamic Binary Translation (DBT):** FEXCore translates only the game's x86-64 CPU code (`eboot.bin`, `libc.prx`, `libSceFios2.prx`).
- **Native OS Replacements:** 85%+ of PS4 OS services (`libkernel`, pthreads, `libScePad`, `libSceAudioOut`, `libSceSaveData`) execute natively as ARM64 Bionic code via an architecture proven by Bloodborne Android.
- **Vulkan Graphics Translation:** shadPS4's Liverpool PM4-to-Vulkan video core translates GNM draw calls to Vulkan 1.3, backed by Mesa Turnip drivers on Qualcomm Adreno GPUs.

---

## 2. Answers to the 12 Core Feasibility Questions

### Question 1: Is a P3R PS4 to Android implementation technically plausible?
**Verdict:** **TECHNICALLY PLAUSIBLE.**  
- **Verified Facts:** 
  - Bloodborne Android (`references/bloodborne-android`) has verified that an x86-64 PS4 retail game can run on Android ARM64 hardware through FEXCore and shadPS4's Liverpool Vulkan core.
  - shadPS4 upstream has verified that *Persona 3 Reload* (CUSA37522 / CUSA43889) successfully boots, passes menus, and reaches active gameplay (`status-ingame`) through its PM4 and shader translation pipeline.
  - Persona 3 Reload uses Unreal Engine 4.27 on PS4 with no Denuvo Anti-Tamper, standard SysV ELF dynamic linking, and standard GNM PM4 submissions.
- **Strong Technical Inferences:** Combining the native ARM64 runtime architecture of Bloodborne Android with the latest shadPS4 video core will allow P3R to boot and render on ARM64 Android.
- **Hypothesis:** Sustained 30 FPS gameplay is achievable on Snapdragon 8 Gen 2/3/Elite devices at 720p/1080p with FSR upscaling.

---

### Question 2: Can FEXCore be used for the CPU translation layer?
**Verdict:** **YES, CONFIRMED.**  
- **Verified Facts:**
  - P3R's PS4 binary is compiled for the AMD Jaguar CPU, which features x86-64, SSE4.2, AVX (128-bit VEX), and BMI1 (`andn`, `bextr`, `blsr`, `tzcnt`).
  - FEXCore (`references/fexcore`) provides comprehensive Arm64 JIT emitters for these exact instruction sets in `FEXCore/Source/Interface/Core/JIT/VectorOps.cpp` and `ALUOps.cpp`.
  - Bloodborne Android's `cpu/guest_cpu_fex.cpp` and `cpu/host_call_arm64.S` prove that FEXCore can be embedded as a static/dynamic library in an Android game process, translating only guest x86-64 code while leaving the runtime, renderer, and OS interfaces in native ARM64.
- **Strong Technical Inference:** FEXCore JIT translation will introduce a modest ~15–25% CPU overhead on modern ARM64 performance cores, leaving sufficient CPU budget for Unreal Engine's TaskGraph workers.

---

### Question 3: Can the Bloodborne Android runtime architecture be adapted?
**Verdict:** **YES, HIGH DEGREE OF REUSABILITY.**  
- **Verified Facts:**
  - Bloodborne Android's low-overhead native C runtime (`src/runtime.c`, `runtime_kernel.c`, `runtime_memory.c`, `runtime_file.c`, `runtime_pad.c`, `runtime_audio.c`) maps 750+ PS4 NIDs directly to Bionic pthreads, Linux file descriptors, and anonymous memory mappings.
  - Its 16-byte `syscall` stub table (`cpu/guest_cpu_fex.cpp#L77-L86`) provides a zero-overhead ABI bridge between x86-64 guest code and ARM64 host functions.
  - Its zero-copy presentation engine (`tools/android/frontend/jni/bbpresent/bbpresent.c`) uses Android `ASurfaceControl` and `AHardwareBuffer` to present frames directly to `SurfaceFlinger`.
- **Required Modifications:** Expand memory pool ceilings, enlarge import stub capacities, and integrate fiber context handling.

---

### Question 4: Can shadPS4's graphics implementation be adapted?
**Verdict:** **YES, WITH REQUIRED UPSTREAM SYNCHRONIZATION.**  
- **Verified Facts:**
  - Both Bloodborne Android and Shadow of the Colossus PC vendor shadPS4's Liverpool GPU video core (`gpu/shadps4/`).
  - It successfully translates AMD GCN PM4 command buffers (`PACKET3_DRAW_INDEX_AUTO`, `PACKET3_SET_CONTEXT_REG`, `PACKET3_DISPATCH_DIRECT`) to Vulkan 1.3 pipelines.
- **Identified Gap:** The video core vendored in Bloodborne Android is locked to commit `b4e7ae7` (October 2026). Unreal Engine 4 requires newer compute shader control-flow fixes and descriptor indexing improvements present in modern shadPS4 main.

---

### Question 5: What does P3R require that Bloodborne does not implement?
**Verdict:** **FIVE PRIMARY MISSING COMPONENTS IDENTIFIED.**  
1. **`libSceFiber` (PS4 User-Mode Fibers):** Unreal Engine 4 uses fibers for cooperative task scheduling. Bloodborne never calls `libSceFiber`; however, **Shadow of the Colossus PC implements it in `src/runtime_fiber.c`**. This must be ported and integrated with FEXCore.
2. **Direct Memory Ceiling (> 5 GiB):** Bloodborne runs within the retail PS4 default 5056 MiB direct memory limit. UE4 world streaming and asset caches require expanding this pool to 6–8 GiB.
3. **Complex Compute Shader Pipelines:** P3R uses heavy compute passes for Niagara particle simulation, cel-shading outlines, and deferred tiled lighting.
4. **Unreal Engine IO Store Filesystem:** P3R uses `.utoc` and `.ucas` container formats inside `/app0/P3R/Content/Paks/`, demanding sustained multi-threaded read throughput from `runtime_file.c`.
5. **Atlus / UE4 Specific NIDs:** Additional minor system calls (e.g. `sceKernelIsNeoMode`, `sceKernelGetAppInfo`, `sceUserServiceGetInitialUser`).

---

### Question 6: What changes are needed for Unreal Engine-based rendering?
**Verdict:** **CRITICAL GRAPHICS RECOMPILER ADJUSTMENTS.**  
1. **Structured Control Flow in Shaders:** Resolve `AF:structured_control_flow` assertions by pulling shadPS4 upstream dominator-tree control flow analysis.
2. **Vertex Fetch Descriptors:** Handle untyped and non-standard stride vertex buffers emitted by UE4's `CPS4DynamicRHI`.
3. **Multiple Render Target (MRT) Emulation:** P3R's deferred renderer writes to 4–6 G-Buffer attachments simultaneously (BaseColor, Normals, Roughness/Metallic, Custom Stencil, Depth).
4. **Vulkan Descriptor Indexing & Sampler Aliasing:** Ensure full Vulkan 1.3 `descriptorIndexing` and `customBorderColor` support via Mesa Turnip.

---

### Question 7: Can the current Android application architecture be reused?
**Verdict:** **YES, 90%+ REUSABLE.**  
- **Verified Facts:**
  - Bloodborne Android's `MainActivity.java`, `AutoDriver.java`, `DriverManager.java`, and `TouchControllerOverlay.java` provide a complete native Android launcher.
  - The decoupled process model (Application UI process communicating with the native game process via UNIX domain sockets) ensures that Android lifecycle events do not corrupt native game memory.
  - Persona 5 Royal Android's `ControlsEditor.java` and `SaveFiles.java` provide additional reference implementations for touch customization and save management.

---

### Question 8: What components need to be independently developed?
**Verdict:** **FOUR NEW / ADAPTED COMPONENTS.**  
1. **`p3r-prepare` Tool:** An adapted version of `bb_prepare.cpp` specialized to parse and link P3R's UE4 `eboot.bin`, `libc.prx`, and `libSceFios2.prx`.
2. **FEXCore Guest-Aware Fiber Switcher:** A bridge enabling `sotc_fiber_setjmp` / `longjmp` to safely swap FEXCore's simulated `CPUStateFrame` registers and stack pointers.
3. **Expanded Memory Allocator:** A dual-view direct memory allocator in `runtime_memory.c` supporting 6–8 GiB address reservations below the 1 TiB boundary.
4. **P3R-Specific System Stubs:** Implementations or stubs for missing UE4/P3R NIDs in `runtime_services.c`.

---

### Question 9: What are the biggest engineering blockers?
**Verdict:** **RANKED ORDER OF RISK:**  
1. **BLOCKER 1 (CRITICAL - Graphics):** Shader recompiler bugs resulting in vertex explosions or crashes during compute shader execution (`AF:structured_control_flow`).
2. **BLOCKER 2 (HIGH - Memory):** RAM exhaustion on 8 GB mobile devices leading to Android Low Memory Killer (`SIGKILL`) termination.
3. **BLOCKER 3 (MEDIUM - Concurrency):** Race conditions or deadlocks in UE4's lock-free TaskGraph caused by weakly-ordered ARM64 memory reordering.
4. **BLOCKER 4 (LOW - Audio/Video):** Audio synchronization during CRI Sofdec2 `.usm` video cutscene playback.

---

### Question 10: What hardware would be required?
**Verdict:** **MINIMUM VS. RECOMMENDED HARDWARE PROFILES:**  
- **Minimum Viable Hardware (30 FPS @ 540p / 720p with FSR):**
  - SoC: Qualcomm Snapdragon 7s Gen 2 / 7+ Gen 2 / 8 Gen 1.
  - GPU: Qualcomm Adreno 710 / 725 / 730 with Mesa Turnip driver support.
  - RAM: 8 GB physical RAM (with aggressive texture downscaling).
  - Storage: UFS 3.1.
- **Recommended Hardware (30–60 FPS @ 1080p Native):**
  - SoC: Qualcomm Snapdragon 8 Gen 2 / 8 Gen 3 / 8 Elite.
  - GPU: Qualcomm Adreno 740 / 750 / 830 with active or heavy vapor chamber cooling.
  - RAM: 12 GB or 16 GB LPDDR5X RAM.
- **Unsupported Hardware:**
  - All **ARM Mali / Immortalis GPUs** (MediaTek Dimensity / Google Tensor) and **PowerVR / Xclipse GPUs**. (Mesa Turnip is strictly Qualcomm Adreno; panVK on Mali lacks necessary Vulkan extensions).

---

### Question 11: Is the realme 12 Pro+ a viable initial test device?
**Verdict:** **TECHNICALLY PLAUSIBLE AS A TESTBENCH, BUT SEVERELY CONSTRAINED.**  
- **SoC:** Snapdragon 7s Gen 2 (4x A78 @ 2.4 GHz + 4x A55 @ 1.95 GHz).
- **GPU:** Adreno 710.
- **Analysis:**
  - It **can execute the CPU translation layer** and **run community-patched Turnip drivers** (`sysmem` mode).
  - It has roughly 1/3 the GPU compute of a Snapdragon 8 Gen 2.
  - It will **not** achieve full 1080p 60 FPS; however, it is viable for verifying boot, testing the loader, evaluating memory mappings, and running low-resolution (540p/720p FSR) render passes.
  - If the user's phone is the **8 GB RAM variant**, OS memory kills are a high operational risk.

---

### Question 12: What source-code, licensing or authorization requirements remain?
**Verdict:** **COMPLIANCE REQUIREMENTS:**  
1. **License Harmonization:** The derived native runtime must be licensed under **`GPL-2.0`** to comply with Bloodborne Android and shadPS4 obligations.
2. **Cleanroom Android Application:** The Java/Kotlin launcher should be decoupled or independently authored to avoid GPL-2.0 vs. GPL-3.0 conflicts with P5R Android.
3. **User-Supplied Game Data (Zero Proprietary Files):** The runtime must never distribute game binaries, assets, firmware, or keys. It operates exclusively on user-provided dumps from legitimate PS4 discs/purchases.

