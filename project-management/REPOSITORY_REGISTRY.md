# Reference Repository Registry

**Project:** Persona 3 Reload — PS4 to Android Research (Phases 1 & 2)  
**Retrieval Date:** 2026-11-02 (Phase 1) / 2026-11-03 (Phase 2)  
**Status:** All repositories verified, original Git histories and licenses preserved without modification.

## Primary Investigated Repositories

| Repository | Directory | Remote URL | Branch | Commit Hash | Retrieval Date | License | Role in Research |
|---|---|---|---|---|---|---|---|
| **Bloodborne Android Rebuild Tool** | `references/bloodborne-android-rebuild-tool` | `https://github.com/ducvd89/Bloodborne-android-rebuild-tool` | `main` | `6ebb33b0c729a3942fddaa03965360c699d7d900` | 2026-11-03 | GPL-3.0-or-later | Primary reference for AOT lifting, LLVM lowering, and ARM64 code generation. |
| **Bloodborne Android (Official Upstream)** | `references/bloodborne-android-upstream` | `https://github.com/ducvd89/Bloodborne-Android` | `master` | `f241353e36f46bf183806acd7b79222afff2fd2f` | 2026-11-03 | GPL-2.0-or-later | Primary reference for native ARM64 Android runtime, AOT unit loading, and FEXCore removal. |
| **Bloodborne PC** | `references/bloodborne-pc` | `https://github.com/deadinside28/bloodborne_pc` | `master` | `0fc2921c45f8ff3900f6bfa43a299e9a4f532af4` | 2026-11-03 | GPL-3.0-or-later | Desktop x86-64 recompilation reference and variant patching. |
| **Bloodborne Android (StanTheMackiar)** | `references/bloodborne-android` | `https://github.com/StanTheMackiar/bloodborne-android-port` | `master` | `631b3f568bbf4d25abd5e05340c21becf2ca2a9b` | 2026-11-02 | GPL-2.0-or-later | Historical Phase 1 reference for earlier FEXCore embedded runtime. |
| **Shadow of the Colossus PC** | `references/shadow-of-the-colossus-pc` | `https://github.com/AjncSystem/ShadowOfTheColossus-PC` | `main` | `cfbbfab9c94cf18f6b1ee34d64f005a305282931` | 2026-11-02 | GPL-2.0 | Secondary reference for static PS4 ELF loading and rendering shims. |
| **Persona 5 Royal Android** | `references/p5r-android` | `https://github.com/Brandon04Gonzalez/p5r-android` | `main` | `5e05e70a3ff8b2638ebee9092511b676d1f22544` | 2026-11-02 | GPL-3.0 | Reference for Atlus game asset structures and Android packaging. |
| **shadPS4** | `references/shadps4` | `https://github.com/shadps4-emu/shadPS4` | `main` | `2183807e592b36d4440384878165b43d930c1dee` | 2026-11-02 | GPL-2.0-or-later | Reference for GNM/PM4 packet translation, Vulkan shader recompiler, and Orbis OS system libraries. |
| **FEX (FEXCore)** | `references/fexcore` | `https://github.com/FEX-Emu/FEX` | `main` | `02e24ca5c01ed0c864466ed573db347336f70170` | 2026-11-02 | MIT | Historical reference for Dynamic Binary Translation, CPU state layouts, and opcode dispatching. |
