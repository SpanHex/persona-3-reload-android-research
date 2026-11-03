# SPDX-License-Identifier: MIT
"""
Build script for P3R Native Harness using Android NDK r26c and CMake 3.22.1.
Compiles libp3r_native_harness.so targeting arm64-v8a and places it in jniLibs.
"""

import os
import subprocess
import sys
import shutil

SDK_ROOT = r"C:\Users\SPANDAN UPAMANYU\AppData\Local\Android\Sdk"
CMAKE_BIN = os.path.join(SDK_ROOT, "cmake", "3.22.1", "bin", "cmake.exe")
NINJA_BIN = os.path.join(SDK_ROOT, "cmake", "3.22.1", "bin", "ninja.exe")
NDK_ROOT = os.path.join(SDK_ROOT, "ndk", "26.3.11579264")
TOOLCHAIN_FILE = os.path.join(NDK_ROOT, "build", "cmake", "android.toolchain.cmake")

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
CPP_DIR = os.path.join(APP_DIR, "app", "src", "main", "cpp")
BUILD_DIR = os.path.join(APP_DIR, "app", "build", "cmake-arm64-v8a")
JNILIBS_DIR = os.path.join(APP_DIR, "app", "src", "main", "jniLibs", "arm64-v8a")

def main():
    print(f"[+] Configuring CMake for arm64-v8a with NDK r26c...")
    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(JNILIBS_DIR, exist_ok=True)

    cmake_args = [
        CMAKE_BIN,
        "-G", "Ninja",
        f"-DCMAKE_MAKE_PROGRAM={NINJA_BIN}",
        f"-DCMAKE_TOOLCHAIN_FILE={TOOLCHAIN_FILE}",
        "-DANDROID_ABI=arm64-v8a",
        "-DANDROID_PLATFORM=android-30",
        "-DCMAKE_BUILD_TYPE=Release",
        "-B", BUILD_DIR,
        "-S", CPP_DIR
    ]

    print("Running:", " ".join(cmake_args))
    res = subprocess.run(cmake_args, capture_output=True, text=True)
    print("CMake Output:\n", res.stdout)
    if res.stderr:
        print("CMake Errors:\n", res.stderr)
    if res.returncode != 0:
        print(f"[-] CMake configuration failed with code {res.returncode}")
        sys.exit(res.returncode)

    print(f"[+] Building p3r_native_harness...")
    build_args = [
        CMAKE_BIN,
        "--build", BUILD_DIR
    ]
    res_b = subprocess.run(build_args, capture_output=True, text=True)
    print("Build Output:\n", res_b.stdout)
    if res_b.stderr:
        print("Build Errors:\n", res_b.stderr)
    if res_b.returncode != 0:
        print(f"[-] Build failed with code {res_b.returncode}")
        sys.exit(res_b.returncode)

    built_so = os.path.join(BUILD_DIR, "libp3r_native_harness.so")
    target_so = os.path.join(JNILIBS_DIR, "libp3r_native_harness.so")
    if os.path.exists(built_so):
        shutil.copy2(built_so, target_so)
        print(f"[+] Successfully copied {built_so} -> {target_so}")
        print(f"    Size: {os.path.getsize(target_so)} bytes")
    else:
        print(f"[-] Built SO not found at {built_so}")
        sys.exit(1)

if __name__ == "__main__":
    main()
