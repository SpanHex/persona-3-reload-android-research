// SPDX-License-Identifier: MIT
// Synthetic Test Fixture 05: Control Flow, Atomics & Memory Barriers
// Target ISA: x86-64 (System V AMD64 ABI)

#include <stdint.h>
#include <stdbool.h>

// 1. Spin-Wait Loop Simulation with Loop Bound
__attribute__((noinline))
uint64_t test_spin_wait_simulation(uint32_t count) {
    volatile uint32_t lock_counter = count;
    uint32_t iterations = 0;
    
    while (lock_counter > 0 && iterations < 100) {
        lock_counter--;
        iterations++;
    }
    return (uint64_t)iterations ^ (uint64_t)lock_counter;
}

// 2. Atomic Fetch-and-Add & Compare-and-Swap (XADD / CMPXCHG)
static volatile uint64_t g_atomic_target = 0;

__attribute__((noinline))
uint64_t test_atomic_operations(void) {
    g_atomic_target = 0;
    
    // Atomic Add (XADD)
    uint64_t add_val = 10;
    uint64_t old_val = __sync_fetch_and_add(&g_atomic_target, add_val);
    
    // Atomic Compare and Swap (CMPXCHG)
    uint64_t expected = 10;
    uint64_t new_val = 50;
    bool success = __sync_bool_compare_and_swap(&g_atomic_target, expected, new_val);
    
    uint64_t final_val = g_atomic_target;
    return old_val + (success ? 1 : 0) + final_val;
}

// 3. Error Propagation & Return Value Encoding
__attribute__((noinline))
int64_t test_error_propagation(int64_t code) {
    if (code < 0) {
        return -1; // Propagated error code
    }
    
    int64_t state = 0;
    for (int i = 0; i < 50; i++) {
        if (i % 7 == 0) {
            continue;
        }
        if (i == 45) {
            break;
        }
        if (i & 1) {
            state -= i;
        } else {
            state += (i * 3);
        }
    }
    
    if (state < 100) {
        return -2;
    }
    return state;
}

// Master Entrypoint for Fixture 05
uint64_t run_fixture_05(void) {
    uint64_t r1 = test_spin_wait_simulation(15);
    uint64_t r2 = test_atomic_operations();
    int64_t  r3 = test_error_propagation(1);
    
    return r1 ^ r2 ^ (uint64_t)(~r3);
}
