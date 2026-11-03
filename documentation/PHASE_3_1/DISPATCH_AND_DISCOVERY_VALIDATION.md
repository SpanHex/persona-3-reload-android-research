# Phase 3.1: Dispatch & Discovery Architecture Validation

## Executive Summary

A critical architectural challenge in ahead-of-time (AOT) binary recompilation is handling indirect control flow: function pointers, dynamic polymorphism (C++ virtual method tables), and jump table-driven switch statements.

Phase 3.1 verified both the discovery engine (`discover.py`) and the runtime dispatch subsystem (`guest_cpu.c`, `codegen.py`, `lower.py`). This document details:
1. The binary lookup dispatch table (`g_bbr_units[]` and `bbr_lookup`).
2. Resolution of direct calls vs indirect calls.
3. Virtual method table (vtable) simulation and execution.
4. Intra-function jump table switch handling.
5. Verification of the intentional miss trap (`BBR_TRAP_MISS`).

---

## The Global Dispatch Table Architecture

### Data Structures & Lookup Complexity
Every recompiled function is exported as a standalone C function:
```c
void bbr_<vaddr>(GuestState* state);
```

To enable dynamic indirect branch resolution, the compiler emits a sorted dispatch array and lookup function in `<fixture>_dispatch.c`:

```c
typedef struct RecompUnit {
    uint64_t vaddr;
    bbr_func_t func;
} RecompUnit;

const size_t g_bbr_unit_count = 12;
const RecompUnit g_bbr_units[] = {
    { 0x2011b0ULL, bbr_2011b0 },
    { 0x2011b8ULL, bbr_2011b8 },
    { 0x2011c0ULL, bbr_2011c0 },
    { 0x2011c8ULL, bbr_2011c8 },
    { 0x2011d0ULL, bbr_2011d0 },
    { 0x2011e0ULL, bbr_2011e0 },
    { 0x201240ULL, bbr_201240 },
    { 0x2012a0ULL, bbr_2012a0 },
    { 0x201410ULL, bbr_201410 },
    { 0x201418ULL, bbr_201418 },
    { 0x201420ULL, bbr_201420 },
    { 0x201430ULL, bbr_201430 },
};

bbr_func_t bbr_lookup(uint64_t vaddr) {
    int low = 0;
    int high = (int)g_bbr_unit_count - 1;
    while (low <= high) {
        int mid = low + (high - low) / 2;
        if (g_bbr_units[mid].vaddr == vaddr) return g_bbr_units[mid].func;
        if (g_bbr_units[mid].vaddr < vaddr) low = mid + 1;
        else high = mid - 1;
    }
    return NULL;
}
```

- **Lookup Complexity:** $O(\log_2 N)$ via binary search.
- **Cache Efficiency:** The dispatch table is compact ($16\text{ bytes}$ per entry), contiguous, and stored in read-only memory (`.rodata`).
- **Scalability:** For a full commercial title with $\approx 100,000$ functions, binary search resolves any function in $\le 17$ branch comparisons.

---

## Control Flow Dispatch Categories

### 1. Direct Calls
When an x86-64 instruction calls an immediate address (`callq 0x2011d0`), `lower.py` identifies the target at compile time. It generates a direct call in LLVM IR:
```llvm
call void @bbr_2011d0(i8* %state)
```
- **Overhead:** Zero table lookup overhead. Clang and `ld.lld` emit direct AArch64 `bl` (branch with link) instructions.

### 2. Indirect Calls (Function Pointers & Tail Calls)
When code invokes a function pointer (e.g. `jmpq *%rax` or `callq *%rax`), the target virtual address is only known at runtime:
```python
target_vaddr_val = self._load_operand(builder, insn, ops[0])
builder.call(self.dispatch_fn, [self.state_arg, target_vaddr_val])
```
In `guest_cpu.c`:
```c
void bbr_dispatch(GuestState* state, uint64_t target_vaddr) {
    if (!state) return;
    state->rip = target_vaddr;

    bbr_func_t target_func = bbr_lookup(target_vaddr);
    if (target_func) {
        target_func(state);
    } else {
        bbr_trap(state, BBR_TRAP_MISS);
    }
}
```
- **Stack Protocol:** Tail-calls (`jmpq *%reg`) reuse the caller's stack frame. When the callee executes `retq`, it adjusts `RSP` and returns through the host call stack back to the original caller.

