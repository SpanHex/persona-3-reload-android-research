# Persona 3 Reload — PS4 to Android Technical Research & Architecture

[![Status](https://img.shields.io/badge/Phase_1-Research_Complete-success?style=for-the-badge)](#)
[![Target](https://img.shields.io/badge/Target-Android_ARM64-3DDC84?style=for-the-badge&logo=android&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-GPL--2.0-blue?style=for-the-badge)](#licensing--legal-compliance)
[![Engine](https://img.shields.io/badge/Engine-Unreal_Engine_4.27-0E1128?style=for-the-badge&logo=unrealengine&logoColor=white)](#)

> **PHASE 1 RESEARCH DELIVERABLE:** Complete reverse-engineering investigation, native systems architecture analysis, and feasibility evaluation for adapting the PlayStation 4 release of **Persona 3 Reload** into a dedicated native Android ARM64 application.
> 
> *Notice: This repository contains research documents, architecture maps, dependency matrices, and system diagrams only. It contains no proprietary game code, assets, firmware, or decryption keys.*

---

## 1. Executive Summary

This research investigates the technical requirements for hosting the PlayStation 4 release of *Persona 3 Reload* (CUSA43889 / CUSA43890 / CUSA37522) on modern 64-bit ARM Android devices.

Rather than emulating a full PlayStation 4 console and operating system, this project evaluates a **hybrid native compatibility runtime**:
1. **Dynamic Binary Translation (DBT):** Only the game's actual x86-64 machine code (`eboot.bin`, `libc.prx`, `libSceFios2.prx`) is translated at runtime into native ARM64 instructions using an embedded build of **FEXCore**.
2. **Native Platform Replacement (HLE):** 85%+ of PlayStation 4 OS services (`libkernel`, pthreads, direct memory management, `libScePad`, `libSceAudioOut`, `libSceSaveData`) execute natively as ARM64 Bionic code.
3. **Graphics Translation:** The game links Sony's low-level graphics library (`libGnm`), emitting AMD GCN PM4 command packets. These packets are intercepted by an adapted build of **shadPS4's Liverpool Vulkan video core**, which compiles GCN shaders into SPIR-V and executes them via Vulkan 1.3.
4. **Direct GPU Driver Access:** The runtime bypasses Android's system Vulkan loader and directly loads custom-tuned **Mesa Turnip** drivers for Qualcomm Adreno GPUs.
5. **Zero-Copy Display Presentation:** Frames are rendered into `AHardwareBuffer` surfaces and presented directly to `SurfaceFlinger` via Android `ASurfaceControl` transactions.

---

## 2. System Architecture

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

## 3. Execution Flow

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

## 4. Documentation Directory & Research Index

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
| [FINAL_FEASIBILITY_REPORT.md](documentation/FINAL_FEASIBILITY_REPORT.md) | Concluding feasibility report answering the 12 core engineering questions with empirical evidence and risk rankings. |
| [IMPLEMENTATION_ROADMAP.md](documentation/IMPLEMENTATION_ROADMAP.md) | Phased engineering roadmap detailing Milestones 1 through 6, prerequisites, deliverables, technical blockers, and definitions of completion. |
| [REPOSITORY_REGISTRY.md](project-management/REPOSITORY_REGISTRY.md) | Provenance log of all reference repositories, recording commit SHAs, branches, licenses, and retrieval dates. |

---

## 5. Summary of Key Findings

1. **CPU Execution:** **Technically Plausible**. FEXCore supports all instruction sets emitted by the PS4 Clang compiler for AMD Jaguar (x86-64, AVX, BMI1, SSE4.2). Bloodborne Android's embedded stub bridge demonstrates translation overhead under ~20%.
2. **Platform Services:** **85%+ Reusable**. Bloodborne Android's native C runtime provides complete replacements for pthreads, mutexes, semaphores, file routing, and controller input. The primary missing dependency is **`libSceFiber`**, which can be ported from Shadow of the Colossus PC.
3. **Graphics Subsystem:** **Highest Engineering Complexity**. While Bloodborne uses an older forward renderer, Persona 3 Reload utilizes modern Unreal Engine 4.27 deferred rendering with heavy compute shader passes (Niagara particles, light culling, outlines). shadPS4's Liverpool Vulkan core successfully boots P3R to `status-ingame`, but requires upstream recompiler updates to resolve structured control-flow assertions (`AF:structured_control_flow`).
4. **Target Device (realme 12 Pro+ / Adreno 710):**
   - **Viable as a research testbench:** Can execute the CPU translation layer and run community-patched Turnip drivers (`vauzi-17` with `TU_DEBUG=sysmem`).
   - **Performance expectation:** The Adreno 710 has ~1/3 the compute throughput of a flagship Snapdragon 8 Gen 2 (Adreno 740). Playable target is **540p or 720p at 30 FPS with FSR 1.0 upscaling**.
   - **RAM Warning:** If the user device is the **8 GB RAM variant**, aggressive texture memory clamping is required to prevent Android Low Memory Killer (`SIGKILL`) eviction. The **12 GB RAM variant** has comfortable headroom.

---

## 6. Implementation Roadmap Overview

- **MILESTONE 1 (Complete):** Technical Research & Reverse Engineering.
- **MILESTONE 2 (Prospective):** Independent ARM64/FEXCore Proof of Concept (verify FEXCore JIT on Android Bionic with synthetic math/memory payloads).
- **MILESTONE 3 (Prospective):** Android PS4 Compatibility Runtime Architecture (Bionic pthreads, 6–8 GiB direct memory pool below 1 TiB, `libSceFiber` context switching).
- **MILESTONE 4 (Prospective):** Vulkan Graphics Compatibility (integrate updated shadPS4 Liverpool core, test compute passes and `ASurfaceControl` presentation).
- **MILESTONE 5 (Prospective):** P3R-Specific Compatibility & Ingestion (`p3r-prepare` offline linker, IO Store `.utoc`/`.ucas` verification, CriWare audio routing).
- **MILESTONE 6 (Prospective):** Device Testing & Adreno 710 Optimization (Turnip `sysmem` profile, 540p/720p FSR scaling, thermal tuning).

---

## 7. Licensing & Legal Compliance

- **GPL-2.0 Compliance:** The native runtime is derived from GPL-2.0 code (Bloodborne Android, shadPS4) and will be licensed under GPL-2.0 upon binary distribution.
- **No Proprietary Assets:** This repository does **not** host, distribute, or link to copyrighted game files, executables, textures, audio, video, firmware, or cryptographic keys.
- **BYOG (Bring Your Own Game):** The proposed runtime functions solely by ingesting a user's legitimately obtained and dumped PlayStation 4 game files.
