// SPDX-License-Identifier: MIT
// Synthetic Test Fixture 01: Integer, Scalar Float & Recursive Arithmetic
// Target ISA: x86-64 (System V AMD64 ABI)

#include <stdint.h>
#include <stddef.h>

// 1. Basic Integer Arithmetic & Bitwise
__attribute__((noinline))
uint64_t test_integer_ops(int64_t a, int64_t b) {
    uint64_t sum = (uint64_t)(a + b);
    uint64_t diff = (uint64_t)(a - b);
    uint64_t prod = (uint64_t)(a * b);
    
    // Safe division: guard against divide-by-zero
    uint64_t sdiv = b != 0 ? (uint64_t)(a / b) : 0;
    uint64_t udiv = (uint64_t)b != 0 ? ((uint64_t)a / (uint64_t)b) : 0;
    uint64_t mod = b != 0 ? (uint64_t)(a % b) : 0;
    
    uint64_t bit_and = (uint64_t)a & (uint64_t)b;
    uint64_t bit_or  = (uint64_t)a | (uint64_t)b;
    uint64_t bit_xor = (uint64_t)a ^ (uint64_t)b;
    uint64_t lsh     = (uint64_t)a << (b & 63);
    uint64_t rsh     = (uint64_t)a >> (b & 63);
    
    // Hash accumulation
    uint64_t hash = 0x9E3779B97F4A7C15ULL;
    hash ^= sum + (hash << 6) + (hash >> 2);
    hash ^= diff + (hash << 6) + (hash >> 2);
    hash ^= prod + (hash << 6) + (hash >> 2);
    hash ^= sdiv + (hash << 6) + (hash >> 2);
    hash ^= udiv + (hash << 6) + (hash >> 2);
    hash ^= mod  + (hash << 6) + (hash >> 2);
    hash ^= bit_and + bit_or + bit_xor + lsh + rsh;
    return hash;
}

// 2. High-Byte Register Test (AH, CH, DH, BH)
__attribute__((noinline))
uint64_t test_high_bytes(uint64_t val) {
    uint64_t r = val;
    __asm__ volatile (
        "movb $0x5A, %%ah\n\t"
        "movb $0xA5, %%ch\n\t"
        "movb $0x3C, %%dh\n\t"
        "movb $0xC3, %%bh\n\t"
        : "+a"(r)
        :
        : "rcx", "rdx", "rbx"
    );
    return r;
}

// 3. Scalar Floating Point Arithmetic (Float and Double)
__attribute__((noinline))
double test_float_ops(double x, double y) {
    double add = x + y;
    double sub = x - y;
    double mul = x * y;
    double div = (y != 0.0) ? (x / y) : 0.0;
    
    // Convert to float and back
    float f_val = (float)(add + sub);
    float f_mul = (float)mul * 0.5f;
    
    return (double)f_val + (double)f_mul + div;
}

// 4. Recursive Call Test (Factorial)
__attribute__((noinline))
uint64_t test_factorial(uint64_t n) {
    if (n <= 1) return 1;
    return n * test_factorial(n - 1);
}

// 5. Recursive Call Test (Fibonacci)
__attribute__((noinline))
uint64_t test_fibonacci(uint64_t n) {
    if (n == 0) return 0;
    if (n == 1) return 1;
    return test_fibonacci(n - 1) + test_fibonacci(n - 2);
}

// Master Entrypoint for Fixture 01
uint64_t run_fixture_01(void) {
    uint64_t r1 = test_integer_ops(42, 7);
    uint64_t r2 = test_high_bytes(0x1122334455667788ULL);
    double r3 = test_float_ops(100.5, 4.0);
    uint64_t r4 = test_factorial(10);
    uint64_t r5 = test_fibonacci(12);
    
    uint64_t combined = r1 ^ r2 ^ (uint64_t)(r3 * 1000.0) ^ r4 ^ (r5 << 32);
    return combined;
}
