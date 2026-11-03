// SPDX-License-Identifier: MIT
/*
 * P3R Native Android AOT Runtime: Guest CPU Interface
 * Matches Recomp ABI v2 (Bloodborne-Android upstream cpu/guest_cpu_aot.cpp)
 */

#ifndef P3R_GUEST_CPU_H
#define P3R_GUEST_CPU_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// Recomp ABI Version
#define BBR_ABI_VERSION 2

// Trap Reason Bitmasks
#define BBR_TRAP_UNSUPPORTED (1ULL << 63)
#define BBR_TRAP_UNLIFTABLE  (1ULL << 62)
#define BBR_TRAP_MISS        (1ULL << 61)
#define BBR_TRAP_DIV_ZERO    (1ULL << 60)
#define BBR_TRAP_OVERFLOW    (1ULL << 59)

// Register Index Enumerations
enum GuestGPR {
    GUEST_RAX = 0,
    GUEST_RCX = 1,
    GUEST_RDX = 2,
    GUEST_RBX = 3,
    GUEST_RSP = 4,
    GUEST_RBP = 5,
    GUEST_RSI = 6,
    GUEST_RDI = 7,
    GUEST_R8  = 8,
    GUEST_R9  = 9,
    GUEST_R10 = 10,
    GUEST_R11 = 11,
    GUEST_R12 = 12,
    GUEST_R13 = 13,
    GUEST_R14 = 14,
    GUEST_R15 = 15,
};

typedef union {
    uint8_t   u8[16];
    uint32_t  u32[4];
    uint64_t  u64[2];
    float     f32[4];
    double    f64[2];
} XMMReg;

/*
 * Exact memory layout of GuestState (720 bytes)
 * Aligned to 16 bytes (natural alignment for 128-bit vector registers).
 */
typedef struct GuestState {
    uint64_t gregs[16];     // Offset 0x000 (128B)
    uint64_t rip;           // Offset 0x080 (8B)
    uint64_t flags;         // Offset 0x088 (8B)
    uint32_t pf_raw;        // Offset 0x090 (4B)
    uint32_t af_raw;        // Offset 0x094 (4B)
    uint32_t df_raw;        // Offset 0x098 (4B)
    uint32_t _pad0;         // Offset 0x09C (4B)
    uint64_t resume_flag;   // Offset 0x0A0 (8B)
    XMMReg   xmm[16];       // Offset 0x0A8 (256B)
    XMMReg   avx_high[16];  // Offset 0x1A8 (256B)
    uint64_t gs_base;       // Offset 0x2A8 (8B)
    uint64_t fs_base;       // Offset 0x2B0 (8B)
    uint64_t mem_base;      // Offset 0x2B8 (8B)
    uint64_t trap_code;     // Offset 0x2C0 (8B)
    uint64_t exit_code;     // Offset 0x2C8 (8B)
} __attribute__((aligned(16))) GuestState;

// Compile-time static verification of binary layout & offsets (Milestone 5)
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

// Recompiled Unit Function Pointer
typedef void (*bbr_func_t)(GuestState*);

typedef struct RecompUnit {
    uint64_t vaddr;
    bbr_func_t func;
} RecompUnit;

// Runtime Public API
void bbr_init_guest_state(GuestState* state, void* stack_base, size_t stack_size, uint64_t mem_base);
void bbr_dispatch(GuestState* state, uint64_t target_vaddr);
void bbr_trap(GuestState* state, uint64_t trap_code);
bbr_func_t bbr_lookup(uint64_t vaddr);
uint64_t bbr_run_entry(GuestState* state, uint64_t entry_vaddr);

#ifdef __cplusplus
}
#endif

#endif // P3R_GUEST_CPU_H
