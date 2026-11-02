# Cross-Repository Architecture & Component Matrix

**Document:** `documentation/CROSS_REPOSITORY_COMPARISON.md`  
**Repositories Analyzed:**  
- **Bloodborne Android:** `references/bloodborne-android` (Commit `631b3f56`, GPL-2.0)  
- **Shadow of the Colossus PC:** `references/shadow-of-the-colossus-pc` (Commit `cfbbfab9`, GPL-2.0)  
- **Persona 5 Royal Android:** `references/p5r-android` (Commit `5e05e70a`, GPL-3.0)  
- **shadPS4:** `references/shadps4` (Commit `2183807e`, GPL-2.0-or-later)  
- **FEXCore:** `references/fexcore` (Commit `02e24ca5`, MIT)  
**Investigation Date:** 2026-11-02  

---

## 1. Comprehensive Architecture Comparison Matrix

| Architectural Subsystem | Bloodborne Android | Shadow of the Colossus PC | Persona 5 Royal Android | shadPS4 | FEXCore | Reusability for P3R Android | License Compatibility |
|---|---|---|---|---|---|---|---|
| **CPU Execution Engine** | Embedded **FEXCore** JIT (`cpu/guest_cpu_fex.cpp`) with 16-byte `syscall` stubs | **Direct x86-64 Execution** on host PC CPU via function pointer (`probe.c`) | **NX_NCE** native ARM64 Switch execution (`runtime/src/nce/`) | **Host execution** (PC) with software traps (`src/core/`) | **ARM64 JIT Dynamic Binary Translation** (`Source/Interface/Core/JIT/`) | **FEXCore + BB Android ABI bridge** is the ONLY viable path for PS4 on Android. | FEXCore: MIT; BB Android: GPL-2.0. Clean compatibility. |
| **Executable & Module Loader** | Offline pre-linker (`tools/android/prepare/bb_prepare.cpp`) emitting `BBPROBE5` blob | Dynamic ELF/SELF parser & memory mapper (`src/probe.c`) | In-memory NSO/NCA decryptor & ELF mapper (`runtime/src/nce/nso.cpp`) | Full dynamic ELF/PRX linker (`src/core/linker.cpp`, `module.cpp`) | Linux ELF loader for generic x86 programs (`Source/Interface/Core/`) | Adapt **Bloodborne Android's `bb_prepare.cpp`** to support UE4 `eboot.bin` + PRX dependencies. | GPL-2.0. Fully compatible. |
| **PS4 System Library HLE** | Native C runtime (`src/runtime_*.c`) for 750+ NIDs | Extended C runtime (`src/runtime_*.c` + `runtime_sotc.c`) | N/A (Emulates Nintendo Horizon OS `nn::*` APIs) | Full C++ PS4 HLE implementation (`src/core/libraries/`) | N/A (Emulates Linux kernel syscalls) | Merge **BB Android runtime** with **SotC PC's `libSceFiber`** and shadPS4 updates. | GPL-2.0. Fully compatible. |
| **Graphics API Translation** | AMD GCN PM4 command processor to **Vulkan 1.3** (`gpu/shadps4/`) | AMD GCN PM4 command processor to **Vulkan 1.3** (`gpu/shadps4/`) | NVIDIA NVN API to **Vulkan 1.1+** (`runtime/src/nvn/`) | Full Liverpool GPU emulator on **Vulkan 1.3** (`src/video_core/`) | N/A | **shadPS4 Liverpool Vulkan renderer** (vendored in BB Android/SotC PC). | GPL-2.0-or-later. Fully compatible. |
| **Shader Translation Pipeline** | AMD GCN ISA to **SPIR-V** via Sirit (`gpu/shadps4/src/shader_recompiler/`) | AMD GCN ISA to **SPIR-V** with multi-threaded compilation (`gpu/`) | NVIDIA Maxwell ISA to **SPIR-V** via Ryujinx .NET AOT (`libspirvharness.so`) | Comprehensive AMD GCN to **SPIR-V** translator (`src/shader_recompiler/`) | N/A | Update BB Android's shader recompiler to **latest shadPS4 main** to support UE4 compute shaders. | GPL-2.0-or-later. Fully compatible. |
| **GPU Driver Integration** | Direct `dlopen` of bundled **Mesa Turnip** drivers (`tools/android/build_turnip_android.sh`) | System Vulkan ICD loader on Windows | Standard Android `libvulkan.so` system loader | Standard system Vulkan loader (Windows/Linux) | N/A | Adopt **Bloodborne Android's direct Turnip loader** (critical for Adreno stability). | Mesa: MIT/Khronos. Fully compatible. |
| **Virtual Memory Management** | `runtime_low_map` below 1 TiB, direct physical memory aliasing | `VirtualAlloc2` placeholder mapping (4 TiB space) + dual backing | Horizon OS 39-bit address space allocation via `mmap` | Host mmap / VirtualAlloc with page-tracking handlers | Custom host allocator hooks (`FEXCore/Utils/Allocator.h`) | Combine **BB Android's `runtime_low_map`** with **SotC PC's dual-view backing memory**. | GPL-2.0. Compatible. |
| **Audio Subsystem** | Software ATRAC9 decoder + Android `AudioTrack` (`AudioBridge.java`) | ATRAC9 decoder + PS4 console modules (`libSceNgs2.sprx`) | Low-latency **AAudio** backend (`games/p5r/java/`) | Software ATRAC9 + SDL2/Cubeb audio output | N/A | Combine **BB Android's `runtime_audio.c`** with **P5R Android's NDK AAudio** backend. | GPL-2.0 / GPL-3.0. Compatible. |
| **Input Subsystem** | DualShock 4 pad mapping + on-screen virtual pad (`TouchControllerOverlay.java`) | DirectInput / XInput / SDL2 gamepad mapping | Custom interactive touch layout editor (`ControlsEditor.java`) | SDL2 gamepad, keyboard, mouse mapping | N/A | Port **P5R Android's `ControlsEditor.java`** or **BB Android's `TouchControllerOverlay.java`**. | Fully compatible. |
| **Android Presentation Pipeline** | Zero-copy `AHardwareBuffer` + `ASurfaceControl` over UNIX socket (`bbpresent.c`) | Win32 Vulkan Swapchain (`VkSwapchainKHR`) | Standard `ANativeWindow` Vulkan Surface (`vkCreateAndroidSurfaceKHR`) | Desktop Vulkan Swapchain (`VkSwapchainKHR`) | N/A | **Bloodborne Android's `libbbpresent.so`** is 100% reusable and optimal. | GPL-2.0. Fully compatible. |
| **Game Preparation Pipeline** | Offline Bionic C++ tool (`tools/android/prepare/bb_prepare.cpp`) | Launcher automated directory verification (`sotc.py`) | On-device `.nsp`/`.xci` decryption + AOT shader compilation | Real-time loading from directory or `.pkg` | N/A | Use **Bloodborne Android's offline preparation pattern** for P3R's `eboot.bin` and PRX files. | GPL-2.0. Fully compatible. |

