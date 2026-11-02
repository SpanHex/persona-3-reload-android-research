#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
P3R Ahead-of-Time (AOT) Recompiler Driver
Connects:
1. Function Discovery (discover.py)
2. Instruction Lifter (lower.py)
3. Target Code Generator (codegen.py)
Emits:
- AArch64 ELF object file (.o)
- AArch64 GNU Assembly (.s)
- C Runtime Dispatch Table (.c)
- Compilation Performance & Metadata JSON (.json)
"""

import os
import sys
import time
import json
import argparse
import capstone
import llvmlite.ir as ir

from abi import BBR_ABI_VERSION, GuestState
from discover import DiscoveryEngine
from lower import FunctionLifter
from codegen import CodeGenerator

def main():
    parser = argparse.ArgumentParser(description="P3R AOT Recompiler Driver")
    parser.add_argument("--input", required=True, help="Path to input x86-64 binary")
    parser.add_argument("--base-vaddr", default="0x401000", help="Base virtual address (hex)")
    parser.add_argument("--entry", default="0x401000", help="Entrypoint virtual address (hex)")
    parser.add_argument("--extra-entries", default=None, help="Path to extra entries file")
    parser.add_argument("--out-asm", default=None, help="Path to output AArch64 assembly (.s)")
    parser.add_argument("--out-obj", default=None, help="Path to output AArch64 ELF object (.o)")
    parser.add_argument("--out-c", default=None, help="Path to output C dispatch table (.c)")
    parser.add_argument("--stats", default=None, help="Path to output compilation stats JSON")
    parser.add_argument("--opt", type=int, default=2, help="Optimization level (0-3)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose debug logs")

    args = parser.parse_args()

    start_time = time.perf_counter()
    base_vaddr = int(args.base_vaddr, 16)
    entry_vaddr = int(args.entry, 16)

    if not os.path.exists(args.input):
        print(f"[-] Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    with open(args.input, "rb") as f:
        code_bytes = f.read()

    print(f"[*] Loaded input: {args.input} ({len(code_bytes)} bytes, base: {hex(base_vaddr)})")

    # 1. Discovery Phase
    discovery = DiscoveryEngine()
    if args.extra_entries and os.path.exists(args.extra_entries):
        discovery.load_extra_entries_file(args.extra_entries)
        print(f"[*] Loaded {len(discovery.extra_entries)} extra entrypoints from {args.extra_entries}")

    disc_start = time.perf_counter()
    functions = discovery.discover_from_code(code_bytes, base_vaddr, [entry_vaddr])
    disc_time = time.perf_counter() - disc_start
    print(f"[+] Discovery completed in {disc_time*1000:.2f} ms: found {len(functions)} functions")

    # 2. Lowering Phase
    lower_start = time.perf_counter()
    ir_module = ir.Module(name=os.path.basename(args.input))
    ir_module.triple = "aarch64-unknown-linux-android30"

    cs_md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    cs_md.detail = True

    total_insns = 0
    discovered_addrs = sorted(list(functions.keys()))

    for fn_addr in discovered_addrs:
        fn_meta = functions[fn_addr]
        fn_offset = fn_addr - base_vaddr
        fn_len = fn_meta.end - fn_addr if fn_meta.end > fn_addr else len(code_bytes) - fn_offset
        fn_bytes = code_bytes[fn_offset:fn_offset + fn_len]

        insns = list(cs_md.disasm(fn_bytes, fn_addr))
        total_insns += len(insns)

        lifter = FunctionLifter(ir_module, fn_addr, fn_bytes, cs_md)
        lifter.lift()

    lower_time = time.perf_counter() - lower_start
    print(f"[+] Lowered {len(discovered_addrs)} functions ({total_insns} x86-64 insns) in {lower_time*1000:.2f} ms")

    # 3. Code Generation Phase
    codegen_start = time.perf_counter()
    codegen = CodeGenerator(opt_level=args.opt)
    mod_parsed = codegen.verify_and_parse(ir_module)

    asm_code = None
    obj_bytes = None

    if args.out_asm:
        asm_code = codegen.emit_aarch64_assembly(mod_parsed)
        os.makedirs(os.path.dirname(os.path.abspath(args.out_asm)), exist_ok=True)
        with open(args.out_asm, "w", encoding="utf-8") as f:
            f.write(asm_code)
        print(f"[+] Emitted AArch64 assembly: {args.out_asm} ({len(asm_code)} chars)")

    if args.out_obj:
        obj_bytes = codegen.emit_aarch64_object(mod_parsed)
        os.makedirs(os.path.dirname(os.path.abspath(args.out_obj)), exist_ok=True)
        with open(args.out_obj, "wb") as f:
            f.write(obj_bytes)
        print(f"[+] Emitted AArch64 ELF object: {args.out_obj} ({len(obj_bytes)} bytes)")

    if args.out_c:
        c_code = codegen.generate_dispatch_table_c(discovered_addrs)
        os.makedirs(os.path.dirname(os.path.abspath(args.out_c)), exist_ok=True)
        with open(args.out_c, "w", encoding="utf-8") as f:
            f.write(c_code)
        print(f"[+] Emitted C dispatch table: {args.out_c}")

    codegen_time = time.perf_counter() - codegen_start
    total_time = time.perf_counter() - start_time

    # 4. Statistics Output
    stats = {
        "compiler_version": "1.0.0-phase3-poc",
        "abi_version": BBR_ABI_VERSION,
        "input_binary": args.input,
        "input_size_bytes": len(code_bytes),
        "discovered_functions": len(discovered_addrs),
        "total_x86_instructions": total_insns,
        "discovery_time_ms": round(disc_time * 1000, 3),
        "lowering_time_ms": round(lower_time * 1000, 3),
        "codegen_time_ms": round(codegen_time * 1000, 3),
        "total_time_ms": round(total_time * 1000, 3),
        "throughput_insns_per_sec": round(total_insns / max(total_time, 0.0001), 2),
        "output_elf_size_bytes": len(obj_bytes) if obj_bytes else 0,
        "target_triple": "aarch64-unknown-linux-android30",
        "target_cpu": codegen.target_cpu,
        "target_features": codegen.features,
    }

    if args.stats:
        os.makedirs(os.path.dirname(os.path.abspath(args.stats)), exist_ok=True)
        with open(args.stats, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
        print(f"[+] Wrote compilation statistics: {args.stats}")

    print(f"[*] Recompilation finished in {total_time*1000:.2f} ms ({stats['throughput_insns_per_sec']} insns/sec)")

if __name__ == "__main__":
    main()
