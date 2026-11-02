// SPDX-License-Identifier: MIT
// Synthetic Test Fixture 03: Memory Access, Globals, Structs & Relocations
// Target ISA: x86-64 (System V AMD64 ABI)

#include <stdint.h>
#include <stddef.h>

// Global Data: Read-Only (rodata) and Writable (data/bss)
static const uint64_t g_rodata_lut[8] = {
    0x0102030405060708ULL, 0x1112131415161718ULL,
    0x2122232425262728ULL, 0x3132333435363738ULL,
    0x4142434445464748ULL, 0x5152535455565758ULL,
    0x6162636465666768ULL, 0x7172737475767778ULL
};

static uint64_t g_data_counter = 0x1000;
static uint64_t g_bss_buffer[16];

// Nested Structure with various data widths
typedef struct Node {
    uint32_t id;
    uint16_t flags;
    uint8_t  tag;
    uint8_t  pad;
    uint64_t value;
    struct Node* next;
} Node;

// Pointer arithmetic and structure traversal
uint64_t test_struct_traversal(void) {
    Node n3 = { 3, 0x03, 0xAA, 0, 3000, NULL };
    Node n2 = { 2, 0x02, 0xBB, 0, 2000, &n3 };
    Node n1 = { 1, 0x01, 0xCC, 0, 1000, &n2 };
    
    uint64_t sum = 0;
    Node* cur = &n1;
    while (cur != NULL) {
        sum += cur->value;
        sum += cur->id;
        sum += (uint64_t)cur->tag;
        cur = cur->next;
    }
    return sum;
}

// Global Relocations & Buffer Manipulation
uint64_t test_global_access(uint64_t input) {
    g_data_counter += input;
    
    for (int i = 0; i < 8; i++) {
        g_bss_buffer[i] = g_rodata_lut[i] ^ g_data_counter;
    }
    
    uint64_t xor_sum = 0;
    for (int i = 0; i < 8; i++) {
        xor_sum ^= g_bss_buffer[i];
    }
    return xor_sum;
}

// Stack Array & Alignment Test
uint64_t test_stack_frame_alignment(uint64_t salt) {
    uint64_t local_arr[32];
    for (int i = 0; i < 32; i++) {
        local_arr[i] = salt * (uint64_t)(i + 1);
    }
    
    uint64_t res = 0;
    for (int i = 0; i < 32; i += 2) {
        res += local_arr[i] ^ local_arr[i + 1];
    }
    return res;
}

// Master Entrypoint for Fixture 03
uint64_t run_fixture_03(void) {
    uint64_t r1 = test_struct_traversal();
    uint64_t r2 = test_global_access(42);
    uint64_t r3 = test_stack_frame_alignment(0x55AA55AA);
    
    return r1 ^ r2 ^ r3;
}
