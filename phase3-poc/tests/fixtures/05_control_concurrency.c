// SPDX-License-Identifier: MIT
// Synthetic Test Fixture 05: Control Flow, Spin-Waits, Atomics & Error Handlers
// Target ISA: x86-64 (System V AMD64 ABI)

#include <stdint.h>

// 1. Spin-Wait Loop Pattern (verifying volatile load preservation in loops)
// In Bloodborne commit ef1a331, spin-wait loops without volatile stores were
// hoisted by LLVM, causing infinite hangs. This test ensures the load remains in-loop.
uint64_t test_spin_wait_simulation(uint32_t initial_counter) {
    volatile uint32_t poll_var = initial_counter;
    uint32_t spins = 0;
    
    // Simulate multi-threaded polling with bounded iterations
    while (poll_var > 0 && spins < 100) {
        spins++;
        poll_var--; // Decrement simulates worker progress
    }
    return (uint64_t)spins ^ (uint64_t)poll_var;
}

// 2. Hardware Atomic Operations (fetch-and-add, compare-and-swap)
static uint64_t g_shared_atomic_counter = 0;

uint64_t test_atomic_operations(void) {
    // __sync_fetch_and_add maps to `lock xadd` on x86-64
    uint64_t prev = __sync_fetch_and_add(&g_shared_atomic_counter, 10);
    
    // __sync_bool_compare_and_swap maps to `lock cmpxchg` on x86-64
    int success = __sync_bool_compare_and_swap(&g_shared_atomic_counter, 10, 50);
    
    return prev + g_shared_atomic_counter + (uint64_t)success;
}

// 3. Complex Nested Control Flow & Error Propagation
int64_t test_error_propagation(int64_t input_code) {
    if (input_code < 0) {
        return -1; // EINVAL
    }
    
    int64_t accumulator = 0;
    for (int i = 0; i < 50; i++) {
        if (i % 7 == 0) continue;
        if (i == 45) break;
        
        if (i % 2 == 0) {
            accumulator += (i * 3);
        } else {
            accumulator -= i;
        }
    }
    
    if (accumulator < 100) {
        return -2; // ERANGE
    }
    return accumulator;
}

// Master Entrypoint for Fixture 05
uint64_t run_fixture_05(void) {
    uint64_t r1 = test_spin_wait_simulation(15);
    uint64_t r2 = test_atomic_operations();
    int64_t  r3 = test_error_propagation(100);
    int64_t  r4 = test_error_propagation(-5);
    
    return r1 ^ r2 ^ (uint64_t)r3 ^ (uint64_t)r4;
}
