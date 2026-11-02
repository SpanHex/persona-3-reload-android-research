# Licensing & Technical Dependency Compliance Audit

**Document:** `documentation/LICENSE_AND_DEPENDENCY_AUDIT.md`  
**Investigation Date:** 2026-11-02  
**Scope:** Technical compliance evaluation of third-party open-source components, proprietary boundaries, and distribution requirements for a Persona 3 Reload Android compatibility runtime.  
*Disclaimer: This document is a technical compliance assessment, not formal legal advice.*

---

## 1. Upstream Dependency License Inventory

| Component / Project | Repository / Origin | Declared License | SPXD Identifier | Modification / Distribution Obligation |
|---|---|---|---|---|
| **Bloodborne Android** | `StanTheMackiar/bloodborne-android-port` | GNU General Public License v2.0 | `GPL-2.0` | Copyleft: Derivative works must be licensed under GPL-2.0 and provide source code upon binary distribution. |
| **Shadow of the Colossus PC** | `AjncSystem/ShadowOfTheColossus-PC` | GNU General Public License v2.0 | `GPL-2.0` | Copyleft: Reused components (`runtime_fiber.c`) require GPL-2.0 compatibility. |
| **Persona 5 Royal Android** | `Brandon04Gonzalez/p5r-android` | GNU General Public License v3.0 | `GPL-3.0` | Strong Copyleft: Code licensed strictly under GPL-3.0 cannot be linked into a GPL-2.0-only binary without relicensing. UI/Java code can be studied or adapted under cleanroom principles. |
| **shadPS4** | `shadps4-emu/shadPS4` | GNU General Public License v2.0 or later | `GPL-2.0-or-later` | Copyleft: Fully compatible with GPL-2.0 and GPL-3.0. |
| **FEXCore** | `FEX-Emu/FEX` | MIT License | `MIT` | Permissive: Can be linked with GPL-2.0 or GPL-3.0 software provided the MIT copyright notice is preserved. |
| **Mesa Turnip** | `mesa/mesa` (Mesa 3D Project) | MIT / Khronos | `MIT` | Permissive: Pre-compiled driver `.so` files can be bundled with appropriate attribution. |
| **Android NDK / Bionic** | Google Android Open Source Project | Apache 2.0 / BSD 2-Clause | `Apache-2.0` | Permissive: Standard runtime system headers and libraries. |
| **Sirit** | `shadps4-emu/sirit` | MIT License | `MIT` | Permissive SPIR-V assembler. |
| **Zydis** | `zyantific/zydis` | MIT License | `MIT` | Fast x86/x86-64 disassembler. |

---

## 2. Copyleft Compatibility & License Harmonization

### 2.1. The GPL-2.0 vs. GPL-3.0 Boundary
- **Bloodborne Android** and **Shadow of the Colossus PC** are licensed strictly under **`GPL-2.0`** (or `GPL-2.0-or-later` in the case of shadPS4 components).
- **Persona 5 Royal Android** is licensed under **`GPL-3.0`**.
- **Crucial Licensing Rule:** Strict GPL-2.0 code cannot be combined in the same linked binary with strict GPL-3.0 code unless an explicit dual-licensing grant exists.
- **Project Architectural Solution:**
  1. **Core Native Runtime (`p3r-runtime` / `p3r-probe`):** Based on Bloodborne Android, shadPS4, and FEXCore. This entire native binary is licensed under **`GPL-2.0`**.
  2. **Android Frontend Application:** The Java/Kotlin launcher can be written as a standalone Android frontend communicating with the native process strictly over standard IPC (UNIX domain sockets and process pipes). Alternatively, UI layouts can be implemented independently to maintain clean licensing.

### 2.2. Source Distribution Requirements
Under GPL-2.0:
- If a pre-compiled Android APK containing the native runtime binaries is distributed, the distributor **MUST** provide access to the exact corresponding source code (including build scripts, patches, and submodules) under the GPL-2.0 license.
- The software must include prominent copyright notices and third-party license texts in a dedicated `THIRD_PARTY_NOTICES` screen within the app.

---

## 3. Proprietary Game Code & Asset Boundaries

### 3.1. Clean-Room & "Bring Your Own Game" (BYOG) Model
To comply with copyright laws and platform terms:
1. **Zero Proprietary Assets in the Repository or APK:**
   - The repository and compiled APK must contain **NO copyrighted assets**:
     - No textures, models, UI sprites, or fonts.
     - No cutscenes (`.usm`), audio cues (`.acb`/`.awb`), or music.
     - No PlayStation console firmware files, cryptographic keys (`keys.bin`), or secure bootroms.
     - No game executables (`eboot.bin`, `libc.prx`, `libSceFios2.prx`).
2. **User-Supplied Decrypted Game Data:**
   - The user must provide their own legitimately obtained dump of *Persona 3 Reload* (PS4 version) extracted from their own console.
   - The application's preparation tool (`p3r-prepare`) reads the user's files from phone storage, prepares the relocatable image on-device, and stores the runtime state in private application storage.
3. **No Circumvention of DRM:**
   - The runtime contains no cryptographic key extraction routines and does not bypass console digital rights management. It operates exclusively on already-decrypted ELF/PRX modules and standard archive containers.

---

## 4. Compliance Checklist for Project Artifacts

- [x] All reference repositories cloned preserving full git history and unmodified original licenses.
- [x] All upstream source attributions recorded with commit hashes and retrieval timestamps.
- [x] License boundaries verified: FEXCore (MIT), shadPS4 (GPL-2.0-or-later), Bloodborne Android (GPL-2.0).
- [x] GPL-2.0 copyleft obligations defined for prospective runtime binaries.
- [x] Strict prohibition against committing commercial game binaries, encryption keys, or proprietary audio/video assets into the research workspace.

