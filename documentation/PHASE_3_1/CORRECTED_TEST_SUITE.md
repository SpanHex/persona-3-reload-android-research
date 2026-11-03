# Phase 3.1: Corrected Authoritative Test Suite

## Overview & Design Principles

The Phase 3 test fixtures were initially compiled from basic synthetic assembly snippets with synthetic expectations. To establish an undeniable, mathematically reproducible ground truth, Phase 3.1 replaced all synthetic fixtures with **authoritative C programs** (`01_arithmetic.c` through `05_control_concurrency.c`).

Each fixture is compiled with Clang into a static, freestanding x86-64 ELF executable:
```bash
clang -target x86_64-unknown-linux-gnu -O2 -c \
      -fno-asynchronous-unwind-tables -fno-stack-protector <fixture>.c -o <fixture>.elf.o
clang -target x86_64-unknown-linux-gnu -nostdlib -static \
      -Wl,-e,run_fixture_XX <fixture>.elf.o -o <fixture>.elf
```

### Anti-Folding & Anti-Devirtualization Safeguards
To ensure that the recompiler exercises real machine instructions rather than constant-folded results:
1. Every sub-test is declared with `__attribute__((noinline))`.
2. Dynamic dispatch tables are referenced through `volatile` function pointers (`math_fn_t volatile*`).
3. Memory buffers, counters, and atomic variables are marked `volatile`.
4. Loops and recursion have non-trivial termination bounds.

---

## Detailed Fixture Breakdown

### Fixture 01: `01_arithmetic`
- **Source File:** `phase3-poc/tests/fixtures/01_arithmetic.c`
- **Target Subsystems:** Integer arithmetic, high-byte registers (`ah`, `ch`, `dh`, `bh`), 64-bit 128-bit numerator division (`idivq`, `divq`), scalar IEEE 754 floating point arithmetic (`addsd`, `subsd`, `mulsd`, `divsd`, `ucomisd`), and deep recursion.
- **Key Functions:**
  - `test_high_byte_regs(uint64_t val)`: Exercises bit operations on `ah`, `ch`, `dh`, `bh`.
  - `test_safe_division(uint64_t a, uint64_t b, int64_t s1, int64_t s2)`: Performs 64-bit unsigned and signed divisions requiring compiler-rt `__udivti3` and `__divti3` routines.
  - `test_float_ops(double a, double b)`: Computes mixed float/double expressions and unordered comparisons (`ucomisd`).
  - `test_recursive_factorial(uint32_t n)`: 12-level recursion verifying guest stack frame allocation and SysV AMD64 return conventions.
  - `test_fibonacci(uint32_t n)`: Double recursion exercising register preservation across stack frames.
- **Entrypoint:** `run_fixture_01` (`0x2013d0`)
- **Authoritative Ground Truth:**
  - Return Value: `14395263374464838504` (`0xc7c63fc50b2aeb68`)

---

### Fixture 02: `02_dispatch`
- **Source File:** `phase3-poc/tests/fixtures/02_dispatch.c`
- **Target Subsystems:** Direct calls, indirect calls via function pointers, simulated C++ virtual method table (vtable) dispatch, and dense switch statements lowering to jump tables.
- **Key Functions:**
  - `test_indirect_call(math_fn_t fn, uint64_t x, uint64_t y)`: Tail call through register (`jmpq *%rax`).
  - `test_vtable_dispatch(int type, uint64_t val)`: Instantiates `ObjectA` and `ObjectB` with virtual function pointer tables (`vtable_A`, `vtable_B`), executing polymorphic method calls.
  - `test_switch_jumptable(int selector, uint64_t val)`: Dense 8-way switch statement compiled into a 32-bit PC-relative jump table (`.rodata`) indexed by `movslq (%rdx, %rcx, 4), %rcx; addq %rdx, %rcx; jmpq *%rcx`.
- **Entrypoint:** `run_fixture_02` (`0x2012a0`)
- **Authoritative Ground Truth:**
  - Return Value: `6965` (`0x1b35`)

---

