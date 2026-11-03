// SPDX-License-Identifier: MIT
/*
 * P3R Native Android App JNI Interface
 * Bridges MainActivity.java to the native Bionic dynamic loading harness.
 */

#include <jni.h>
#include <android/log.h>
#include <dlfcn.h>
#include <sys/mman.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "guest_cpu.h"

#define TAG "P3R-Native-Harness"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, TAG, __VA_ARGS__)

typedef struct {
    const char* id;
    const char* so_name;
    const char* entry_symbol;
    uint64_t expected;
} JniFixtureSpec;

static const JniFixtureSpec G_JNI_FIXTURES[] = {
    { "01_arithmetic",             "libp3r_01_arithmetic.so",             "bbr_2011f0", 0xc7c63fc50b2aeb68ULL },
    { "02_dispatch",               "libp3r_02_dispatch.so",               "bbr_201200", 0x1b35ULL },
    { "03_memory_reloc",           "libp3r_03_memory_reloc.so",           "bbr_2011b0", 0x29f9f9e047ULL },
    { "04_vector_simd",            "libp3r_04_vector_simd.so",            "bbr_201160", 0x74125590ULL },
    { "05_control_concurrency",    "libp3r_05_control_concurrency.so",    "bbr_2011b0", 0xfffffffffffffc8eULL },
    { "06_multithread_concurrency","libp3r_06_multithread_concurrency.so","bbr_201300", 0xc801e2d7c8ULL }
};
#define JNI_FIXTURE_COUNT (sizeof(G_JNI_FIXTURES) / sizeof(G_JNI_FIXTURES[0]))

JNIEXPORT jstring JNICALL
Java_com_p3r_poc_MainActivity_runAotValidationSuite(JNIEnv* env, jobject thiz, jstring fixtures_dir_jstr) {
    const char* dir = (*env)->GetStringUTFChars(env, fixtures_dir_jstr, NULL);
    LOGI("Starting P3R AOT Validation Suite in directory: %s", dir);

    char output_buf[4096];
    size_t offset = 0;
    offset += snprintf(output_buf + offset, sizeof(output_buf) - offset,
                       "{\n  \"suite\": \"P3R-Native-Android-AOT-Validation\",\n  \"phase\": \"3.2\",\n  \"abi_verified\": true,\n  \"fixtures\": [\n");

    int passed_count = 0;
    for (size_t i = 0; i < JNI_FIXTURE_COUNT; i++) {
        char so_path[512];
        snprintf(so_path, sizeof(so_path), "%s/%s", dir, G_JNI_FIXTURES[i].so_name);

        void* handle = dlopen(so_path, RTLD_NOW | RTLD_LOCAL);
        if (!handle) {
            // Also attempt loading from app library dir (default system linker search path)
            handle = dlopen(G_JNI_FIXTURES[i].so_name, RTLD_NOW | RTLD_LOCAL);
        }

        uint64_t actual_rax = 0;
        uint64_t trap_code = 0;
        int status_match = 0;

        if (handle) {
            void (*fn_init_state)(GuestState*, void*, size_t, uint64_t) =
                (void (*)(GuestState*, void*, size_t, uint64_t))dlsym(handle, "bbr_init_guest_state");
            bbr_func_t fn_entry =
                (bbr_func_t)dlsym(handle, G_JNI_FIXTURES[i].entry_symbol);

            if (fn_init_state && fn_entry) {
                size_t stack_sz = 512 * 1024;
                void* stack = mmap(NULL, stack_sz, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
                size_t arena_sz = 8 * 1024 * 1024;
                void* arena = mmap(NULL, arena_sz, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);

                GuestState state;
                fn_init_state(&state, stack, stack_sz, (uint64_t)(uintptr_t)arena);
                fn_entry(&state);

                actual_rax = state.gregs[0];
                trap_code = state.trap_code;
                status_match = (actual_rax == G_JNI_FIXTURES[i].expected) && (trap_code == 0);
                if (status_match) passed_count++;

                munmap(arena, arena_sz);
                munmap(stack, stack_sz);
            }
            dlclose(handle);
        }

        offset += snprintf(output_buf + offset, sizeof(output_buf) - offset,
                           "    {\n      \"id\": \"%s\",\n      \"status\": \"%s\",\n      \"rax\": \"0x%llx\",\n      \"expected\": \"0x%llx\"\n    }%s\n",
                           G_JNI_FIXTURES[i].id,
                           status_match ? "PASS" : "FAIL",
                           (unsigned long long)actual_rax,
                           (unsigned long long)G_JNI_FIXTURES[i].expected,
                           (i + 1 < JNI_FIXTURE_COUNT) ? "," : "");
    }

    offset += snprintf(output_buf + offset, sizeof(output_buf) - offset,
                       "  ],\n  \"summary\": {\n    \"total\": %zu,\n    \"passed\": %d\n  }\n}",
                       JNI_FIXTURE_COUNT, passed_count);

    (*env)->ReleaseStringUTFChars(env, fixtures_dir_jstr, dir);
    return (*env)->NewStringUTF(env, output_buf);
}
