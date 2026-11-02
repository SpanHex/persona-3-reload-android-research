# Legal, Licensing & Intellectual Property Redistribution Audit

**Document ID:** `P3R-DOC-P2-007`  
**Research Phase:** Phase 2: Advanced Recompilation, Compatibility & Feasibility  
**Subject:** Open-Source Software Licensing, Copyright Boundaries, and Redistribution Compliance  
**Audited Repositories & Toolchains:**
- `ducvd89/Bloodborne-android-rebuild-tool` (`GPL-3.0-or-later`)
- `ducvd89/Bloodborne-Android` (`GPL-2.0-or-later`)
- `shadps4-emu/shadPS4` (`GPL-2.0-or-later`)
- `FEX-Emu/FEX` (`MIT License`)
- `llvm/llvm-project` (`Apache-2.0 with LLVM Exception`)
- `AjncSystem/ShadowOfTheColossus-PC` (`GPL-3.0-or-later`)
- `Mesa3D/mesa` (Turnip Driver) (`MIT License`)

---

## 1. Executive Summary

Developing a native Android translation layer for a commercial PlayStation 4 title involves navigating complex legal frameworks spanning software copyright, open-source license compatibility, patent boundaries, and anti-circumvention statutes (e.g., DMCA 17 U.S.C. § 1201 / European Union Software Directive 2009/24/EC).

This audit establishes the legal boundaries for the proposed Persona 3 Reload Android research project, evaluates the compatibility of licenses across upstream projects, determines the legal classification of recompiled `.so` binary artifacts, and prescribes mandatory redistribution guidelines.

**Core Findings:**
1. **The Recompiled `.so` Binary is a Copyrighted Derivative Work:** Generating `libp3raot.so` from Persona 3 Reload's `eboot.bin` creates an unauthorized derivative work under copyright law. **Redistributing `libp3raot.so`, pre-compiled game units, or proprietary Atlus/SEGA game assets is strictly illegal and copyright infringement.**
2. **The Clean-Room Compiler Paradigm is Legally Sound:** Providing an open-source, user-facing recompilation tool (like `bb-recomp`) that allows end-users to compile their own legitimately purchased game files on their private hardware is completely legal under established reverse-engineering and interoperability precedents (*Sony Computer Entertainment, Inc. v. Connectix Corp.*, *Sega Enterprises Ltd. v. Accolade, Inc.*).
3. **Upstream License Compatibility:** Combining code from `shadPS4` (GPL-2.0-or-later) and `Bloodborne-android-rebuild-tool` (GPL-3.0-or-later) is fully permissible under the "or later" clause, with the combined derivative work legally governed by **GPL-3.0-or-later**.

---

## 2. Comprehensive Upstream License Inventory

The following table catalogs the verified software licenses governing every upstream dependency investigated in Phase 2:

| Component / Repository | Exact Source License | Permitted Uses | Redistribution Requirements & Constraints | Compatibility with Combined Project |
|---|---|---|---|---|
| **`Bloodborne-android-rebuild-tool`** | **GPL-3.0-or-later** | Modification, private compilation, redistribution. | Source code of any derived or combined work must be provided under GPL-3.0. | **Compatible** (Sets baseline project license to GPL-3.0). |
| **`Bloodborne-Android` (Runtime)** | **GPL-2.0-or-later** | Modification, private compilation, redistribution. | Allows upgrading to GPL-3.0 under the "or later" provision. Source must accompany binary. | **Compatible** (Upgraded to GPL-3.0 when merged). |
| **`shadps4-emu/shadPS4`** | **GPL-2.0-or-later** | Code reuse, modification, porting. | Allows upgrading to GPL-3.0 under the "or later" provision. Full source must be released. | **Compatible** (Ported graphics modules become GPL-3.0). |
| **`FEX-Emu/FEX`** | **MIT License** | Full commercial and non-commercial reuse. | Retain copyright notice and disclaimer in source headers. | **Fully Compatible** (Permissive; embeds cleanly into GPL-3.0). |
| **`LLVM Project`** | **Apache-2.0 with LLVM Exception** | Linking, embedding, compiler backend use. | LLVM exception permits linking output binaries without viral license contamination. | **Fully Compatible** (Standard compiler dependency). |
| **`Mesa Turnip` (Vulkan Driver)** | **MIT License** | Dynamic loading, runtime bundling. | Include Mesa MIT license notice in application about page. | **Fully Compatible** (Permissive dynamic library). |
| **Persona 3 Reload (`eboot.bin`)** | **Proprietary Copyright (Atlus / SEGA)** | Private personal use on licensed console. | **STRICTLY PROHIBITED FROM REDISTRIBUTION.** Zero game code may be committed to repositories. | **NON-REDISTRIBUTABLE** (End-user supplied only). |

---

## 3. Analysis of GPL-2.0 vs. GPL-3.0 Incompatibility & Resolution

