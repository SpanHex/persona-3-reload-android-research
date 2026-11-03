#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
Automated Recompiler & Android Shared Library Linker
Recompiles all 5 synthetic x86-64 C fixture ELFs into AArch64 objects via p3r_recomp.py,
compiles freestanding runtime/dispatch tables, and links with Bionic-compatible AArch64 flags.
"""

import os
import sys
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BIN_DIR = os.path.join(REPO_ROOT, "tests", "bin")
RUNTIME_DIR = os.path.join(REPO_ROOT, "android-runtime")
COMPILER_SCRIPT = os.path.join(REPO_ROOT, "compiler", "p3r_recomp.py")

CLANG_PATH = r"C:\Program Files\LLVM\bin\clang.exe"

FIXTURE_NAMES = [
    "01_arithmetic",
    "02_dispatch",
    "03_memory_reloc",
    "04_vector_simd",
    "05_control_concurrency",
    "06_multithread_concurrency"
]

def recompile_and_link():
    print("=" * 75)
    print("RECOMPILING AND LINKING ALL FIXTURES FOR REAL ARM64 EXECUTION")
    print("=" * 75)

    # 1. Compile freestanding guest_cpu.o runtime
    guest_cpu_c = os.path.join(RUNTIME_DIR, "guest_cpu.c")
    guest_cpu_o = os.path.join(RUNTIME_DIR, "guest_cpu.o")
    print(f"[*] Compiling freestanding runtime: {guest_cpu_c} -> {guest_cpu_o}")
    cmd_runtime = [
        CLANG_PATH,
        "-target", "aarch64-linux-android30",
        "-ffreestanding",
        "-nostdlib",
        "-fPIC",
        "-O2",
        "-c", guest_cpu_c,
        "-o", guest_cpu_o
    ]
    res = subprocess.run(cmd_runtime, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[-] Failed to compile guest_cpu.c:\n{res.stderr}", file=sys.stderr)
        sys.exit(1)

    for name in FIXTURE_NAMES:
        elf_path = os.path.join(BIN_DIR, f"{name}.elf")
        asm_path = os.path.join(BIN_DIR, f"{name}.s")
        obj_path = os.path.join(BIN_DIR, f"{name}.o")
        dispatch_c = os.path.join(BIN_DIR, f"{name}_dispatch.c")
        dispatch_o = os.path.join(BIN_DIR, f"{name}_dispatch.o")
        stats_path = os.path.join(BIN_DIR, f"{name}_stats.json")
        so_path = os.path.join(BIN_DIR, f"libp3r_{name}.so")

        print(f"\n--- [{name}] ---")
        print(f"[*] Translating x86-64 ELF -> AArch64 ({elf_path})...")
        cmd_recomp = [
            sys.executable,
            COMPILER_SCRIPT,
            "--input", elf_path,
            "--out-asm", asm_path,
            "--out-obj", obj_path,
            "--out-c", dispatch_c,
            "--stats", stats_path,
            "--opt", "2"
        ]
        res_recomp = subprocess.run(cmd_recomp, capture_output=True, text=True)
        if res_recomp.returncode != 0:
            print(f"[-] Recompilation failed for {name}:\n{res_recomp.stderr}", file=sys.stderr)
            sys.exit(1)

        print(f"[*] Compiling dispatch table: {dispatch_c}...")
        cmd_disp = [
            CLANG_PATH,
            "-target", "aarch64-linux-android30",
            "-ffreestanding",
            "-nostdlib",
            "-fPIC",
            "-O2",
            "-c", dispatch_c,
            "-o", dispatch_o
        ]
        res_disp = subprocess.run(cmd_disp, capture_output=True, text=True)
        if res_disp.returncode != 0:
            print(f"[-] Failed to compile dispatch table for {name}:\n{res_disp.stderr}", file=sys.stderr)
            sys.exit(1)

        print(f"[*] Linking AArch64 shared library: {so_path}...")
        cmd_link = [
            CLANG_PATH,
            "-target", "aarch64-linux-android30",
            "-nostdlib",
            "-shared",
            "-Wl,-Bsymbolic",
            "-Wl,--gc-sections",
            obj_path,
            dispatch_o,
            guest_cpu_o,
            "-o", so_path
        ]
        res_link = subprocess.run(cmd_link, capture_output=True, text=True)
        if res_link.returncode != 0:
            print(f"[-] Linking failed for {name}:\n{res_link.stderr}", file=sys.stderr)
            sys.exit(1)

        print(f"[+] Successfully generated: {so_path} ({os.path.getsize(so_path)} bytes)")

    print("\n" + "=" * 75)
    print("[+] All 5 test fixtures recompiled and linked into valid Android shared libraries!")
    print("=" * 75)

if __name__ == "__main__":
    recompile_and_link()
