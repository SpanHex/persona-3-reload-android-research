#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
Builds the standalone Android Bionic native test runner: p3r_bionic_runner
Target: aarch64-linux-android30 (/system/bin/linker64)
Uses the official Android NDK toolchain & legitimate Bionic sysroot.
"""

import os
import sys
import subprocess
import lief

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNTIME_DIR = os.path.join(REPO_ROOT, "android-runtime")
BIN_DIR = os.path.join(REPO_ROOT, "tests", "bin")

# Locate official Android NDK
DEFAULT_NDK_ROOT = os.path.expanduser(r"~\AppData\Local\Android\Sdk\ndk\26.3.11579264")
NDK_ROOT = os.environ.get("ANDROID_NDK_HOME", os.environ.get("ANDROID_NDK_ROOT", DEFAULT_NDK_ROOT))

def find_ndk_clang():
    if not os.path.exists(NDK_ROOT):
        print(f"[-] ERROR: Android NDK not found at {NDK_ROOT}", file=sys.stderr)
        print("    Please set ANDROID_NDK_ROOT to your Android NDK installation.", file=sys.stderr)
        sys.exit(1)

    ndk_bin_dir = os.path.join(NDK_ROOT, "toolchains", "llvm", "prebuilt", "windows-x86_64", "bin")
    clang_cmd = os.path.join(ndk_bin_dir, "aarch64-linux-android30-clang.cmd")

    if not os.path.exists(clang_cmd):
        print(f"[-] ERROR: aarch64-linux-android30-clang.cmd not found in {ndk_bin_dir}", file=sys.stderr)
        sys.exit(1)

    return clang_cmd

def build_bionic_runner():
    print("=" * 75)
    print("BUILDING ANDROID BIONIC NATIVE RUNNER (p3r_bionic_runner)")
    print(f"[*] Android NDK: {NDK_ROOT}")
    print("=" * 75)

    clang_cmd = find_ndk_clang()

    runner_c = os.path.join(RUNTIME_DIR, "bionic_runner.c")
    runner_bin = os.path.join(BIN_DIR, "p3r_bionic_runner")

    print(f"[*] Compiling {runner_c} -> {runner_bin} using official Android NDK...")
    cmd = [
        clang_cmd,
        "-O2",
        "-I", RUNTIME_DIR,
        runner_c,
        "-o", runner_bin
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[-] NDK compilation failed:\n{res.stderr}", file=sys.stderr)
        sys.exit(1)

    print(f"[+] Successfully built: {runner_bin} ({os.path.getsize(runner_bin)} bytes)")

    # Verify binary with LIEF
    elf = lief.parse(runner_bin)
    print("\n--- Official NDK Binary Inspection ---")
    print(f"Architecture:      {elf.header.machine_type}")
    print(f"ELF Class:         {elf.header.identity_class}")
    print(f"ELF Type:          {elf.header.file_type}")
    print(f"Dynamic Linker:    {elf.interpreter}")
    print(f"Needed Libraries:  {[lib for lib in elf.libraries]}")
    print(f"Dynamic Relocs:    {len(elf.dynamic_relocations)}")
    print(f"Dynamic Symbols:   {len(elf.dynamic_symbols)}")
    print("--------------------------------------\n")

    assert elf.interpreter == "/system/bin/linker64", "Interpreter must be Android Bionic linker64"
    assert "libc.so" in elf.libraries, "Must depend on real Bionic libc.so"
    assert "libdl.so" in elf.libraries, "Must depend on real Bionic libdl.so"
    print("[+] All legitimate Android Bionic binary requirements verified via official NDK!")
    print("=" * 75)

if __name__ == "__main__":
    build_bionic_runner()
