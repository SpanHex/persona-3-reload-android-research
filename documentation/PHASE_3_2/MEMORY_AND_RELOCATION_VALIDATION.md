# Memory Translation, ASLR & Relocation Validation Report

## 1. Executive Summary

In x86-64 execution, applications assume access to a 48-bit canonical virtual address space, frequently employing RIP-relative addressing for global variables, jump tables, and `.rodata`. When adapting this code to run natively under Android 64-bit userspace, the guest virtual address space must be mapped into the host process's virtual memory space without collisions with Android Bionic, ART, or other shared libraries.

Phase 3.2 validates the **guest-to-host memory translation model**, testing position-independent execution, dynamic ASLR base relocation, and ELF relocation handling across all recompiled shared libraries.

---

## 2. Address Translation Architecture

The runtime implements a base-register translation model matching Recomp ABI v2:
$$\text{Host Virtual Address} = \text{GuestState.mem\_base} + \text{Guest Virtual Address}$$

```
+------------------------------------------------------------------+
| x86-64 Guest Space: 0x0000000000201000 (VAddr in ELF)            |
+------------------------------------------------------------------+
                               |
                        [ + mem_base ] (Loaded from GuestState offset 696)
                               v
+------------------------------------------------------------------+
| Android Host Space: 0x00000078a4b21000 (mmap'd arena address)    |
+------------------------------------------------------------------+
```

### Compiler Lowering Implementation (`phase3-poc/compiler/lower.py`):
For any memory operand targeting guest space, the compiler emits:
```llvm
%mem_base_ptr = getelementptr inbounds i8, i8* %state, i64 696
%mem_base = load i64, i64* %mem_base_ptr
%host_addr_i64 = add i64 %mem_base, %guest_vaddr
%host_ptr = inttoptr i64 %host_addr_i64 to <type>*
```
On AArch64, this lowers efficiently to a single base-offset addressing instruction:
```assembly
ldr x10, [x0, #696]       // Load mem_base
ldr x8, [x10, x9]         // Load from [mem_base + vaddr]
```

---

## 3. Dynamic ASLR Base Relocation Validation

To prove that the compiled binaries do not rely on hardcoded host pointers, the test harness validates execution across four distinct `mem_base` configurations:

| Test Case | `mem_base` Value | Description | Execution Result |
|---|---|---|---|
| **Case 1: Flat Mapping** | `0x0000000000000000` | 1:1 mapping (used in low-memory testbeds) | **PASS (Match)** |
| **Case 2: Low Arena** | `0x0000000010000000` | Fixed 256 MB base offset | **PASS (Match)** |
| **Case 3: High Arena** | `0x0000000040000000` | Fixed 1 GB base offset | **PASS (Match)** |
| **Case 4: Dynamic ASLR**| `0x00000078a4b00000` | Random address assigned by Android kernel `mmap()` | **PASS (Match)** |

In all four cases, pointer arithmetic, global array lookups, and nested struct member accesses yielded identical results (`0x29f9f9e047` in fixture `03_memory_reloc`).

---

## 4. Dynamic Relocations Analysis

Inspection of the generated `.so` files using LIEF reveals two primary categories of relocations:

```
Relocations (.rela.dyn):
  Offset       Type               Symbol               Addend
  0x00003df0   R_AARCH64_RELATIVE                      +0x1b30
  0x00003df8   R_AARCH64_RELATIVE                      +0x1b70
  0x00003e00   R_AARCH64_RELATIVE                      +0x1bc0
  0x00003e08   R_AARCH64_RELATIVE                      +0x1c00
```

1. **`R_AARCH64_RELATIVE` (Internal Dispatch Tables):**
   - The dispatch tables (`g_bbr_units`) contain absolute addresses of recompiled function entrypoints.
   - The Bionic linker automatically relocates these entries by adding the randomized library load base upon `dlopen()`.
   - Verified that `bbr_lookup(vaddr)` resolves correctly regardless of where Bionic loads the `.so`.
2. **Global Offset Table (`.got`) Integrity:**
   - No external variable relocations remain unresolved.
   - Text segments contain **zero text relocations**, ensuring full compatibility with Android's security enforcement (`SELinux` / `no-exec-with-write`).

---

## 5. Stack Alignment & Relocation Safety

System V AMD64 ABI requires the stack pointer (`RSP`) to be 16-byte aligned before any `call` instruction:
$$(\text{RSP} - 8) \pmod{16} == 0$$

The runtime initializes the guest stack using:
```c
uintptr_t sp = (uintptr_t)stack_base + stack_size - 32;
sp &= ~0xFULL; // Enforce strict 16-byte alignment
state->gregs[GUEST_RSP] = (uint64_t)sp;
state->gregs[GUEST_RBP] = (uint64_t)sp;
```
Validation confirms that SSE/NEON 128-bit aligned vector moves (`movaps`, `movdqa`) operate without memory alignment faults across all test fixtures.
