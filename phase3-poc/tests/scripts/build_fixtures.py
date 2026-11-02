#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
Synthetic Test Fixture Builder
Assembles synthetic x86-64 machine code for fixtures 01..05 using Keystone.
Emits relocatable binary code blobs and address maps into phase3-poc/tests/bin/
Master entrypoint `run_fixture_XX` is placed at offset 0 (base_vaddr) to test
iterative CFG function discovery.
"""

import os
import json
import keystone
import capstone

ks = keystone.Ks(keystone.KS_ARCH_X86, keystone.KS_MODE_64)
cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
cs.detail = True

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bin")
os.makedirs(OUT_DIR, exist_ok=True)

# -------------------------------------------------------------
# Fixture 01: Arithmetic, Safe Division, Floats & Recursion
# Base VAddr: 0x401000 (run_fixture_01)
# -------------------------------------------------------------
ASM_01 = """
// 0x401000: run_fixture_01() - Master Entrypoint
run_fixture_01:
    push rbp
    mov rbp, rsp
    push rbx
    push r12
    push r13

    // 1. test_integer_ops(42, 7)
    mov rdi, 42
    mov rsi, 7
    call test_integer_ops
    mov rbx, rax

    // 2. test_factorial(10)
    mov rdi, 10
    call test_factorial
    mov r12, rax

    // 3. test_fibonacci(12)
    mov rdi, 12
    call test_fibonacci
    mov r13, rax

    // Combine results: rbx ^ (r12 * 7) ^ (r13 << 32)
    mov rax, r12
    imul rax, 7
    xor rax, rbx
    shl r13, 32
    xor rax, r13

    pop r13
    pop r12
    pop rbx
    pop rbp
    ret

// test_integer_ops(a in rdi, b in rsi)
test_integer_ops:
    push rbp
    mov rbp, rsp
    push rbx
    push r12
    push r13
    push r14
    push r15

    // sum = a + b
    mov r8, rdi
    add r8, rsi
    // diff = a - b
    mov r9, rdi
    sub r9, rsi
    // prod = a * b
    mov r10, rdi
    imul r10, rsi

    // Safe division: sdiv = (rsi != 0) ? (rdi / rsi) : 0
    test rsi, rsi
    jz div_by_zero_s
    mov rax, rdi
    cqo
    idiv rsi
    mov r11, rax
    jmp div_done_s
div_by_zero_s:
    xor r11, r11
div_done_s:

    // udiv = (rsi != 0) ? ((uint64)rdi / (uint64)rsi) : 0
    test rsi, rsi
    jz div_by_zero_u
    mov rax, rdi
    xor rdx, rdx
    div rsi
    mov r12, rax
    jmp div_done_u
div_by_zero_u:
    xor r12, r12
div_done_u:

    // bitwise ops
    mov r13, rdi
    and r13, rsi
    mov r14, rdi
    or r14, rsi
    mov r15, rdi
    xor r15, rsi

    // Hash accumulator
    mov rax, 0x9E3779B97F4A7C15
    add rax, r8
    xor rax, r9
    add rax, r10
    xor rax, r11
    add rax, r12
    xor rax, r13
    add rax, r14
    xor rax, r15

    pop r15
    pop r14
    pop r13
    pop r12
    pop rbx
    pop rbp
    ret

// test_factorial(n in rdi)
test_factorial:
    cmp rdi, 1
    jle fact_base
    push rdi
    dec rdi
    call test_factorial
    pop rdi
    imul rax, rdi
    ret
fact_base:
    mov rax, 1
    ret

// test_fibonacci(n in rdi)
test_fibonacci:
    cmp rdi, 0
    je fib_zero
    cmp rdi, 1
    je fib_one
    push rbx
    push r12
    mov rbx, rdi
    dec rdi
    call test_fibonacci
    mov r12, rax
    mov rdi, rbx
    sub rdi, 2
    call test_fibonacci
    add rax, r12
    pop r12
    pop rbx
    ret
fib_zero:
    xor rax, rax
    ret
fib_one:
    mov rax, 1
    ret