### Fixture 03: `03_memory_reloc`
- **Source File:** `phase3-poc/tests/fixtures/03_memory_reloc.c`
- **Target Subsystems:** Global `.rodata` constant reading, `.data` array mutations, pointer arithmetic, struct memory traversal, and 16-byte stack pointer alignment enforcement.
- **Key Functions:**
  - `test_global_data_access(uint64_t offset)`: Reads `g_rodata_string` in `.rodata` and mutates `g_data_array` in `.data`.
  - `test_struct_traversal(uint32_t count)`: Traversals across an array of nested structures (`Point3D`, `Node`) with mixed 32-bit and 64-bit alignment paddings.
  - `test_stack_alignment(void)`: Verifies that $(RSP - 8) \pmod{16} == 0$ upon function entry in accordance with System V AMD64 ABI specifications.
- **Entrypoint:** `run_fixture_03` (`0x201340`)
- **Authoritative Ground Truth:**
  - Return Value: `180287561799` (`0x29f9f9e047`)

---

### Fixture 04: `04_vector_simd`
- **Source File:** `phase3-poc/tests/fixtures/04_vector_simd.c`
- **Target Subsystems:** 128-bit vector arithmetic across single-precision floating point (SSE), integer SIMD (SSE2/SSSE3), and double-precision floating point (SSE2).
- **Key Functions:**
  - `test_vector_float_ops(uint64_t seed)`: Packed 4x32-bit float vector arithmetic (`addps`, `subps`, `mulps`, `unpcklps`, `movlhps`, `shufps`, `cvttss2si`).
  - `test_vector_int_ops(uint64_t seed)`: Packed 4x32-bit integer arithmetic (`paddd`, `psubd`, `pxor`, `pcmpgtd`, `punpckldq`, `pshufd`, `psllq`, `paddq`, `movq`).
  - `test_vector_double_ops(uint64_t seed)`: Packed 2x64-bit double-precision floating point operations (`cvtdq2pd`, `mulpd`, `subpd`, `unpckhpd`, `cvttsd2si`).
- **Entrypoint:** `run_fixture_04` (`0x2013a0`)
- **Authoritative Ground Truth:**
  - Return Value: `1947358608` (`0x74125590`)

---

### Fixture 05: `05_control_concurrency`
- **Source File:** `phase3-poc/tests/fixtures/05_control_concurrency.c`
- **Target Subsystems:** Bounded spin-wait loops, atomic fetch-and-add (`xadd`), atomic compare-and-swap (`cmpxchg`), and conditional branch state propagation (`cmovgeq`).
- **Key Functions:**
  - `test_spin_wait_simulation(uint32_t count)`: Loop with volatile condition variable testing branch prediction and loop counters.
  - `test_atomic_operations(void)`: Atomic operations with x86 bus lock prefix (`lock xaddq`, `lock cmpxchgq`), testing atomic memory modification and condition code flag updates (`sete`).
  - `test_error_propagation(int64_t code)`: Complex multi-way loop with `break`, `continue`, and sign-conditional returns (`cmovgeq`).
- **Entrypoint:** `run_fixture_05` (`0x201260`)
- **Authoritative Ground Truth:**
  - Return Value: `18446744073709550734` (`0xfffffffffffffc8e`)

---

## Authoritative Manifest Summary

```json
{
  "test_suite_version": "2.0.0-phase3.1-authoritative",
  "compiler": "LLVM Clang 23.1.4 (x86_64-unknown-linux-gnu)",
  "reference_runtime": "Unicorn Engine 2.1.4 (x86-64)",
  "fixtures": [
    {
      "id": "01_arithmetic",
      "entrypoint": "0x2013d0",
      "expected_return_hex": "0xc7c63fc50b2aeb68",
      "expected_return_uint64": 14395263374464838504
    },
    {
      "id": "02_dispatch",
      "entrypoint": "0x2012a0",
      "expected_return_hex": "0x1b35",
      "expected_return_uint64": 6965
    },
    {
      "id": "03_memory_reloc",
      "entrypoint": "0x201340",
      "expected_return_hex": "0x29f9f9e047",
      "expected_return_uint64": 180287561799
    },
    {
      "id": "04_vector_simd",
      "entrypoint": "0x2013a0",
      "expected_return_hex": "0x74125590",
      "expected_return_uint64": 1947358608
    },
    {
      "id": "05_control_concurrency",
      "entrypoint": "0x201260",
      "expected_return_hex": "0xfffffffffffffc8e",
      "expected_return_uint64": 18446744073709550734
    }
  ]
}
```
