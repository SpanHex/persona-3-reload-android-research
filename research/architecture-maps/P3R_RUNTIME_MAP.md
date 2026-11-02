# P3R Android Runtime Architecture & Call Mapping

**Document:** `research/architecture-maps/P3R_RUNTIME_MAP.md`  
**Investigation Date:** 2026-11-02  

---

## 1. Process Memory Layout (ARM64 Android Process Space)

```
0x0000_0000_0000 - 0x0000_0001_0000: Unmapped (Guard Page)
0x0000_0001_0000 - 0x0000_2000_0000: PS4 Direct Physical Memory Pool (Direct Memory, Flexible Memory)
0x0000_2000_0000 - 0x0000_4000_0000: Pre-linked Game Image (eboot.bin, libc.prx, libSceFios2.prx)
0x0000_4000_0000 - 0x0000_4010_0000: 16-Byte Host Stub Table (StubBytes = 1 MB)
0x0000_4010_0000 - 0x0000_5000_0000: Unmapped Traps & Diagnostic Return Guards
0x0000_5000_0000 - 0x0000_8000_0000: FEXCore Guest Stacks & Thread Local Storage (< 1 TiB)
-------------------------------------------------------------------------------------------------- [1 TiB Boundary]
0x0010_0000_0000 - 0x007F_FFFF_FFFF: Native Android Process Heap, FEXCore JIT Code Cache, Vulkan Driver
```

---

## 2. Key Interface Mappings

### 2.1. Kernel & Threading Mappings
| PS4 Orbis Function | Native Bionic / Linux Target | Module / File |
|---|---|---|
| `scePthreadCreate` | `pthread_create` + low-memory stack allocation | `runtime_kernel.c` |
| `scePthreadMutexLock` | `pthread_mutex_lock` | `runtime_mutex.c` |
| `scePthreadCondWait` | `pthread_cond_wait` | `runtime_kernel.c` |
| `sceKernelCreateEqueue` | `epoll_create1(EPOLL_CLOEXEC)` | `equeue.cpp` |
| `sceKernelAddUserEventToEqueue` | `eventfd(0, EFD_NONBLOCK | EFD_CLOEXEC)` | `equeue.cpp` |
| `sceKernelWaitEqueue` | `epoll_wait` | `equeue.cpp` |
| `sceFiberInitialize` | `runtime_fiber_initialize` | `runtime_fiber.c` |
| `sceFiberSwitch` | `fex_fiber_switch` (Guest CPU state swap) | `runtime_fiber.c` / `guest_cpu_fex.cpp` |

### 2.2. Memory Mappings
| PS4 Orbis Function | Native Bionic / Linux Target | Module / File |
|---|---|---|
| `sceKernelAllocateDirectMemory` | Anonymous `memfd_create` or `ashmem` | `runtime_memory.c` |
| `sceKernelMapDirectMemory` | `mmap` into guest address space (< 1 TiB) | `runtime_memory.c` |
| `sceKernelGetDirectMemorySize` | Returns configured ceiling (e.g. 6144 MiB) | `runtime_memory.c` |
| `sceKernelMprotect` | `mprotect` with GPU page-tracking interceptor | `runtime_memory.c` |

### 2.3. Graphics & Presentation Mappings
| PS4 GNM Function | Vulkan 1.3 / Android Native Target | Module / File |
|---|---|---|
| `sceGnmSubmitCommandBuffers` | PM4 Packet Iterator -> `vkCmdDrawIndexed` | `liverpool.cpp` / `vk_rasterizer.cpp` |
| `sceGnmDispatchDirect` | `vkCmdDispatch` (Compute pipeline) | `vk_compute_pipeline.cpp` |
| `sceVideoOutRegisterBuffers` | Allocate `AHardwareBuffer` pool | `bbpresent.c` / `vk_swapchain.cpp` |
| `sceVideoOutSubmitFlip` | Pass buffer FD over UNIX domain socket to `ASurfaceTransaction` | `bbpresent.c` |

