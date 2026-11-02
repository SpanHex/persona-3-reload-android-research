# Unreal Engine 4.27 PlayStation 4 Internals & RHI Mechanics

**Document:** `research/technical-findings/UNREAL_ENGINE_PS4_INTERNALS.md`  
**Investigation Date:** 2026-11-02  

---

## 1. Engine RHI Architecture on PlayStation 4

Unreal Engine 4 communicates with the PS4 GPU through a specialized Render Hardware Interface (RHI) implementation named `CPS4DynamicRHI`.

### 1.1. GNM Command Buffer Generation
- UE4 translates abstract render commands (`FRHICommandList`) directly into Sony **GNM** PM4 packets.
- The engine creates a dedicated **RHI Thread** that executes concurrently with the **Render Thread**.
- The RHI thread writes command packets into double-buffered ring buffers allocated from direct physical memory mapped with write-combined CPU caching (`WC`).
- When a pass finishes, the RHI thread calls `sceGnmSubmitDone` / `sceGnmSubmitCommandBuffers`.

### 1.2. Shader Packaging & Pipeline States
- Shaders in UE4 are authored in HLSL / USF (Unreal Shader Format).
- At package time, Sony's proprietary compiler (`orbis-psslc`) compiles them to AMD GCN 2.0 (Sea Islands) ISA machine code.
- GCN shaders are stored inside Unreal `.pak` / `.ucas` container streams as serialized `FShader` bytecode chunks.
- When a PSO (Pipeline State Object) is created at runtime, `CPS4DynamicRHI` passes the GCN bytecode pointers to `sceGnmSetShaders`.
- In our Android compatibility runtime, this pointer is intercepted by shadPS4's `shader_recompiler`, which translates the GCN bytecode to SPIR-V and compiles a Vulkan `VkPipeline`.

---

## 2. Unreal Engine IO Store (.utoc / .ucas)

In Unreal Engine 4.27, Epic introduced the **Zen / IO Store** filesystem:
- Replaces traditional monolithic `.pak` archives with:
  1. `.utoc` (Table of Contents): Binary metadata file describing package chunks, directory trees, and compression headers.
  2. `.ucas` (Container Archive Stream): Raw data chunks (textures, meshes, audio) compressed using Oodle (Kraken / Mermaid) or Zlib.
- **Asynchronous Loading:**
  - UE4 on PS4 loads these chunks via Sony's `libSceFios2` (Fast I/O System).
  - Bloodborne Android already bundles `sce_module/libSceFios2.prx`, which handles the internal caching and queueing of read requests.
  - As long as `runtime_file.c` provides unbuffered, non-blocking file access to the host Android filesystem, FIOS2 will operate cleanly in guest memory.