A common trap in open-source emulation development is the inherent conflict between **GPL-2.0-only** and **GPL-3.0**:
- Under open-source licensing principles, pure GPL-2.0-only code cannot be linked with GPL-3.0 code because GPL-3.0 imposes terms (such as patent clauses and anti-tivoization restrictions) that GPL-2.0-only forbids.
- **The Resolution in Our Ecosystem:**
  Both `shadPS4` and `Bloodborne-Android` explicitly utilize the **"GPL-2.0-or-later"** license header:
  ```cpp
  // SPDX-License-Identifier: GPL-2.0-or-later
  ```
  The "or later" clause grants downstream developers the explicit legal right to license derivative and combined works under any subsequent version of the General Public License published by the Free Software Foundation.
- Therefore, when porting modules from `shadPS4` into the rebuild tool or the native runtime, the combined repository is legally and cleanly licensed under **GNU General Public License version 3.0 or later (GPL-3.0-or-later)**.

---

## 4. Legal Status of the Recompiled ARM64 Binary (`libp3raot.so`)

A critical distinction must be maintained between the **compiler software** and the **compiled game output**:

```
[Open-Source Compiler (GPL-3.0)]  ──────> Compiles ──────> [Output Binary (libp3raot.so)]
       (Free to distribute)                                       (PROPRIETARY DERIVATIVE WORK)
                                                                 ❌ ILLEGAL TO DISTRIBUTE
```

### Why `libp3raot.so` is Legally Equivalent to the Commercial Game
1. **Direct Binary Transformation:** Ahead-of-time binary translation is a deterministic, functional transformation of original compiled machine instructions into another instruction set architecture.
2. **Preservation of Expressive Logic:** The resulting `libp3raot.so` contains the proprietary game scripts, damage formulas, AI decision trees, physics algorithms, and character behaviors authored by Atlus programmers.
3. **Copyright Law Precedents:** Under U.S. Copyright Act Title 17 and international copyright conventions (Berne Convention), a translation of a copyrighted work into another language (including translating x86 machine language into ARM64 machine language) constitutes a **Derivative Work** (§ 101).
4. **Distribution Prohibition:** Only the copyright holder (SEGA / Atlus) possesses the exclusive right to distribute or authorize the distribution of derivative works. Uploading `libp3raot.so` to GitHub, Discord, Telegram, or any public server is an act of **commercial software piracy**.

---

## 5. Clean-Room Interoperability & Anti-Circumvention Compliance

To ensure that the research and any resulting software remain 100% compliant with intellectual property law, the project must adhere to strict clean-room engineering guidelines:

### 5.1 DMCA Anti-Circumvention (17 U.S.C. § 1201(f)) Exemption
Section 1201(f) of the Digital Millennium Copyright Act explicitly provides a statutory exemption for reverse engineering:
> *"A person who has lawfully obtained the right to use a copy of a computer program may circumvent a technological measure... for the sole purpose of identifying and analyzing those elements of the program that are necessary to achieve interoperability of an independently created computer program with other programs..."*

To qualify for this interoperability exemption:
- **No Console Firmware or Keys in Repository:** The repository must *never* contain PlayStation 4 encryption keys (e.g., SAMU keys, pup keys, package keys).
- **No Decryption Tools in Repository:** The toolchain must *not* attempt to decrypt encrypted Sony `.pkg` files or encrypted SELF containers directly.
- **Requirement for Decrypted Input:** The user must independently decrypt and extract their legitimately purchased game files on their own jailbroken console or through established third-party homebrew dumpers before feeding the resulting `eboot.bin` to the offline recompiler.

### 5.2 Clean-Room Source Architecture
The repository must consist strictly of:
1. Open-source compiler source code (`.cpp`, `.h`, CMake scripts).
2. Clean-room platform implementations of standard Orbis OS and POSIX APIs.
3. Open-source Vulkan translation layers mapping GCN commands to standard Vulkan.
4. Documentation, technical research reports, and architectural specifications.

---

## 6. Redistribution Protocol & Repository Guardrails

To permanently protect the repository and maintain rigorous compliance, the following operational guardrails are established:

### Mandatory Repository Exclusions (`.gitignore`)
The following file types are strictly banned from Git commits and tracked via `.gitignore`:
```gitignore
# Commercial Game & Binary Data (Strictly Prohibited)
*.pkg
*.elf
*.bin
*.prx
*.sprx
*.pak
*.ucas
*.utoc
*.usm
*.acb
*.awb
*.keys
*.sfo
*.iso

# Compiled Recompilation Outputs
*.so
*.a
libbbaot.so
libp3raot.so
game.*.o
aot/
```

### The "Bring-Your-Own-Game" (BYOG) Execution Model
The user-facing application must operate exclusively on the Bring-Your-Own-Game model established by Bloodborne Android 2.0.0:
1. The user downloads the open-source Android APK from the release page.
2. The APK contains zero game code, zero game assets, and zero copyrighted materials.
3. On first launch, the app displays a file picker prompting the user to select their local game directory containing their self-dumped game data and their self-compiled `libp3raot.so`.
4. The runtime verifies the integrity of the user's `libp3raot.so` via `bbr_image_hash` and begins native execution locally.

---

## 7. Conclusion

By maintaining a strict structural separation between the **open-source translation runtime** (GPL-3.0) and the **user's proprietary game data**, the project operates on solid legal and ethical footing. The research and software can be published, distributed, and improved openly without infringing upon Atlus, SEGA, or Sony Interactive Entertainment intellectual property.
