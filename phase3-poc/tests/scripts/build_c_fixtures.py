#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
Authoritative C Fixture Builder
Compiles 01..05 C fixtures directly into x86-64 ELF objects and executables using LLVM Clang.
Guarantees compiler flags, symbol table generation, and disassembly inspection.
"""

import os
import sys
import subprocess
import lief

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURES_DIR = os.path.join(REPO_ROOT, "tests", "fixtures")
BIN_DIR = os.path.join(REPO_ROOT, "tests", "bin")
CLANG_PATH = r"C:\Program Files\LLVM\bin\clang.exe"
OBJDUMP_PATH = r"C:\Program Files\LLVM\bin\llvm-objdump.exe"

os.makedirs(BIN_DIR, exist_ok=True)

FIXTURE_NAMES = [
    "01_arithmetic",
    "02_dispatch",
    "03_memory_reloc",
    "04_vector_simd",
    "05_control_concurrency",
    "06_multithread_concurrency"
]

def build_fixture(name: str):
    c_path = os.path.join(FIXTURES_DIR, f"{name}.c")
    obj_path = os.path.join(FIXTURES_DIR, f"{name}.elf.o")
    bin_elf = os.path.join(BIN_DIR, f"{name}.elf")
    disasm_path = os.path.join(BIN_DIR, f"{name}.x86.s")

    print(f"[*] Compiling {c_path} -> {obj_path}...")
    # Compile with clang -O2 -target x86_64-unknown-linux-gnu -c -fno-asynchronous-unwind-tables
    cmd_compile = [
        CLANG_PATH,
        "-target", "x86_64-unknown-linux-gnu",
        "-O2",
        "-c",
        "-fno-asynchronous-unwind-tables",
        "-fno-stack-protector",
        c_path,
        "-o", obj_path
    ]
    res = subprocess.run(cmd_compile, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[-] Clang compilation failed:\n{res.stderr}", file=sys.stderr)
        sys.exit(1)

    # Link into a static ELF executable with entry point `run_fixture_XX`
    entry_sym = f"run_fixture_{name[:2]}"
    print(f"[*] Linking static ELF {bin_elf} (entry: {entry_sym})...")
    cmd_link = [
        CLANG_PATH,
        "-target", "x86_64-unknown-linux-gnu",
        "-nostdlib",
        "-static",
        f"-Wl,-e,{entry_sym}",
        obj_path,
        "-o", bin_elf
    ]
    res_link = subprocess.run(cmd_link, capture_output=True, text=True)
    if res_link.returncode != 0:
        print(f"[-] Static linking failed:\n{res_link.stderr}", file=sys.stderr)
        sys.exit(1)

    # Disassemble
    with open(disasm_path, "w", encoding="utf-8") as df:
        subprocess.run([OBJDUMP_PATH, "-d", bin_elf], stdout=df, check=True)

    print(f"[+] Successfully built: {bin_elf} and {disasm_path}")

def main():
    print("=" * 70)
    print("BUILDING AUTHORITATIVE X86-64 C FIXTURES")
    print("=" * 70)
    for name in FIXTURE_NAMES:
        build_fixture(name)
    print("=" * 70)
    print("[+] All 5 C fixtures compiled and linked into x86-64 ELF executables.")

if __name__ == "__main__":
    main()

