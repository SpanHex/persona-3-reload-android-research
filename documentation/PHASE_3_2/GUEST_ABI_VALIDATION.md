# GuestState ABI v2 Static Verification & Binary Layout Report

## 1. Executive Summary

In Ahead-of-Time (AOT) binary translation, memory layout discrepancies between the compiler's code generator, the C runtime library, and the test orchestrator result in catastrophic memory corruption, silent register desynchronization, and segmentation faults.

Phase 3.2 establishes **formal static verification** of the `GuestState` structure according to the Recomp ABI v2 specification (matching the upstream Bloodborne-Android CPU architecture). The layout is verified through compile-time `_Static_assert` checks in Clang/C11 and runtime assertion checks in Python ctypes.

---

## 2. Field-by-Field Binary Memory Layout

The complete `GuestState` structure occupies exactly **720 bytes** and is aligned to a **16-byte boundary** (the natural alignment for 128-bit ARM NEON vector registers and x86 SSE registers).

| Offset (Hex) | Offset (Dec) | Size (Bytes) | Field Name | C Data Type | Description |
|---|---|---|---|---|---|
| `0x000` | 0 | 128 | `gregs[16]` | `uint64_t[16]` | x86-64 General Purpose Registers (`RAX`..`R15`) in System V AMD64 order |
| `0x080` | 128 | 8 | `rip` | `uint64_t` | Guest Virtual Instruction Pointer |
| `0x088` | 136 | 8 | `flags` | `uint64_t` | Packed RFLAGS condition register (`CF`, `ZF`, `SF`, `OF`, `PF`, `AF`) |
| `0x090` | 144 | 4 | `pf_raw` | `uint32_t` | Raw Parity Flag calculation state |
| `0x094` | 148 | 4 | `af_raw` | `uint32_t` | Raw Auxiliary Carry Flag calculation state |
| `0x098` | 152 | 4 | `df_raw` | `uint32_t` | Raw Direction Flag calculation state |
| `0x09C` | 156 | 4 | `_pad0` | `uint32_t` | Explicit alignment padding to maintain 8-byte alignment for subsequent 64-bit integers |
| `0x0A0` | 160 | 8 | `resume_flag` | `uint64_t` | Granular entrypoint resumption bitmask |
| `0x0A8` | 168 | 256 | `xmm[16]` | `XMMReg[16]` | 16 x 128-bit SSE/AVX low vector registers (`XMM0`..`XMM15`) |
| `0x1A8` | 424 | 256 | `avx_high[16]` | `XMMReg[16]` | 16 x 128-bit AVX upper 128 bits (`YMM0_HI`..`YMM15_HI`) |
| `0x2A8` | 680 | 8 | `gs_base` | `uint64_t` | Thread-Local Storage (TLS) GS segment base pointer |
| `0x2B0` | 688 | 8 | `fs_base` | `uint64_t` | FS segment base pointer |
| `0x2B8` | 696 | 8 | `mem_base` | `uint64_t` | Host virtual memory base for guest virtual-to-host address translation |
| `0x2C0` | 704 | 8 | `trap_code` | `uint64_t` | Fault reason bitmask (`BBR_TRAP_MISS`, `BBR_TRAP_UNLIFTABLE`, etc.) |
| `0x2C8` | 712 | 8 | `exit_code` | `uint64_t` | Host execution completion status (0 = success, 1 = trapped) |
| **`0x2D0`** | **720** | **0** | **TOTAL** | — | **End of Struct (720 bytes = 45 x 16-byte blocks)** |

---

## 3. Structural Alignment Analysis

In earlier revisions, the struct was annotated with `__attribute__((aligned(64)))`. Because 720 is not a multiple of 64 ($720 / 64 = 11.25$), compilers added 48 bytes of implicit tail padding, bumping `sizeof(GuestState)` to 768 bytes in C while ctypes in Python allocated 720 bytes.

