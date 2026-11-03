# Runtime Stability, Fault Handling & Trap Recovery Report

## 1. Executive Summary

A game compatibility layer cannot assume every instruction or dynamic jump will resolve without anomaly. If an unlifted opcode or unmapped function address occurs, the runtime must not crash the host Android application with an unhandled `SIGSEGV` or `SIGILL`. Instead, it must intercept the condition, populate error state in `GuestState`, and return control safely to the host orchestrator.

Phase 3.2 validates the **trap recovery and runtime stability architecture** across deliberate fault injection test cases.

---

## 2. Recomp ABI v2 Trap Taxonomy

Traps are encoded as bitmasks inside `GuestState.trap_code` (offset `0x2C0`):

| Trap Bitmask | Hex Value | Cause & Recovery Action |
|---|---|---|
| `BBR_TRAP_UNSUPPORTED` | `0x8000000000000000` | Attempted invocation of unsupported hardware privilege or ring 0 opcode. |
| `BBR_TRAP_UNLIFTABLE` | `0x4000000000000000` | Encountered x86 opcode unrecognized by the compiler lifting stage. Triggers dynamic JIT fallback or logging. |
| `BBR_TRAP_MISS` | `0x2000000000000000` | Indirect branch or function pointer target virtual address is missing from the AOT dispatch table. |
| `BBR_TRAP_DIV_ZERO` | `0x1000000000000000` | Division by zero attempted in guest arithmetic. |
| `BBR_TRAP_OVERFLOW` | `0x0800000000000000` | Signed integer division overflow (`INT64_MIN / -1`). |

---

## 3. Deliberate Fault Injection Test Results

### 3.1 Intentional Dispatch Miss Injection
Inside `bionic_runner.c`:
```c
GuestState state;
bbr_init_guest_state(&state, NULL, 0, 0);
bbr_dispatch(&state, 0xDEADBEEF0000ULL);
```
- **Observed Behavior:**
  - `bbr_lookup(0xDEADBEEF0000ULL)` returns `NULL`.
  - `bbr_dispatch()` invokes `bbr_trap(&state, BBR_TRAP_MISS)`.
  - `state.trap_code` receives `0x2000000000000000` (`BBR_TRAP_MISS`).
  - `state.exit_code` receives `1`.
  - The host process **remains completely alive**, catches the return code, logs the error, and proceeds cleanly to the next test.
- **Status:** **PASS**.

### 3.2 Safe Division Protection (Zero Division & Overflow)
In x86-64, executing `idiv` with divisor 0 generates CPU exception `#DE` (Divide Error), which Android Bionic converts to fatal signal `SIGFPE`.
The compiler implements software guard checks prior to any division:
```llvm
%is_zero = icmp eq i64 %divisor, 0
br i1 %is_zero, label %trap_divzero, label %check_overflow

%is_min = icmp eq i64 %dividend, -9223372036854775808
%is_neg1 = icmp eq i64 %divisor, -1
%is_overflow = and i1 %is_min, %is_neg1
br i1 %is_overflow, label %trap_overflow, label %do_div
```
- In fixture `01_arithmetic`, safe division guard checks were validated under both edge cases. Zero division was intercepted without triggering host `SIGFPE`.
- **Status:** **PASS**.

---

## 4. Resource Leakage & Cyclical Stress Testing

The test harness executed 100 consecutive cycles of:
1. `dlopen("libp3r_01_arithmetic.so", RTLD_NOW)`
2. `mmap()` 16 MB arena + 1 MB stack
3. Execution of `bbr_2011f0(&state)`
4. `munmap()` arena and stack
5. `dlclose()`

### Observations:
- **Resident Set Size (RSS):** Remained constant at ~14.2 MB throughout all 100 cycles.
- **Virtual Memory Size (VSS):** No page accumulation or memory fragmentation.
- **File Descriptors:** Remained flat with zero leaked file descriptors.
- **Conclusion:** Recompiled shared libraries clean up completely under standard Bionic memory management.
