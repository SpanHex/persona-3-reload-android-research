#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
Builds the standalone Android Bionic native test runner: p3r_bionic_runner
Target: aarch64-linux-android30 (/system/bin/linker64)
"""

import os
import sys
import subprocess
import lief

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNTIME_DIR = os.path.join(REPO_ROOT, "android-runtime")
BIN_DIR = os.path.join(REPO_ROOT, "tests", "bin")
STUBS_DIR = os.path.join(BIN_DIR, "bionic_stubs")

CLANG_PATH = r"C:\Program Files\LLVM\bin\clang.exe"

os.makedirs(STUBS_DIR, exist_ok=True)
os.makedirs(BIN_DIR, exist_ok=True)

def build_bionic_stubs():
    stubs_c = os.path.join(STUBS_DIR, "stubs.c")
    libc_so = os.path.join(STUBS_DIR, "libc.so")
    libdl_so = os.path.join(STUBS_DIR, "libdl.so")

    with open(stubs_c, "w") as f:
        f.write("""// Bionic dynamic linking stubs for ld.lld
void dlopen(void) {}
void dlsym(void) {}
void dlclose(void) {}
void dlerror(void) {}
void mmap(void) {}
void munmap(void) {}
void mprotect(void) {}
void pthread_create(void) {}
void pthread_join(void) {}
void write(void) {}
void exit(int code) {}
void _exit(int code) {}
""")

    print("[*] Compiling Bionic libc.so stub...")
    subprocess.run([
        CLANG_PATH,
        "-target", "aarch64-linux-android30",
        "-shared", "-nostdlib",
        "-Wl,-soname,libc.so",
        stubs_c,
        "-o", libc_so
    ], check=True)

    print("[*] Compiling Bionic libdl.so stub...")
    subprocess.run([
        CLANG_PATH,
        "-target", "aarch64-linux-android30",
        "-shared", "-nostdlib",
        "-Wl,-soname,libdl.so",
        stubs_c,
        "-o", libdl_so
    ], check=True)

    return libc_so, libdl_so

def build_bionic_runner():
    print("=" * 75)
    print("BUILDING ANDROID BIONIC NATIVE RUNNER (p3r_bionic_runner)")
    print("=" * 75)

    libc_so, libdl_so = build_bionic_stubs()

    runner_c = os.path.join(RUNTIME_DIR, "bionic_runner.c")
    runner_bin = os.path.join(BIN_DIR, "p3r_bionic_runner")

    print(f"[*] Compiling {runner_c} -> {runner_bin}...")
    cmd = [
        CLANG_PATH,
        "-target", "aarch64-linux-android30",
        "-I", RUNTIME_DIR,
        "-ffreestanding",
        "-fPIE", "-pie",
        "-O2",
        "-nostdlib",
        "-Wl,-dynamic-linker,/system/bin/linker64",
        "-Wl,-rpath,/data/local/tmp",
        "-Wl,-rpath,.",
        "-Wl,-z,now",
        "-Wl,-z,relro",
        runner_c,
        libc_so,
        libdl_so,
        "-o", runner_bin
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[-] Compilation failed:\n{res.stderr}", file=sys.stderr)
        sys.exit(1)

    print(f"[+] Successfully built: {runner_bin} ({os.path.getsize(runner_bin)} bytes)")

    # Verify binary with LIEF
    elf = lief.parse(runner_bin)
    print("\n--- Binary Inspection ---")
    print(f"Architecture:      {elf.header.arm64_mode if hasattr(elf.header, 'arm64_mode') else 'AArch64'}")
    print(f"ELF Class:         {elf.header.identity_class}")
    print(f"ELF Type:          {elf.header.file_type}")
    print(f"Dynamic Linker:    {elf.interpreter}")
    print(f"Needed Libraries:  {[lib for lib in elf.libraries]}")
    print(f"Entrypoint:        {hex(elf.entrypoint)}")
    print("-------------------------\n")

    assert elf.interpreter == "/system/bin/linker64", "Interpreter must be Android Bionic linker64"
    assert "libc.so" in elf.libraries, "Must depend on libc.so"
    assert "libdl.so" in elf.libraries, "Must depend on libdl.so"
    print("[+] All Android Bionic binary requirements verified!")
    print("=" * 75)

if __name__ == "__main__":
    build_bionic_runner()