### 3. Polymorphic C++ Virtual Method Tables (VTables)
Fixture `02_dispatch` implements two polymorphic classes (`ObjectA`, `ObjectB`) deriving from a common `VTable`:
```c
typedef struct VTable {
    uint64_t (*op1)(void* self, uint64_t v);
    uint64_t (*op2)(void* self, uint64_t v);
} VTable;
```
- In x86 assembly, this lowers to `callq *0x0(%rax)` and `callq *0x8(%rax)`.
- During execution, the pointers in `vtable_A` (`objA_op1 = 0x201410`, `objA_op2 = 0x201418`) and `vtable_B` (`objB_op1 = 0x201420`, `objB_op2 = 0x201430`) are looked up and executed, producing bit-exact virtual dispatch.

### 4. Dense Jump Tables (Switch Statements)
Dense switch statements (such as `test_switch_jumptable`) index a table of relative basic block offsets in `.rodata`:
```assembly
leaq   -0x10c1(%rip), %rdx       # 0x200190 (.rodata jump table)
movslq (%rdx, %rcx, 4), %rcx     # 32-bit signed offset
addq   %rdx, %rcx                # Absolute target basic block address
jmpq   *%rcx                     # Intra-function jump
```
- **The Problem:** The targets (`0x20125a`, `0x20125f`, `0x201264`, etc.) are internal basic blocks, not registered function entries in `g_bbr_units[]`. Routing this through `bbr_dispatch` caused miss traps.
- **The Solution:** In `lower.py`, indirect jumps emit an LLVM `switch` instruction covering all basic blocks in the function:
  ```python
  default_bb = self.fn.append_basic_block(name=f"disp_fallback_{hex(insn.address)[2:]}")
  sw = builder.switch(target_vaddr_val, default_bb)
  for b_addr, b_block in block_map.items():
      sw.add_case(ir.Constant(self.i64, b_addr), b_block)
  builder.position_at_end(default_bb)
  builder.call(self.dispatch_fn, [self.state_arg, target_vaddr_val])
  builder.ret_void()
  ```
- **Result:** LLVM lowers the `switch` into an optimized AArch64 jump table or binary search tree. Internal jumps resolve locally without runtime table lookup. Unmatched addresses (genuine external tail-calls) fall through to `bbr_dispatch`.

---

## Intentional Miss Trap Validation (`BBR_TRAP_MISS`)

A robust recompiler must fail safely when encountering unlifted, unmapped, or corrupted function addresses.

### Trap Mechanism
In `guest_cpu.h`:
```c
#define BBR_TRAP_MISS (1ULL << 61) // 0x2000000000000000 (2305843009213693952)
```
When `bbr_lookup(target_vaddr)` returns `NULL`:
```c
void bbr_trap(GuestState* state, uint64_t trap_code) {
    if (!state) return;
    state->trap_code = trap_code;
    state->exit_code = 1;
}
```

### Verification Test
To verify this behavior, an intentional miss was tested:
1. Target virtual address `0xDEADBEEF` was dispatched via `bbr_dispatch(&state, 0xDEADBEEF)`.
2. Binary search confirmed `0xDEADBEEF` does not exist in `g_bbr_units`.
3. `bbr_lookup` returned `NULL`.
4. `bbr_trap` set:
   - `state.trap_code = 0x2000000000000000` (`BBR_TRAP_MISS`)
   - `state.exit_code = 1`
5. The execution terminated cleanly without memory corruption or segmentation faults.

This confirms that the dispatch subsystem provides safe error containment for unanticipated dynamic branches.

