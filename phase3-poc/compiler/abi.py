# SPDX-License-Identifier: MIT
"""
GuestState & Recomp ABI v2 Specification
Matches references/bloodborne-android-upstream/cpu/guest_state.h
and docs/RECOMP_ABI.md
"""

import ctypes

# Register Enums matching System V AMD64 order
RAX = 0
RCX = 1
RDX = 2
RBX = 3
RSP = 4
RBP = 5
RSI = 6
RDI = 7
R8  = 8
R9  = 9
R10 = 10
R11 = 11
R12 = 12
R13 = 13
R14 = 14
R15 = 15

GPR_NAMES = [
    "rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi",
    "r8",  "r9",  "r10", "r11", "r12", "r13", "r14", "r15"
]

class XMMReg(ctypes.Structure):
    _fields_ = [("data", ctypes.c_uint8 * 16)]

class GuestState(ctypes.Structure):
    """
    Exact in-memory replica of FEXCore CPUState / GuestState (docs/RECOMP_ABI.md).
    Aligned to 64 bytes.
    """
    _fields_ = [
        ("gregs", ctypes.c_uint64 * 16),      # GPRs: RAX..R15 (0x000)
        ("rip", ctypes.c_uint64),             # Guest instruction pointer (0x080)
        ("flags", ctypes.c_uint64),           # NZCV / RFLAGS condition flags (0x088)
        ("pf_raw", ctypes.c_uint32),          # Parity flag raw (0x090)
        ("af_raw", ctypes.c_uint32),          # Aux carry flag raw (0x094)
        ("df_raw", ctypes.c_uint32),          # Direction flag raw (0x098)
        ("_pad0", ctypes.c_uint32),           # Alignment pad (0x09C)
        ("resume_flag", ctypes.c_uint64),     # Resume entry flag (GranularEntry) (0x0A0)
        ("xmm", XMMReg * 16),                 # 16 x 128-bit vector registers (0x0A8)
        ("avx_high", XMMReg * 16),            # 16 x 128-bit AVX upper halves (0x1A8)
        ("gs_base", ctypes.c_uint64),         # Thread-local storage (TLS) base (0x2A8)
        ("fs_base", ctypes.c_uint64),         # FS base (0x2B0)
        ("mem_base", ctypes.c_uint64),        # Guest-to-host memory translation base (0x2B8)
        ("trap_code", ctypes.c_uint64),       # Reason code if execution traps (0x2C0)
        ("exit_code", ctypes.c_uint64),       # Host exit / completion status (0x2C8)
    ]

# ABI v2 Flags
BBR_ABI_VERSION = 2
BBR_FLAG_RESUME_ENTRIES = 1 << 0
BBR_FLAG_DIRTY_CHECKS   = 1 << 1
BBR_FLAG_VARIANTS       = 1 << 2
BBR_FLAG_HOOK_SLOTS     = 1 << 3

# Trap Reason Constants
BBR_TRAP_UNSUPPORTED = 1 << 63
BBR_TRAP_UNLIFTABLE  = 1 << 62
BBR_TRAP_MISS        = 1 << 61
BBR_TRAP_DIV_ZERO    = 1 << 60
BBR_TRAP_OVERFLOW    = 1 << 59
