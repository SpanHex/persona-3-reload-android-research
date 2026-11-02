// SPDX-License-Identifier: MIT
// Synthetic Test Fixture 02: Direct Calls, Indirect Calls, VTables & Jump Tables
// Target ISA: x86-64 (System V AMD64 ABI)

#include <stdint.h>

// Direct Callee Functions
uint64_t target_func_add(uint64_t a, uint64_t b) { return a + b; }
uint64_t target_func_sub(uint64_t a, uint64_t b) { return a - b; }
uint64_t target_func_mul(uint64_t a, uint64_t b) { return a * b; }
uint64_t target_func_xor(uint64_t a, uint64_t b) { return a ^ b; }

// Function Pointer Type
typedef uint64_t (*math_fn_t)(uint64_t, uint64_t);

// 1. Indirect Call through Function Pointer
uint64_t test_indirect_call(math_fn_t fn, uint64_t x, uint64_t y) {
    return fn(x, y);
}

// 2. Simulated C++ Virtual Table Interface
typedef struct VTable {
    uint64_t (*op1)(void* self, uint64_t v);
    uint64_t (*op2)(void* self, uint64_t v);
} VTable;

typedef struct ObjectA {
    const VTable* vptr;
    uint64_t base_val;
} ObjectA;

typedef struct ObjectB {
    const VTable* vptr;
    uint64_t multiplier;
} ObjectB;

static uint64_t objA_op1(void* self, uint64_t v) { return ((ObjectA*)self)->base_val + v; }
static uint64_t objA_op2(void* self, uint64_t v) { return ((ObjectA*)self)->base_val - v; }
static uint64_t objB_op1(void* self, uint64_t v) { return ((ObjectB*)self)->multiplier * v; }
static uint64_t objB_op2(void* self, uint64_t v) { return ((ObjectB*)self)->multiplier ^ v; }

static const VTable vtable_A = { objA_op1, objA_op2 };
static const VTable vtable_B = { objB_op1, objB_op2 };

uint64_t test_vtable_dispatch(int type, uint64_t val) {
    ObjectA a = { &vtable_A, 500 };
    ObjectB b = { &vtable_B, 3 };
    
    if (type == 0) {
        return a.vptr->op1(&a, val) + a.vptr->op2(&a, val);
    } else {
        return b.vptr->op1(&b, val) + b.vptr->op2(&b, val);
    }
}

// 3. Jump Table / Switch Statement (dense switch lowering to jmp [rip + reg*8])
uint64_t test_switch_jumptable(int selector, uint64_t val) {
    uint64_t out = 0;
    switch (selector) {
        case 0: out = val + 10; break;
        case 1: out = val * 2;  break;
        case 2: out = val ^ 0xFF; break;
        case 3: out = val - 5;  break;
        case 4: out = val << 3; break;
        case 5: out = val >> 2; break;
        case 6: out = val + 0x1000; break;
        case 7: out = val * 7 + 1; break;
        default: out = 0xDEADBEEF; break;
    }
    return out;
}

// Master Entrypoint for Fixture 02
uint64_t run_fixture_02(void) {
    math_fn_t fn_table[4] = {
        target_func_add,
        target_func_sub,
        target_func_mul,
        target_func_xor
    };
    
    uint64_t acc = 0;
    // Test all indirect calls
    for (int i = 0; i < 4; i++) {
        acc += test_indirect_call(fn_table[i], 100, (uint64_t)(i + 1));
    }
    
    // Test VTable dispatch
    acc += test_vtable_dispatch(0, 25);
    acc += test_vtable_dispatch(1, 25);
    
    // Test Jump Table switch cases
    for (int s = 0; s < 8; s++) {
        acc += test_switch_jumptable(s, (uint64_t)(s * 10));
    }
    
    return acc;
}
