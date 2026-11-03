# ANDROID APPLICATION BUILD & PACKAGING VALIDATION
**Phase 3.2.1 — Evidence-Based Android Validation & Runtime Corrections**
**Document ID:** `P3R-DOC-321-APK`
**Date:** 2026-11-04
**Status:** COMPLETE & VERIFIED

---

## 1. Executive Summary

Milestone 4 requires building the native Android application and packaging the AArch64 JNI harness along with all generated AOT shared libraries into a real, deployable Android Package (`app-debug.apk`) using the official Android toolchain:
- Android Gradle Plugin (AGP) `8.2.2`
- Gradle `8.5`
- Microsoft OpenJDK `17.0.21` (LTS)
- Android NDK `26.3.11579264` (r26c LTS)
- CMake `3.22.1`
- Android SDK Platform `android-34` / Build-Tools `34.0.0`
- Target ABI: `arm64-v8a`

The build was successfully completed from clean sources without artificial stubs or mock environments.

---

## 2. Toolchain & Environment Specifications

The build environment was verified and recorded with exact versions:

| Component | Version | Installation / Configuration Path |
| :--- | :--- | :--- |
| **Gradle** | `8.5` | `C:\Users\SPANDAN UPAMANYU\AppData\Local\gradle-8.5` |
| **Android Gradle Plugin** | `8.2.2` | `com.android.tools.build:gradle:8.2.2` via Google Maven |
| **Java Development Kit** | `17.0.21.0.2` (64-Bit) | `C:\Program Files\Microsoft\jdk-17.0.21.21-hotspot` |
| **Android NDK** | `26.3.11579264` (r26c) | `C:\Users\SPANDAN UPAMANYU\AppData\Local\Android\Sdk\ndk\26.3.11579264` |
| **CMake** | `3.22.1` | `C:\Users\SPANDAN UPAMANYU\AppData\Local\Android\Sdk\cmake\3.22.1\bin\cmake.exe` |
| **Android SDK Platform** | API Level 34 | `C:\Users\SPANDAN UPAMANYU\AppData\Local\Android\Sdk\platforms\android-34` |
| **Build Tools** | `34.0.0` | `C:\Users\SPANDAN UPAMANYU\AppData\Local\Android\Sdk\build-tools\34.0.0` |
| **Minimum SDK** | API Level 28 (Android 9 Pie)| Configured in `app/build.gradle` |
| **Target SDK** | API Level 34 (Android 14) | Configured in `app/build.gradle` |
| **Target ABI** | `arm64-v8a` | Exclusive ABI filter (no 32-bit x86/ARM bloat) |

---

## 3. Defect Remediation During Build

During initial invocation of `gradle assembleDebug`, two concrete configuration defects were identified and rectified:

### 3.1 NDK Version Inconsistency (`[CXX1104]`)
- **Diagnosis:** AGP 8.2.2 defaulted to `android.ndkVersion [25.1.8937393]`, disagreeing with the installed NDK r26c (`26.3.11579264`) pointed to by `ndk.dir`.
- **Correction:** Explicitly configured `ndkVersion "26.3.11579264"` in `app/build.gradle` and removed deprecated `ndk.dir` from `local.properties`.

### 3.2 AndroidX Support Property
- **Diagnosis:** Gradle task `:app:checkDebugAarMetadata` failed because dependencies (`androidx.appcompat`, `com.google.android.material`) require AndroidX namespace mapping.
- **Correction:** Created `gradle.properties` in the project root with `android.useAndroidX=true` and memory tuning parameters (`org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8`).

---

## 4. Built Artifact Verification

The build succeeded with exit code 0 (`BUILD SUCCESSFUL in 1m 16s`).

### 4.1 Artifact Metadata
- **APK Path:** `phase3-poc/android-app/app/build/outputs/apk/debug/app-debug.apk`
- **File Size:** `11,775,360 bytes` (11.23 MB)
- **SHA-256 Checksum:** `6f876fe4f146535d6af88d838ccc8ad8bf3347c379f54db0fbc963ccc3d57e70`
- **Signing Scheme:** Android v1 + v2 Debug Keystore (`androiddebugkey`)

### 4.2 Native Library Packaging Inspection
Unzipping the generated APK confirms the complete set of native ARM64 libraries properly aligned and packaged in `lib/arm64-v8a/`:

| Library Name | Uncompressed Size | Packed In APK | Role |
| :--- | :--- | :--- | :--- |
| `lib/arm64-v8a/libp3r_native_harness.so` | 7,160 bytes | **YES** | JNI bridge to Bionic dynamic loader (`dlopen`/`dlsym`) |
| `lib/arm64-v8a/libp3r_01_arithmetic.so` | 10,848 bytes | **YES** | Recompiled Fixture 01 (Integer ops, recursion, division) |
| `lib/arm64-v8a/libp3r_02_dispatch.so` | 9,112 bytes | **YES** | Recompiled Fixture 02 (Branching & function dispatch) |
| `lib/arm64-v8a/libp3r_03_memory_reloc.so` | 8,488 bytes | **YES** | Recompiled Fixture 03 (Rip-relative memory addressing) |
| `lib/arm64-v8a/libp3r_04_vector_simd.so` | 6,504 bytes | **YES** | Recompiled Fixture 04 (SSE/AVX 128-bit vector arithmetic) |
| `lib/arm64-v8a/libp3r_05_control_concurrency.so` | 6,288 bytes | **YES** | Recompiled Fixture 05 (Spinlocks & atomic cmpxchg) |
| `lib/arm64-v8a/libp3r_06_multithread_concurrency.so` | 7,560 bytes | **YES** | Recompiled Fixture 06 (Multithreaded counter increments) |

All 7 native `.so` files are correctly located in `lib/arm64-v8a/` and will be unpacked to the application's native library search path upon installation on any ARM64 Android device.
