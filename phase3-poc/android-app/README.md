# P3R Native Android Test Application (Phase 3.2)

Minimal Android application harness for Persona 3 Reload AOT recompiled ARM64 shared libraries.

## Architecture

- **UI Layer:** Minimal single-activity UI (`MainActivity.java`, `activity_main.xml`) with execution trigger button and real-time result logs.
- **JNI Bridge:** `p3r_jni.c` implements JNI bindings between Android Java runtime and native Bionic execution layer.
- **Dynamic Loader:** Directly invokes Android Bionic `dlopen()`, `dlsym()`, `dlclose()` to load recompiled `.so` fixtures.
- **ABI & Memory:** Allocates guest memory and stack via `mmap()`, initializes `GuestState` (720 bytes, 16-byte aligned), and calls translated entrypoint functions natively on the CPU.

## Building via Android Gradle Plugin (AGP)

```bash
cd phase3-poc/android-app
./gradlew assembleDebug
```

The resulting APK will be at:
`app/build/outputs/apk/debug/app-debug.apk`

## Installing and Running on Device (e.g. realme 12 Pro+)

```bash
# Push recompiled shared libraries to app internal storage or /data/local/tmp
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb push ../tests/bin/libp3r_*.so /data/local/tmp/
adb shell am start -n com.p3r.poc/.MainActivity
```
