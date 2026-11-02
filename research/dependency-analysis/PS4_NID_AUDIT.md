# PS4 NID Audit & Service Classification for Persona 3 Reload

**Document:** `research/dependency-analysis/PS4_NID_AUDIT.md`  
**Investigation Date:** 2026-11-02  

---

## 1. Primary Required PS4 Modules

Persona 3 Reload (PS4) dynamically links and interacts with the following major system modules:

```
eboot.bin (Target Binary)
  ├── sce_module/libc.prx (C Standard Library)
  ├── sce_module/libSceFios2.prx (Asynchronous File I/O System)
  ├── libkernel.sprx (Core Orbis OS Kernel Services)
  ├── libSceGnmDriver.sprx (Hardware Graphics Driver)
  ├── libSceVideoOut.sprx (Display & Buffer Presentation)
  ├── libScePad.sprx (DualShock 4 Gamepad Input)
  ├── libSceAudioOut.sprx (Multichannel PCM Sound Output)
  ├── libSceSaveData.sprx (Encrypted Savedata Management)
  ├── libSceUserService.sprx (User Account Profiles)
  ├── libSceSystemService.sprx (System Power & State Callbacks)
  ├── libSceRtc.sprx (Real-Time Clock)
  ├── libSceFiber.sprx (User-mode Fibers / Scheduling)
  ├── libSceSysmodule.sprx (Dynamic Module Loader)
  └── libSceNet.sprx / libSceNetCtl.sprx (Networking)
```

---

## 2. NID Status Classification

### Group A: Already Implemented in Bloodborne Android (Tested & Verified)
- `_init_env`, `atexit`, `exit`, `__stack_chk_fail`
- Pthread operations: `pthread_create`, `pthread_join`, `pthread_mutex_*`, `pthread_cond_*`, `pthread_rwlock_*`
- C Standard Library: `malloc`, `free`, `realloc`, `calloc`, `memcpy`, `memmove`, `memset`, math functions (`sin`, `cos`, `pow`, etc.)
- Kernel Direct Memory: `sceKernelAllocateDirectMemory`, `sceKernelMapDirectMemory`, `sceKernelReleaseDirectMemory`
- Process time & clocks: `sceKernelGetProcessTime`, `gettimeofday`, `clock_gettime`
- Gamepad: `scePadInit`, `scePadOpen`, `scePadReadState`, `scePadSetVibration`
- Display: `sceVideoOutOpen`, `sceVideoOutRegisterBuffers`, `sceVideoOutSubmitFlip`
- File System: `sceKernelOpen`, `sceKernelRead`, `sceKernelWrite`, `sceKernelClose`, `stat`
- Audio: `sceAudioOutOpen`, `sceAudioOutOutput`, `sceAudioOutClose`

### Group B: Implemented in Shadow of the Colossus PC (Requires Porting to FEXCore)
- `libSceFiber`:
  - `sceFiberInitialize`
  - `sceFiberSwitch`
  - `sceFiberGetSelf`
  - `sceFiberFinalize`
- System Service:
  - `sceKernelIsNeoMode` (PS4 Pro / Neo detection)
  - `uuid_create`
  - `heap_get_trace_info`

### Group C: Missing or Partially Stubbed in shadPS4 (Requires Implementation)
- `sceUserServiceGetInitialUser`: Returns default user ID `0x10000000`.
- `sceUserServiceGetUserName`: Returns default string `"Player"`.
- `sceSystemServiceReceiveEvent`: Stubs system sleep/wake/power notifications.
- `libSceNpWebApi2`: Stubs for network telemetry/PSN; returns offline error code.

### Group D: Game Middleware Internal Functions (Executes in Guest Code)
- `CriWareRuntime` (CriAtomEx, CriFs, CriSofdec2):
  - These libraries are compiled directly into P3R's `eboot.bin` or statically linked PRX modules.
  - They execute as guest x86-64 machine code and interact with the host solely through `libSceAudioOut` and `libSceFios2`.