"""

# -------------------------------------------------------------
# Fixture 02: Dispatch, Indirect Calls, VTables & Jump Tables
# Base VAddr: 0x402000 (run_fixture_02)
# -------------------------------------------------------------
ASM_02 = """
// 0x402000: run_fixture_02() - Master Entrypoint
run_fixture_02:
    push rbp
    mov rbp, rsp
    push rbx
    push r12
    push r13

    // 1. Indirect calls through registers
    mov rdi, 100
    mov rsi, 20
    lea rdx, [rip + target_func_add - 7]
    call test_indirect_call
    mov rbx, rax

    mov rdi, 100
    mov rsi, 20
    lea rdx, [rip + target_func_sub - 7]
    call test_indirect_call
    add rbx, rax

    mov rdi, 100
    mov rsi, 20
    lea rdx, [rip + target_func_mul - 7]
    call test_indirect_call
    add rbx, rax

    // 2. Switch jump table tests
    mov rdi, 0
    mov rsi, 50
    call test_switch_jumptable
    add rbx, rax

    mov rdi, 1
    mov rsi, 50
    call test_switch_jumptable
    add rbx, rax

    mov rdi, 2
    mov rsi, 50
    call test_switch_jumptable
    add rbx, rax

    mov rdi, 3
    mov rsi, 50
    call test_switch_jumptable
    add rbx, rax

    mov rax, rbx
    pop r13
    pop r12
    pop rbx
    pop rbp
    ret

// target_func_add(a in rdi, b in rsi)
target_func_add:
    mov rax, rdi
    add rax, rsi
    ret

// target_func_sub(a in rdi, b in rsi)
target_func_sub:
    mov rax, rdi
    sub rax, rsi
    ret

// target_func_mul(a in rdi, b in rsi)
target_func_mul:
    mov rax, rdi
    imul rax, rsi
    ret

// target_func_xor(a in rdi, b in rsi)
target_func_xor:
    mov rax, rdi
    xor rax, rsi
    ret

// test_indirect_call(fn in rdx, a in rdi, b in rsi)
test_indirect_call:
    call rdx
    ret

// test_switch_jumptable(selector in rdi, val in rsi)
test_switch_jumptable:
    cmp rdi, 3
    je case_3
    cmp rdi, 2
    je case_2
    cmp rdi, 1
    je case_1
    cmp rdi, 0
    je case_0
    mov rax, 0xDEAD
    ret
case_0:
    mov rax, rsi
    add rax, 10
    ret
case_1:
    mov rax, rsi
    imul rax, 2
    ret
case_2:
    mov rax, rsi
    xor rax, 0xFF
    ret
case_3:
    mov rax, rsi
    sub rax, 5
    ret
"""

# -------------------------------------------------------------
# Fixture 03: Memory Access, Structs, Relocations & Stack Alignment
# Base VAddr: 0x403000 (run_fixture_03)
# -------------------------------------------------------------
ASM_03 = """
// 0x403000: run_fixture_03() - Master Entrypoint
run_fixture_03:
    push rbp
    mov rbp, rsp
    push rbx
    push r12

    call test_struct_traversal
    mov rbx, rax

    mov rdi, 0x100000000
    call test_stack_frame_alignment
    mov r12, rax

    mov rax, rbx
    xor rax, r12

    pop r12
    pop rbx
    pop rbp
    ret

// test_struct_traversal()
test_struct_traversal:
    push rbp
    mov rbp, rsp
    sub rsp, 96

    // Construct Node 3 on stack at [rsp + 64]
    mov qword ptr [rsp + 64], 3000
    mov qword ptr [rsp + 72], 0 // NULL

    // Construct Node 2 at [rsp + 32]
    mov qword ptr [rsp + 32], 2000
    lea rax, [rsp + 64]
    mov qword ptr [rsp + 40], rax

    // Construct Node 1 at [rsp]
    mov qword ptr [rsp], 1000
    lea rax, [rsp + 32]
    mov qword ptr [rsp + 8], rax

    // Traverse list
    xor rax, rax // sum = 0
    lea rdx, [rsp] // cur = &n1
traverse_loop:
    test rdx, rdx
    jz traverse_done
    add rax, qword ptr [rdx]
    mov rdx, qword ptr [rdx + 8]
    jmp traverse_loop
traverse_done:
    add rsp, 96
    pop rbp
    ret

// test_stack_frame_alignment(salt in rdi)
test_stack_frame_alignment:
    push rbp
    mov rbp, rsp
    sub rsp, 256

    // Verify 16-byte stack alignment
    mov rax, rsp
    and rax, 0xF
    test rax, rax
    jnz unaligned_trap

    // Fill local stack array
    mov qword ptr [rsp], rdi
    mov qword ptr [rsp + 8], 0x1234
    mov qword ptr [rsp + 16], 0x5678

    mov rax, qword ptr [rsp]
    xor rax, qword ptr [rsp + 8]
    add rax, qword ptr [rsp + 16]

    add rsp, 256
    pop rbp
    ret
