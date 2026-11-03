# Phase 3.1: Technical, Performance & Architectural Risk Register

## Executive Summary

Translating a commercial PlayStation 4 title into a native Android ARM64 application involves multi-layered risks across instruction translation, operating system compatibility, thermal management, GPU shader reproduction, and legal boundaries.

This Risk Register identifies the critical technical risks, scores their probability and impact, and defines actionable mitigation strategies.

---

## Risk Scoring Matrix

| Risk ID | Category | Description | Severity | Likelihood | Risk Level | Mitigation Strategy |
|---|---|---|:---:|:---:|:---:|---|
| **RSK-01** | Compiler | Incomplete x86-64 ISA coverage in custom lifter | High | High | **CRITICAL** | Adopt Option B (FEXCore production IR lifter) |
| **RSK-02** | Graphics | GNM / GCN shader translation overhead & Vulkan bugs | High | High | **CRITICAL** | Leverage shadPS4's SPIR-V translator; precompile PSOs |
| **RSK-03** | System | Android Low Memory Killer (LMK) terminating game | High | Medium | **HIGH** | Texture compression (ASTC) & asset streaming clamp |
| **RSK-04** | Hardware | Thermal throttling on Snapdragon 7s Gen 2 | Medium | High | **HIGH** | Target 720p 30fps baseline; dynamic resolution scaling |
| **RSK-05** | Runtime | Unreal Engine 4 TaskGraph & thread fiber crashes | High | Medium | **HIGH** | Clean `GuestState` context swapping; fiber emulation |
| **RSK-06** | OS | Memory page alignment violations (4KB vs 16KB) | Medium | Low | **MEDIUM** | Link with `-Wl,-z,max-page-size=16384` |
| **RSK-07** | Audio | Proprietary ATRAC9 audio decoding | Low | High | **MEDIUM** | Offline transcoding to Opus/Vorbis or FFmpeg decoder |
| **RSK-08** | Security | Circumvention of console DRM / copyright claims | Critical | Low | **HIGH** | Clean-room design; zero proprietary assets bundled |

---

## In-Depth Risk Analysis & Mitigation Plans

### RSK-01: Incomplete x86-64 ISA Coverage
- **Description:** A commercial UE4 game binary utilizes complex vector extensions (SSE4.2, AVX, BMI1/2) and obscure x86 instructions. A custom Python/llvmlite compiler risks tripping unliftable traps (`BBR_TRAP_UNLIFTABLE`) during gameplay.
- **Impact:** Game crash, soft-lock, or visual glitches.
- **Mitigation:** Transition compiler frontend to FEXCore (Option B), which has 99%+ x86-64 ISA coverage and years of battle-testing across Linux and Android.

---

### RSK-02: GNM to Vulkan Shader Translation
- **Description:** The PS4 uses AMD GCN bytecode for compute and pixel shaders. Translating GCN shaders to Vulkan SPIR-V at runtime introduces shader compilation stutter.
- **Impact:** Heavy frame drops, visual artifacts, or missing rendering passes.
- **Mitigation:**
  1. Leverage the shader translation pipeline from shadPS4.
  2. Implement an Ahead-of-Time (AOT) shader pre-compilation step that translates all game shaders into Vulkan Pipeline State Objects (PSOs) during initial game installation on the device.

---

### RSK-03: System Memory Footprint & Android LMK
- **Description:** Persona 3 Reload on PS4 consumes approximately $4.5\text{ GB}$ to $5.5\text{ GB}$ of unified RAM. While the realme 12 Pro+ has 8 GB or 12 GB of physical RAM, the Android operating system and background applications typically consume 3–4 GB. If the game exceeds available RAM, Android's Low Memory Killer (LMK) will abruptly terminate the process.
- **Impact:** Sudden, ungraceful crash to Android launcher.
- **Mitigation:**
  1. Transcode uncompressed RGBA textures to native mobile ASTC (Adaptive Scalable Texture Compression) formats, reducing texture memory bandwidth and VRAM by up to $60\%$.
  2. Implement aggressive Unreal Engine asset garbage collection during scene transitions.

---

### RSK-04: Sustained Thermal Performance on Snapdragon 7s Gen 2
- **Description:** The Snapdragon 7s Gen 2 features 4x Cortex-A78 cores and an Adreno 710 GPU manufactured on a 4nm process. Under sustained heavy loads, passive smartphone cooling leads to thermal throttling, dropping CPU clocks from $2.40\text{ GHz}$ to $\approx 1.6\text{ GHz}$.
- **Impact:** Frame rates dropping from 60 fps to sub-20 fps after 15 minutes of continuous play.
- **Mitigation:**
  1. Default target: **720p @ 30 fps** (or dynamic resolution scaling between 540p and 720p).
  2. Offload non-critical worker threads (audio decompression, background asset parsing) to the 4x Cortex-A55 efficiency cores, leaving the Cortex-A78 cores dedicated to rendering and game logic.

---

### RSK-05: Unreal Engine 4 TaskGraph & Fiber Context Switching
- **Description:** UE4's job system relies on fine-grained task switching. If guest registers and stack pointers are corrupted during thread yielding, the engine state becomes indeterminate.
- **Impact:** Hard fatal crashes inside engine task workers.
- **Mitigation:** Ensure the `GuestState` structure accurately maintains stack boundaries (`RSP`/`RBP`), condition flags, and callee-saved registers. Provide POSIX-compatible thread-local storage (`pthread_key_create`) for all guest worker threads.

---

### RSK-06: Legal & Intellectual Property Boundaries
- **Description:** Commercial PlayStation 4 binaries, game scripts, textures, and models are copyrighted intellectual property of Atlus / SEGA.
- **Impact:** Copyright infringement or DMCA takedown actions.
- **Mitigation:**
  1. The project distributes **only open-source compiler tooling and compatibility runtime code**.
  2. All commercial game data, executables (`eboot.bin`), and asset archives (`*.cpk`, `*.pak`) must be legitimately obtained and decrypted by the end user from their own legally purchased PS4 retail copy.
  3. No proprietary console firmware keys, certificates, or assets shall ever be hosted in the repository.
