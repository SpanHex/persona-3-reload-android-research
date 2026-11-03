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
    Aligned to 16 bytes, total size 720 bytes.
    """
    _fields_ = [
        ("gregs", ctypes.c_uint64 * 16),      # GPRs: RAX..R15 (0x000, 128B)
        ("rip", ctypes.c_uint64),             # Guest instruction pointer (0x080, 8B)
        ("flags", ctypes.c_uint64),           # NZCV / RFLAGS condition flags (0x088, 8B)
        ("pf_raw", ctypes.c_uint32),          # Parity flag raw (0x090, 4B)
        ("af_raw", ctypes.c_uint32),          # Aux carry flag raw (0x094, 4B)
        ("df_raw", ctypes.c_uint32),          # Direction flag raw (0x098, 4B)
        ("_pad0", ctypes.c_uint32),           # Alignment pad (0x09C, 4B)
        ("resume_flag", ctypes.c_uint64),     # Resume entry flag (GranularEntry) (0x0A0, 8B)
        ("xmm", XMMReg * 16),                 # 16 x 128-bit vector registers (0x0A8, 256B)
        ("avx_high", XMMReg * 16),            # 16 x 128-bit AVX upper halves (0x1A8, 256B)
        ("gs_base", ctypes.c_uint64),         # Thread-local storage (TLS) base (0x2A8, 8B)
        ("fs_base", ctypes.c_uint64),         # FS base (0x2B0, 8B)
        ("mem_base", ctypes.c_uint64),        # Guest-to-host memory translation base (0x2B8, 8B)
        ("trap_code", ctypes.c_uint64),       # Reason code if execution traps (0x2C0, 8B)
        ("exit_code", ctypes.c_uint64),       # Host exit / completion status (0x2C8, 8B)
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

def create_aligned_guest_state() -> GuestState:
    """
    Allocates a GuestState instance guaranteed to be 16-byte aligned.
    Resolves the limitation where ctypes.alignment(GuestState) is 8 bytes.
    """
    raw_buf = (ctypes.c_uint8 * (ctypes.sizeof(GuestState) + 16))()
    addr = ctypes.addressof(raw_buf)
    offset = (16 - (addr % 16)) % 16
    st = GuestState.from_buffer(raw_buf, offset)
    st._backing_buffer = raw_buf
    assert ctypes.addressof(st) % 16 == 0, f"Pointer {hex(ctypes.addressof(st))} is not 16-byte aligned"
    return st

# Static runtime verification of binary layout (Milestone 3)
assert ctypes.sizeof(GuestState) == 720, f"Expected GuestState size 720, got {ctypes.sizeof(GuestState)}"
assert GuestState.gregs.offset == 0, f"Expected gregs offset 0, got {GuestState.gregs.offset}"
assert GuestState.rip.offset == 128, f"Expected rip offset 128, got {GuestState.rip.offset}"
assert GuestState.flags.offset == 136, f"Expected flags offset 136, got {GuestState.flags.offset}"
assert GuestState.pf_raw.offset == 144, f"Expected pf_raw offset 144, got {GuestState.pf_raw.offset}"
assert GuestState.af_raw.offset == 148, f"Expected af_raw offset 148, got {GuestState.af_raw.offset}"
assert GuestState.df_raw.offset == 152, f"Expected df_raw offset 152, got {GuestState.df_raw.offset}"
assert GuestState._pad0.offset == 156, f"Expected _pad0 offset 156, got {GuestState._pad0.offset}"
assert GuestState.resume_flag.offset == 160, f"Expected resume_flag offset 160, got {GuestState.resume_flag.offset}"
assert GuestState.xmm.offset == 168, f"Expected xmm offset 168, got {GuestState.xmm.offset}"
assert GuestState.avx_high.offset == 424, f"Expected avx_high offset 424, got {GuestState.avx_high.offset}"
assert GuestState.gs_base.offset == 680, f"Expected gs_base offset 680, got {GuestState.gs_base.offset}"
assert GuestState.fs_base.offset == 688, f"Expected fs_base offset 688, got {GuestState.fs_base.offset}"
assert GuestState.mem_base.offset == 696, f"Expected mem_base offset 696, got {GuestState.mem_base.offset}"
assert GuestState.trap_code.offset == 704, f"Expected trap_code offset 704, got {GuestState.trap_code.offset}"
assert GuestState.exit_code.offset == 712, f"Expected exit_code offset 712, got {GuestState.exit_code.offset}"
