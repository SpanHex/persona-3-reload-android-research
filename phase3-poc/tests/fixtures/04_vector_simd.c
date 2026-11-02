// SPDX-License-Identifier: MIT
// Synthetic Test Fixture 04: Vector SIMD Instructions (SSE, SSE2, SSE4.1)
// Target ISA: x86-64 (System V AMD64 ABI)

#include <stdint.h>

// Software/Compiler-portable 128-bit vector types mapped to SSE/NEON
typedef float    v4sf __attribute__((vector_size(16)));
typedef int32_t  v4si __attribute__((vector_size(16)));
typedef double   v2df __attribute__((vector_size(16)));

// 1. Packed 32-bit Float Arithmetic (SSE / SSE2)
uint64_t test_vector_float_ops(void) {
    v4sf a = { 1.5f, 2.5f, 3.5f, 4.5f };
    v4sf b = { 10.0f, 20.0f, 30.0f, 40.0f };
    
    v4sf sum = a + b;
    v4sf mul = sum * a;
    
    float out[4];
    __builtin_memcpy(out, &mul, sizeof(out));
    
    uint64_t res = 0;
    for (int i = 0; i < 4; i++) {
        res ^= (uint64_t)(out[i] * 100.0f);
    }
    return res;
}

// 2. Packed 32-bit Integer Vector Math & Bitwise (SSE2 / SSSE3)
uint64_t test_vector_int_ops(void) {
    v4si a = { 100, 200, 300, 400 };
    v4si b = { 7, 8, 9, 10 };
    
    v4si sum = a + b;
    v4si sub = a - b;
    v4si xor_val = sum ^ sub;
    v4si and_val = xor_val & a;
    
    int32_t out[4];
    __builtin_memcpy(out, &and_val, sizeof(out));
    
    uint64_t combined = 0;
    for (int i = 0; i < 4; i++) {
        combined += (uint64_t)out[i] << (i * 8);
    }
    return combined;
}

// 3. Packed Double Precision (SSE2)
uint64_t test_vector_double_ops(void) {
    v2df a = { 1234.5678, 8765.4321 };
    v2df b = { 2.0, 3.0 };
    
    v2df prod = a * b;
    v2df diff = prod - a;
    
    double out[2];
    __builtin_memcpy(out, &diff, sizeof(out));
    
    return (uint64_t)out[0] ^ (uint64_t)out[1];
}

// Master Entrypoint for Fixture 04
uint64_t run_fixture_04(void) {
    uint64_t r1 = test_vector_float_ops();
    uint64_t r2 = test_vector_int_ops();
    uint64_t r3 = test_vector_double_ops();
    
    return r1 + r2 + r3;
}
