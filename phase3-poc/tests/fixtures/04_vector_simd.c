// SPDX-License-Identifier: MIT
// Synthetic Test Fixture 04: Vector SIMD Instructions (SSE, SSE2, SSE4.1)
// Target ISA: x86-64 (System V AMD64 ABI)

#include <stdint.h>

// Software/Compiler-portable 128-bit vector types mapped to SSE/NEON
typedef float    v4sf __attribute__((vector_size(16)));
typedef int32_t  v4si __attribute__((vector_size(16)));
typedef double   v2df __attribute__((vector_size(16)));

// 1. Packed 32-bit Float Arithmetic (SSE / SSE2)
__attribute__((noinline))
uint64_t test_vector_float_ops(uint64_t seed) {
    float f = (float)(seed & 0xFF);
    volatile v4sf a = { f + 1.0f, f + 2.0f, f + 3.0f, f + 4.0f };
    volatile v4sf b = { 10.0f, 20.0f, 30.0f, 40.0f };
    
    v4sf sum = a + b;
    v4sf sub = b - a;
    v4sf mul = sum * sub;
    
    float out[4];
    *(v4sf*)out = mul;
    
    uint64_t res = 0;
    for (int i = 0; i < 4; i++) {
        res ^= (uint64_t)(out[i]);
    }
    return res;
}

// 2. Packed 32-bit Integer Vector Math & Bitwise (SSE2 / SSSE3)
__attribute__((noinline))
uint64_t test_vector_int_ops(uint64_t seed) {
    int32_t s = (int32_t)(seed & 0xFF);
    volatile v4si a = { s + 100, s + 200, s + 300, s + 400 };
    volatile v4si b = { 7, 8, 9, 10 };
    
    v4si sum = a + b;
    v4si sub = a - b;
    v4si xor_val = sum ^ sub;
    
    int32_t out[4];
    *(v4si*)out = xor_val;
    
    uint64_t combined = 0;
    for (int i = 0; i < 4; i++) {
        combined += (uint64_t)out[i] << (i * 8);
    }
    return combined;
}

// 3. Packed Double Precision (SSE2)
__attribute__((noinline))
uint64_t test_vector_double_ops(uint64_t seed) {
    double d = (double)(seed & 0xFF);
    volatile v2df a = { d + 1234.0, d + 8765.0 };
    volatile v2df b = { 2.0, 3.0 };
    
    v2df prod = a * b;
    v2df diff = prod - a;
    
    double out[2];
    *(v2df*)out = diff;
    
    return (uint64_t)out[0] ^ (uint64_t)out[1];
}

// Master Entrypoint for Fixture 04
uint64_t run_fixture_04(void) {
    uint64_t r1 = test_vector_float_ops(42);
    uint64_t r2 = test_vector_int_ops(42);
    uint64_t r3 = test_vector_double_ops(42);
    
    return r1 + r2 + r3;
}
