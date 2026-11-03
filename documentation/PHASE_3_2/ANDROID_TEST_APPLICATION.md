# Android Native Test Application & JNI Harness Specification

## 1. Executive Summary

To validate that AOT-recompiled ARM64 code can execute inside a legitimate Android application context, Phase 3.2 implements a standalone, fully structured Android NDK application in `phase3-poc/android-app/`.

This application moves beyond CLI-only binaries, demonstrating execution within an Android process lifecycle, sandbox filesystem constraints, and the Android ART / JNI environment on ARM64-v8a devices.

---

## 2. Directory Structure & Component Architecture

```
phase3-poc/android-app/
├── build.gradle                       # Top-level Gradle configuration
├── settings.gradle                    # Project inclusion (:app)
├── README.md                          # Application build & run guide
└── app/
    ├── build.gradle                   # App module build file (NDK cmake, arm64-v8a)
    └── src/main/
        ├── AndroidManifest.xml        # Minimal manifest (SDK 28-34, portrait)
        ├── java/com/p3r/poc/
        │   └── MainActivity.java      # Activity UI, JNI bindings, background worker
        ├── res/
        │   ├── layout/
        │   │   └── activity_main.xml  # Monospace log view & test trigger UI
        │   └── values/
        │       └── strings.xml        # Localization strings
        └── cpp/
            ├── CMakeLists.txt         # NDK CMake build definition
            └── p3r_jni.c              # JNI bridge & Bionic dynamic loading harness
```

---

## 3. Component Details

### 3.1 UI & Activity Layer (`MainActivity.java`)
- **Library Pre-Loading:** Calls `System.loadLibrary("p3r_native_harness")` inside a static initialization block.
- **Native Method Signature:**
  ```java
  public native String runAotValidationSuite(String fixturesDir);
  ```
- **Asynchronous Execution:** Launches the test suite on a dedicated background thread to prevent Application Not Responding (ANR) warnings.
- **UI Feedback:** Renders live test results, execution duration, and JSON summaries into a scrollable `TextView` styled in monospace.

### 3.2 Native JNI Bridge (`p3r_jni.c`)
- Implements `Java_com_p3r_poc_MainActivity_runAotValidationSuite`.
- Directs Bionic `dlopen()` to load `libp3r_*.so` fixtures from the app's internal private storage directory (`/data/user/0/com.p3r.poc/files/`).
- Allocates guest memory and stack structures via `mmap()` (`MAP_PRIVATE | MAP_ANONYMOUS`).
- Invokes recompiled entrypoint functions natively on the CPU.
- Formats execution metrics into a machine-readable JSON payload returned directly to Java.
- Emits diagnostic messages to Android `logcat` under the tag `P3R-Native-Harness`.

### 3.3 Build Configuration (`CMakeLists.txt` & `build.gradle`)
- **Target ABI:** Strictly filtered to `arm64-v8a` (`Kryo / Cortex-A78`).
- **C Standard:** `C11` with `_Static_assert` and POSIX thread support.
- **Native Dependencies:** Links against Android NDK `liblog.so` and `libdl.so`.
- **Target SDK:** Android 14 (API level 34), backwards compatible to Android 9 (API level 28).

---

## 4. Build and Deployment Instructions

### 4.1 Building the APK
```bash
cd phase3-poc/android-app
./gradlew assembleDebug
```
The output APK is generated at:
`app/build/outputs/apk/debug/app-debug.apk`

### 4.2 Installing and Executing on Device
```bash
# 1. Install APK
adb install -r app/build/outputs/apk/debug/app-debug.apk

# 2. Push recompiled shared libraries to app internal storage
adb push ../tests/bin/libp3r_*.so /data/local/tmp/
adb shell "run-as com.p3r.poc cp /data/local/tmp/libp3r_*.so /data/user/0/com.p3r.poc/files/"

# 3. Launch Activity
adb shell am start -n com.p3r.poc/.MainActivity

# 4. View real-time logcat output
adb logcat -s P3R-Native-Harness:V
```
