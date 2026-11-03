cmake_minimum_required(VERSION 3.22.1)
project("p3r_native_harness")

set(CMAKE_C_STANDARD 11)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Path to android-runtime headers
set(RUNTIME_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../../../../android-runtime)

include_directories(
    ${RUNTIME_DIR}
)

add_library(
    p3r_native_harness
    SHARED
    p3r_jni.c
    ${RUNTIME_DIR}/guest_cpu.c
)

find_library(log-lib log)

target_link_libraries(
    p3r_native_harness
    ${log-lib}
    dl
)