In Phase 3.2, this discrepancy was resolved by defining:
```c
typedef struct GuestState {
    // ... fields ...
} __attribute__((aligned(16))) GuestState;
```
Since 720 is an exact multiple of 16 ($720 = 16 \times 45$), the tail padding is precisely zero bytes, guaranteeing that `sizeof(GuestState) == 720` across both C and Python without any hidden compiler padding.

---

## 4. Compile-Time Static Assertions (`guest_cpu.h`)

The following C11 `_Static_assert` validations are compiled into every compilation unit:

```c
#if (defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L) || defined(__clang__) || defined(__GNUC__)
_Static_assert(sizeof(GuestState) == 720, "GuestState size must be exactly 720 bytes");
_Static_assert(offsetof(GuestState, gregs) == 0, "GuestState::gregs offset mismatch");
_Static_assert(offsetof(GuestState, rip) == 128, "GuestState::rip offset mismatch");
_Static_assert(offsetof(GuestState, flags) == 136, "GuestState::flags offset mismatch");
_Static_assert(offsetof(GuestState, pf_raw) == 144, "GuestState::pf_raw offset mismatch");
_Static_assert(offsetof(GuestState, af_raw) == 148, "GuestState::af_raw offset mismatch");
_Static_assert(offsetof(GuestState, df_raw) == 152, "GuestState::df_raw offset mismatch");
_Static_assert(offsetof(GuestState, _pad0) == 156, "GuestState::_pad0 offset mismatch");
_Static_assert(offsetof(GuestState, resume_flag) == 160, "GuestState::resume_flag offset mismatch");
_Static_assert(offsetof(GuestState, xmm) == 168, "GuestState::xmm offset mismatch");
_Static_assert(offsetof(GuestState, avx_high) == 424, "GuestState::avx_high offset mismatch");
_Static_assert(offsetof(GuestState, gs_base) == 680, "GuestState::gs_base offset mismatch");
_Static_assert(offsetof(GuestState, fs_base) == 688, "GuestState::fs_base offset mismatch");
_Static_assert(offsetof(GuestState, mem_base) == 696, "GuestState::mem_base offset mismatch");
_Static_assert(offsetof(GuestState, trap_code) == 704, "GuestState::trap_code offset mismatch");
_Static_assert(offsetof(GuestState, exit_code) == 712, "GuestState::exit_code offset mismatch");
_Static_assert(_Alignof(GuestState) == 16, "GuestState alignment must be 16 bytes");
#endif
```

---

## 5. Python ctypes Verification (`phase3-poc/compiler/abi.py`)

At module load time, `abi.py` validates byte offsets and size:

```python
assert ctypes.sizeof(GuestState) == 720
assert GuestState.gregs.offset == 0
assert GuestState.rip.offset == 128
assert GuestState.flags.offset == 136
assert GuestState.pf_raw.offset == 144
assert GuestState.af_raw.offset == 148
assert GuestState.df_raw.offset == 152
assert GuestState._pad0.offset == 156
assert GuestState.resume_flag.offset == 160
assert GuestState.xmm.offset == 168
assert GuestState.avx_high.offset == 424
assert GuestState.gs_base.offset == 680
assert GuestState.fs_base.offset == 688
assert GuestState.mem_base.offset == 696
assert GuestState.trap_code.offset == 704
assert GuestState.exit_code.offset == 712
```

---

## 6. Execution Calling Convention (AAPCS64)

The recompiled functions follow standard ARM64 Procedure Call Standard (AAPCS64):
- **Register `X0`:** Pointer to `GuestState` struct (`GuestState* state`). Passed as the sole argument.
- **Register `SP`:** Dedicated host execution stack pointer (minimum 256 KB allocated per thread).
- **Register `X30` (LR):** Link register holding host return address.
- **Callee-Saved Registers (`X19`..`X28`):** Preserved across calls according to AAPCS64 rules.
- **Return Value:** In accordance with the System V AMD64 ABI, the guest return value is deposited into `state->gregs[GUEST_RAX]` (offset `0x000`).
