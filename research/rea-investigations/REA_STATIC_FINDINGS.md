# REA Static Analysis & Investigation Ledger

**Document:** `research/rea-investigations/REA_STATIC_FINDINGS.md`  
**Tool:** REA (Reverse Engineering for Coding Agents) v6.4.0 / v6.8.0  
**Investigation Date:** 2026-11-02  

---

## 1. REA Environment & Provider Verification

1. **Host Environment:**
   - Platform: `win32 x64`
   - Node.js: `v24.19.0`
   - REA CLI: `rea@6.4.0` (installed globally at `C:\Users\SPANDAN UPAMANYU\AppData\Roaming\npm\rea.cmd`)
   - Skill Version: v37 (170 tools) at `C:\Users\SPANDAN UPAMANYU\.gemini\config\skills\reverse-engineer-anything`
2. **MCP Live Server Status:**
   - Client: Google Antigravity
   - Config Path: `C:\Users\SPANDAN UPAMANYU\.gemini\config\mcp_config.json`
   - Script Path: `C:\Users\SPANDAN UPAMANYU\Downloads\rea-rea-agents-6.4.0\rea-rea-agents-6.4.0\scripts\rea.mjs, mcp`
   - Verified active and responding via `call_mcp_tool` (`binary_session`).
3. **Provider Diagnostics:**
   - Non-native providers: Fully active (artifact extraction, PE/CLI inspection, JavaScript/Web analysis, package inspection).
   - Headless Disassembler (Ghidra): Not configured (`GHIDRA_INSTALL_DIR` not set). In accordance with the prompt guidelines ("Install Ghidra only if needed for native binary analysis. For this phase, prioritize source-code investigation rather than commercial game binary analysis"), static source code investigation was prioritized across all five reference repositories.

---

## 2. Source-Level Code Investigation Findings

### Evidence Record 1: FEXCore Guest-to-Host ABI Bridge
- **Location:** `references/bloodborne-android/cpu/guest_cpu_fex.cpp#L77-L206`
- **Finding:** A 16-byte stub table (`StubBytes = 1 << 20`) containing `mov r10, rcx; syscall; ret` intercepts guest calls. The FEXCore `SyscallHandler` intercepts the syscall instruction, resolves the stub to a host function pointer, and calls `bbcpu_host_call` (`cpu/host_call_arm64.S`) to transition from SysV x86-64 calling convention to AAPCS64 ARM64.
- **Significance for P3R:** Eliminates the need for Wine or Linux system emulation. Translates only the game's actual machine code.

### Evidence Record 2: Pre-Linked Boot Blob Generation
- **Location:** `references/bloodborne-android/tools/android/prepare/bb_prepare.cpp#L29-L100`
- **Finding:** An offline pre-linker parses PS4 ELF/SELF binaries, resolves internal dynamic relocations (`R_X86_64_RELATIVE`, `R_X86_64_GLOB_DAT`, `R_X86_64_JUMP_SLOT`), links PRX modules (`libc.prx`, `libSceFios2.prx`) directly into the image, and outputs a single contiguous memory blob (`BBPROBE5`).
- **Significance for P3R:** Can be directly adapted (`p3r-prepare`) to link P3R's UE4 executable.

### Evidence Record 3: PS4 Fiber Emulation
- **Location:** `references/shadow-of-the-colossus-pc/src/runtime_fiber.c#L87-L150`
- **Finding:** `sotc_fiber_setjmp` and `sotc_fiber_longjmp` save and restore callee-saved registers (`RBX`, `RBP`, `RSP`, `R12-R15`, `FPU CW`, `MXCSR`).
- **Significance for P3R:** Required for Unreal Engine 4's task scheduling, but must be adapted to swap FEXCore's simulated `CPUStateFrame` rather than native host registers.

### Evidence Record 4: Native ARM64 Code Execution Contrast
- **Location:** `references/p5r-android/runtime/src/nce/nce.cpp#L21-L80`
- **Finding:** P5R Android executes Switch ARM64 machine code directly by patching `svc` and `TPIDR_EL0`. It contains no x86-64 binary translation engine.
- **Significance for P3R:** Proves conclusively that P5R's NCE loader cannot run PS4 x86-64 games, but its UI, AAudio, and touch input systems are prime candidates for reuse.

