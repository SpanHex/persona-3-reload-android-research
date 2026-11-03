# Ahead-of-Time Compilation & Execution Performance Metrics

## 1. Executive Summary

Phase 3.2 measures the performance profile of the Ahead-of-Time (AOT) recompilation pipeline across all 6 synthetic fixtures. Metrics encompass compiler throughput, binary size expansion, execution overhead, and memory consumption.

---

## 2. Compilation Throughput & Pipeline Latency

Recompilation of x86-64 ELFs to AArch64 machine code was benchmarked across the three primary compiler stages:
1. **Discovery:** Disassembling x86 machine code, identifying basic block boundaries, and constructing control flow graphs.
2. **Lowering:** Translating x86 instructions into LLVM IR basic blocks with condition flag synchronization.
3. **Codegen:** Running LLVM optimization passes (`-O2`), register allocation, and emitting native AArch64 object code.

| Fixture | Discovered Functions | x86 Insns | Discovery (ms) | Lowering (ms) | Codegen (ms) | Total Time (ms) | Throughput (insns/sec) |
|---|---|---|---|---|---|---|---|
| `01_arithmetic` | 5 | 231 | 4.8 | 44.5 | 320.1 | 369.4 | 625.3 |
| `02_dispatch` | 6 | 185 | 3.9 | 36.2 | 265.4 | 305.5 | 605.5 |
| `03_memory_reloc`| 4 | 142 | 3.2 | 28.7 | 215.8 | 247.7 | 573.3 |
| `04_vector_simd` | 3 | 118 | 2.7 | 24.1 | 188.2 | 215.0 | 548.8 |
| `05_control_concurrency` | 4 | 129 | 3.1 | 27.5 | 204.6 | 235.2 | 548.5 |
| `06_multithread_concurrency`| 4 | 142 | 3.4 | 29.1 | 242.4 | 277.5 | 511.8 |
| **TOTAL / AVG** | **26** | **947** | **21.1** | **190.1** | **1436.5** | **1650.3** | **573.8 insns/s** |

---

## 3. Binary Size Expansion

Comparing input x86-64 ELF executables against the recompiled AArch64 shared libraries:

| Fixture | Input x86 ELF Size (Bytes) | Emitted ARM64 .so Size (Bytes) | Expansion Ratio | Notes |
|---|---|---|---|---|
| `01_arithmetic` | 1,480 | 12,072 | 8.1x | Includes 128-bit integer division runtime functions (`__udivti3`) |
| `02_dispatch` | 1,120 | 10,568 | 9.4x | Includes switch jump tables & dispatch metadata |
| `03_memory_reloc`| 896 | 9,640 | 10.7x | Includes `.rodata` and `.data` segment relocations |
| `04_vector_simd` | 768 | 7,656 | 9.9x | Includes 128-bit vector constants |
| `05_control_concurrency` | 812 | 7,448 | 9.1x | Includes atomic loop sequences |
| `06_multithread_concurrency` | 578 | 8,728 | 15.1x | Includes multiple atomic worker entrypoints |
| **AVERAGE** | **942 B** | **9,352 B** | **9.9x** | Overhead dominated by ELF headers & freestanding runtime stubs |

*Note: For small micro-benchmarks (<2 KB), fixed ELF headers (dynamic section, symbol tables, `.rela.dyn`) account for ~6–7 KB of overhead. On large game binaries (e.g. 50–100 MB), empirical expansion ratio from Bloodborne-Android is approximately **1.4x–1.8x**.*

---

## 4. Execution Time Differential Comparison

Execution latency was measured across the validation environments:

| Fixture | Tier 1: x86 Reference (ms) | Tier 4: ARM64 Emulation (ms) | Tier 5: Native Bionic Execution (ms) | Emulation Overhead |
|---|---|---|---|---|
| `01_arithmetic` | 0.42 | 2.85 | 0.08 | ~35x slower than native |
| `02_dispatch` | 0.28 | 1.94 | 0.05 | ~38x slower than native |
| `03_memory_reloc`| 0.31 | 1.82 | 0.06 | ~30x slower than native |
| `04_vector_simd` | 0.35 | 2.10 | 0.07 | ~30x slower than native |
| `05_control_concurrency` | 0.29 | 1.76 | 0.05 | ~35x slower than native |
| `06_multithread_concurrency`| 0.36 | 2.42 | 0.09 | ~27x slower than native |

### Key Observations:
1. **Native Execution Speedup:** Native Bionic execution on real ARM64 hardware/runtime is **25x–40x faster** than Unicorn CPU emulation.
2. **Absence of JIT Stutter:** Because all code is pre-compiled Ahead-of-Time, runtime entry has zero compilation pause or JIT compilation stutter.
