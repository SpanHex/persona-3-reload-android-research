// SPDX-License-Identifier: MIT
// Synthetic Test Fixture 06: Multi-Threaded Concurrency, Lock Contention & Atomics
// Target ISA: x86-64 (System V AMD64 ABI)
// Recompilation Target: AArch64 Android Bionic Runtime

#include <stdint.h>
#include <stdbool.h>

// Shared atomic state in guest memory
static volatile uint64_t g_shared_counter = 0;
static volatile uint64_t g_shared_cas_val = 0;
static volatile uint64_t g_shared_lock_acquisitions = 0;

/*
 * Worker 1: Atomic Fetch-and-Add (x86 'lock xaddq')
 * Concurrently adds 'step' to *counter for 'iterations' loops.
 */
__attribute__((noinline))
uint64_t worker_atomic_add(volatile uint64_t* counter, uint64_t iterations, uint64_t step) {
    if (!counter) return 0;
    uint64_t accum_old = 0;
    for (uint64_t i = 0; i < iterations; i++) {
        accum_old += __sync_fetch_and_add(counter, step);
    }
    return accum_old;
}

/*
 * Worker 2: Atomic Compare-and-Swap Loop (x86 'lock cmpxchgq')
 * Retries CAS until the value is incremented by 1 for 'iterations' times.
 */
__attribute__((noinline))
uint64_t worker_cas_increment(volatile uint64_t* target, uint64_t iterations) {
    if (!target) return 0;
    uint64_t retries = 0;
    for (uint64_t i = 0; i < iterations; i++) {
        uint64_t cur;
        do {
            cur = *target;
            retries++;
        } while (!__sync_bool_compare_and_swap(target, cur, cur + 1));
    }
    return retries;
}

/*
 * Worker 3: Spin-lock acquisition and critical section
 * Protects an unprotected counter using an atomic test-and-set spinlock.
 */
static volatile uint32_t g_spinlock = 0;
static volatile uint64_t g_protected_data = 0;

__attribute__((noinline))
void worker_spinlock_critical_section(uint64_t iterations) {
    for (uint64_t i = 0; i < iterations; i++) {
        // Acquire spinlock: test-and-set
        while (__sync_lock_test_and_set(&g_spinlock, 1)) {
            // Spin wait
            #if defined(__x86_64__)
            __asm__ volatile("pause" ::: "memory");
            #elif defined(__aarch64__)
            __asm__ volatile("yield" ::: "memory");
            #endif
        }
        
        // Critical section
        g_protected_data++;
        g_shared_lock_acquisitions++;
        
        // Release spinlock
        __sync_lock_release(&g_spinlock);
    }
}

/*
 * Sequential Reference Entrypoint for Fixture 06
 * Used for single-threaded verification in Unicorn & host reference environments.
 */
uint64_t run_fixture_06(void) {
    g_shared_counter = 0;
    g_shared_cas_val = 0;
    g_spinlock = 0;
    g_protected_data = 0;
    g_shared_lock_acquisitions = 0;

    // Sequential run of worker operations
    uint64_t add_accum = worker_atomic_add(&g_shared_counter, 1000, 3);
    uint64_t cas_retries = worker_cas_increment(&g_shared_cas_val, 500);
    worker_spinlock_critical_section(200);

    // Expected values:
    // g_shared_counter = 3000
    // g_shared_cas_val = 500
    // g_protected_data = 200
    // g_shared_lock_acquisitions = 200
    // Return hash combining all results
    uint64_t result = g_shared_counter ^ (g_shared_cas_val << 16) ^ (g_protected_data << 32) ^ add_accum ^ cas_retries;
    return result;
}