---

## 2. In-Depth Component Analysis

### 2.1. CPU Execution & Translation Engine
- **Bloodborne Android:** Implements an embedded FEXCore bridge in `cpu/guest_cpu_fex.cpp`. The game process runs as an ARM64 binary (`bb-probe`). Only x86-64 machine code passes through FEXCore. A 1 MB block of 16-byte stubs intercepts calls from x86-64 guest code into host runtime functions via `syscall`, which the `FEXCore::HLE::SyscallHandler` catches and routes to `bbcpu_host_call` (`host_call_arm64.S`).
- **Shadow of the Colossus PC:** Executes on x86-64 host CPU directly. Calls into the runtime are direct function calls. This architecture cannot run on ARM64 devices without complete emulation.
- **Persona 5 Royal Android:** Executes natively on ARM64 host CPU because the source game is compiled for Nintendo Switch (AArch64). Privileged instructions (`svc`) are patched with user-space stubs. This loader is completely incompatible with x86-64 PS4 games.
- **Verdict for P3R Android:** **Bloodborne Android's embedded FEXCore architecture is the only proven, functional design.**

### 2.2. PS4 Compatibility Runtime
- **Bloodborne Android:** Implements 750+ NIDs across `runtime_kernel.c`, `runtime_memory.c`, `runtime_mutex.c`, `runtime_sema.c`, `runtime_file.c`, `runtime_pad.c`, `runtime_audio.c`, `runtime_savedata.c`.
- **Shadow of the Colossus PC:** Expands upon Bloodborne PC with:
  - `runtime_fiber.c`: Complete implementation of `libSceFiber` (fibers / cooperative coroutines).
  - `runtime_sotc.c`: PS4 Pro (`sceKernelIsNeoMode`), heap trace information, direct memory expansion.
- **shadPS4:** Comprehensive C++23 reference implementation of the entire PS4 OS user-space library set.
- **Verdict for P3R Android:** **Combine Bloodborne Android's thin C runtime with SotC PC's `runtime_fiber.c` and missing NID handlers from shadPS4.**

### 2.3. Graphics & Shader Pipeline
- **Bloodborne Android & SotC PC:** Both vendor shadPS4's Liverpool GPU video core (`gpu/shadps4/`).
  - Emulates AMD GCN PM4 command processor.
  - Compiles GCN bytecode to SPIR-V.
  - Submits commands via Vulkan 1.3.
- **Differences for Unreal Engine 4 (P3R):**
  - *Bloodborne* uses a custom 2015 forward renderer with simple shader permutations.
  - *Persona 3 Reload* uses modern Unreal Engine 4.27 deferred rendering with heavy compute shader passes (Niagara particles, light culling, cel-shading post-processing).
  - shadPS4's shader recompiler has undergone extensive fixes since the commit vendored in Bloodborne Android (`b4e7ae7`, October 2026).
- **Verdict for P3R Android:** **The graphics core must be updated to modern shadPS4 main** to pull in critical compute shader control-flow fixes and vertex fetch enhancements.

### 2.4. Android Presentation & Display
- **Bloodborne Android (`libbbpresent.so`):**
  - Utilizes Android NDK `ASurfaceControl` and `ASurfaceTransaction` (API 29+).
  - Renders to `AHardwareBuffer` in the game process and passes buffer FDs over a local UNIX socket.
  - Bypasses standard Android window rendering overhead; latches directly into `SurfaceFlinger`.
  - Supports both **Newest-wins (low latency)** and **FIFO (smooth 30/60 FPS pacing)** modes.
- **Verdict for P3R Android:** **100% reusable without structural modification.**