unaligned_trap:
    mov rax, 0xBADF00D
    add rsp, 256
    pop rbp
    ret
"""

# -------------------------------------------------------------
# Fixture 04: Vector SIMD Operations (SSE/SSE2)
# Base VAddr: 0x404000 (run_fixture_04)
# -------------------------------------------------------------
ASM_04 = """
// 0x404000: run_fixture_04() - Master Entrypoint
run_fixture_04:
    push rbp
    mov rbp, rsp
    push rbx

    call test_vector_float_ops
    mov rbx, rax

    call test_vector_int_ops
    add rbx, rax

    call test_vector_double_ops
    add rbx, rax

    mov rax, rbx
    pop rbx
    pop rbp
    ret

// test_vector_float_ops()
test_vector_float_ops:
    push rbp
    mov rbp, rsp
    sub rsp, 64

    movaps xmm0, xmm1
    addps xmm0, xmm2
    mulps xmm0, xmm1

    mov rax, 100
    add rsp, 64
    pop rbp
    ret

// test_vector_int_ops()
test_vector_int_ops:
    paddd xmm0, xmm1
    psubd xmm0, xmm2
    pxor xmm0, xmm3
    mov rax, 200
    ret

// test_vector_double_ops()
test_vector_double_ops:
    mulpd xmm0, xmm1
    subpd xmm0, xmm2
    mov rax, 300
    ret
"""

# -------------------------------------------------------------
# Fixture 05: Control Flow, Spin-Waits & Atomics
# Base VAddr: 0x405000 (run_fixture_05)
# -------------------------------------------------------------
ASM_05 = """
// 0x405000: run_fixture_05() - Master Entrypoint
run_fixture_05:
    push rbp
    mov rbp, rsp
    push rbx
    push r12

    mov rdi, 15
    call test_spin_wait_simulation
    mov rbx, rax

    call test_atomic_operations
    add rbx, rax

    mov rdi, 10
    call test_error_propagation
    add rbx, rax

    mov rax, rbx
    pop r12
    pop rbx
    pop rbp
    ret

// test_spin_wait_simulation(count in rdi)
test_spin_wait_simulation:
    mov rax, rdi
spin_loop:
    test rax, rax
    jle spin_done
    dec rax
    jmp spin_loop
spin_done:
    ret

// test_atomic_operations()
test_atomic_operations:
    push rbp
    mov rbp, rsp
    sub rsp, 16

    mov qword ptr [rsp], 100
    mov rax, 25
    xadd qword ptr [rsp], rax

    mov rax, 125
    mov rdx, 200
    cmpxchg qword ptr [rsp], rdx

    mov rax, qword ptr [rsp]
    add rsp, 16
    pop rbp
    ret

// test_error_propagation(code in rdi)
test_error_propagation:
    test rdi, rdi
    js error_bail
    mov rax, rdi
    imul rax, 3
    ret
error_bail:
    mov rax, -1
    ret
"""

FIXTURES = [
    ("01_arithmetic", ASM_01, 0x401000),
    ("02_dispatch", ASM_02, 0x402000),
    ("03_memory_reloc", ASM_03, 0x403000),
    ("04_vector_simd", ASM_04, 0x404000),
    ("05_control_concurrency", ASM_05, 0x405000),
]

def main():
    print("[*] Rebuilding synthetic fixtures with entrypoints at base_vaddr...")
    manifest = {}

    for name, asm_src, base_vaddr in FIXTURES:
        enc, count = ks.asm(asm_src, base_vaddr)
        code_bytes = bytes(enc)
        bin_path = os.path.join(OUT_DIR, f"{name}.bin")

        with open(bin_path, "wb") as f:
            f.write(code_bytes)

        insns = list(cs.disasm(code_bytes, base_vaddr))
        print(f"[+] Fixture '{name}': {count} insns ({len(code_bytes)} bytes) at {hex(base_vaddr)}")

        manifest[name] = {
            "binary_path": bin_path,
            "base_vaddr": hex(base_vaddr),
            "entry_vaddr": hex(base_vaddr),
            "size_bytes": len(code_bytes),
            "instruction_count": count
        }

    with open(os.path.join(OUT_DIR, "fixtures_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print("[+] All fixtures rebuilt successfully.")

if __name__ == "__main__":
    main()
