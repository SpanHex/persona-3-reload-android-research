#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
Phase 3.2.1 Automated Validation Test Runner
Distinguishes states: COMPILED, LINKED, LOADED, SYMBOL_RESOLVED, EXECUTED, MATCHED, NOT_TESTED, FAILED.
Records execution environments: host_x86_64, unicorn_x86_64, unicorn_aarch64, android_emulator_arm64, physical_android_arm64.
Preserves raw hashes, toolchain versions, and enforces non-zero exit codes on failures.
Outputs results to phase3-poc/test-results/phase-3.2.1/
"""

import os
import sys
import json
import time
import hashlib
import subprocess
import ctypes
import lief
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_ARCH_ARM64, UC_MODE_ARM
from unicorn import x86_const, arm64_const

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "compiler"))
from abi import GuestState, create_aligned_guest_state

BIN_DIR = os.path.join(REPO_ROOT, "tests", "bin")
MANIFEST_PATH = os.path.join(REPO_ROOT, "tests", "expected", "manifest.json")
RESULTS_DIR = os.path.join(REPO_ROOT, "test-results", "phase-3.2.1")
APK_PATH = os.path.join(REPO_ROOT, "android-app", "app", "build", "outputs", "apk", "debug", "app-debug.apk")
ADB_PATH = r"C:\Users\SPANDAN UPAMANYU\AppData\Local\Android\Sdk\platform-tools\adb.exe"

PAGE_SIZE = 4096

def sha256_file(filepath: str) -> str:
    if not os.path.exists(filepath):
        return None
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def get_toolchain_metadata() -> dict:
    return {
        "python": sys.version.split()[0],
        "ndk_version": "26.3.11579264 (r26c LTS)",
        "clang_version": "17.0.2 (NDK r26c)",
        "cmake_version": "3.22.1",
        "gradle_version": "8.5",
        "java_version": "17.0.21 (Microsoft OpenJDK LTS)",
        "target_api": 34,
        "target_abi": "arm64-v8a"
    }

def audit_adb_hardware() -> dict:
    res = {
        "attached": False,
        "device_model": None,
        "status": "NOT_TESTED",
        "reason": "Missing hardware connection"
    }
    if os.path.exists(ADB_PATH):
        try:
            proc = subprocess.run([ADB_PATH, "devices", "-l"], capture_output=True, text=True, timeout=5)
            lines = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
            for l in lines[1:]:
                if "device" in l and not l.startswith("*"):
                    res["attached"] = True
                    res["device_model"] = l
                    res["status"] = "CONNECTED"
                    res["reason"] = None
                    break
        except Exception as e:
            res["reason"] = f"ADB query failed: {str(e)}"
    else:
        res["reason"] = "adb.exe not found at configured platform-tools path"
    return res

def run_unicorn_x86(elf_path: str) -> dict:
    elf = lief.parse(elf_path)
    load_segs = [s for s in elf.segments if s.type.name == "LOAD"]
    min_v = min(s.virtual_address for s in load_segs)
    max_v = max(s.virtual_address + s.virtual_size for s in load_segs)
    page_start = (min_v // PAGE_SIZE) * PAGE_SIZE
    page_end = ((max_v + PAGE_SIZE - 1) // PAGE_SIZE) * PAGE_SIZE
    map_size = page_end - page_start

    mu = Uc(UC_ARCH_X86, UC_MODE_64)
    mu.mem_map(page_start, map_size)
    for s in load_segs:
        mu.mem_write(s.virtual_address, bytes(s.content))

    STACK_BASE = 0x70000000
    STACK_SIZE = 0x200000
    EXIT_ADDR = 0x80000000
    mu.mem_map(STACK_BASE, STACK_SIZE)
    mu.mem_map(EXIT_ADDR, 0x1000)

    sp = STACK_BASE + STACK_SIZE - 0x1000
    mu.mem_write(sp, (EXIT_ADDR).to_bytes(8, "little"))
    mu.reg_write(x86_const.UC_X86_REG_RSP, sp)
    mu.reg_write(x86_const.UC_X86_REG_RBP, sp)

    entry = elf.header.entrypoint
    start_t = time.perf_counter()
    mu.emu_start(entry, EXIT_ADDR)
    dur_ms = (time.perf_counter() - start_t) * 1000.0

    rax = mu.reg_read(x86_const.UC_X86_REG_RAX)
    return {
        "success": True,
        "entrypoint": hex(entry),
        "return_value_uint64": rax,
        "return_value_hex": hex(rax),
        "execution_time_ms": round(dur_ms, 3)
    }

def run_unicorn_arm64(so_path: str, elf_path: str) -> dict:
    if not os.path.exists(so_path):
        return {"success": False, "error": f"Shared library not found: {so_path}"}

    so = lief.parse(so_path)
    elf = lief.parse(elf_path)
    mu = Uc(UC_ARCH_ARM64, UC_MODE_ARM)

    for s in so.segments:
        if s.type.name == "LOAD":
            p_start = (s.virtual_address // PAGE_SIZE) * PAGE_SIZE
            p_end = ((s.virtual_address + s.virtual_size + PAGE_SIZE - 1) // PAGE_SIZE) * PAGE_SIZE
            try:
                mu.mem_map(p_start, p_end - p_start)
            except Exception:
                pass
            mu.mem_write(s.virtual_address, bytes(s.content))

    for s in elf.segments:
        if s.type.name == "LOAD":
            p_start = (s.virtual_address // PAGE_SIZE) * PAGE_SIZE
            p_end = ((s.virtual_address + s.virtual_size + PAGE_SIZE - 1) // PAGE_SIZE) * PAGE_SIZE
            try:
                mu.mem_map(p_start, p_end - p_start)
            except Exception:
                pass
            mu.mem_write(s.virtual_address, bytes(s.content))

    symbols = {f.name: f.address for f in so.exported_functions}
    target_vaddr = elf.header.entrypoint
    bbr_target_name = f"bbr_{hex(target_vaddr)[2:]}"
    entry_addr = symbols.get(bbr_target_name)
    if entry_addr is None:
        for name, addr in symbols.items():
            if name == bbr_target_name or (name.startswith("bbr_") and hex(target_vaddr)[2:] in name):
                entry_addr = addr
                break

    if entry_addr is None:
        return {"success": False, "error": f"Could not resolve entry function {bbr_target_name} in SO"}

    STATE_ADDR = 0x20000000
    STACK_ADDR = 0x30000000
    EXIT_ADDR  = 0x40000000
    GUEST_STACK_VADDR = 0x70000000

    mu.mem_map(STATE_ADDR, 0x1000)
    mu.mem_map(STACK_ADDR, 0x200000)
    mu.mem_map(EXIT_ADDR, 0x1000)
    mu.mem_map(GUEST_STACK_VADDR, 0x100000)

    st = create_aligned_guest_state()
    st.gregs[4] = GUEST_STACK_VADDR + 0x80000
    st.gregs[5] = GUEST_STACK_VADDR + 0x80000
    st.mem_base = 0
    st.rip = target_vaddr
    mu.mem_write(STATE_ADDR, bytes(st))

    mu.reg_write(arm64_const.UC_ARM64_REG_X0, STATE_ADDR)
    mu.reg_write(arm64_const.UC_ARM64_REG_SP, STACK_ADDR + 0x100000)
    mu.reg_write(arm64_const.UC_ARM64_REG_LR, EXIT_ADDR)

    start_t = time.perf_counter()
    try:
        mu.emu_start(entry_addr, EXIT_ADDR)
        dur_ms = (time.perf_counter() - start_t) * 1000.0

        res_bytes = mu.mem_read(STATE_ADDR, ctypes.sizeof(GuestState))
        out_state = GuestState.from_buffer_copy(res_bytes)
        rax = out_state.gregs[0]

        return {
            "success": True,
            "entry_function": bbr_target_name,
            "entry_addr": hex(entry_addr),
            "return_value_uint64": rax,
            "return_value_hex": hex(rax),
            "trap_code": out_state.trap_code,
            "exit_code": out_state.exit_code,
            "execution_time_ms": round(dur_ms, 3)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "entry_function": bbr_target_name,
            "entry_addr": hex(entry_addr)
        }

def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    log_lines = []
    def log(msg):
        print(msg)
        log_lines.append(msg)

    log("=" * 85)
    log("PHASE 3.2.1 AUTOMATED VALIDATION TEST HARNESS & INTEGRITY RUNNER")
    log("=" * 85)

    toolchain = get_toolchain_metadata()
    log(f"[*] Toolchain: NDK={toolchain['ndk_version']}, Clang={toolchain['clang_version']}, Gradle={toolchain['gradle_version']}")

    adb_status = audit_adb_hardware()
    log(f"[*] Physical Device Status: {adb_status['status']} ({adb_status['reason'] if not adb_status['attached'] else adb_status['device_model']})")

    apk_sha = sha256_file(APK_PATH)
    apk_exists = (apk_sha is not None)
    log(f"[*] Android APK Built: {'YES' if apk_exists else 'NO'} (SHA-256: {apk_sha[:16]}...)")

    with open(MANIFEST_PATH, "r") as f:
        manifest = json.load(f)

    fixtures = manifest["fixtures"]
    fixture_reports = []
    all_mandatory_passed = True

    log("\n" + "-" * 85)
    log(f"{'FIXTURE ID':<26} | {'COMP':<5} | {'LINK':<5} | {'LOAD':<5} | {'SYM':<5} | {'EXEC':<5} | {'MATCH':<5} | {'DEV':<7} | STATUS")
    log("-" * 85)

    for fix in fixtures:
        fid = fix["id"]
        elf_path = os.path.join(BIN_DIR, f"{fid}.elf")
        obj_path = os.path.join(BIN_DIR, f"{fid}.o")
        so_path = os.path.join(BIN_DIR, f"libp3r_{fid}.so")

        # 1. Hashes
        elf_sha = sha256_file(elf_path)
        obj_sha = sha256_file(obj_path)
        so_sha = sha256_file(so_path)

        # 2. Status checks
        is_compiled = (obj_sha is not None and os.path.getsize(obj_path) > 0)
        is_linked = (so_sha is not None and os.path.getsize(so_path) > 0)

        # 3. Dynamic inspections (LOADED & SYMBOL_RESOLVED)
        is_loaded = False
        is_sym_resolved = False
        entry_sym = None
        if is_linked:
            try:
                parsed_so = lief.parse(so_path)
                is_loaded = (parsed_so is not None and len(parsed_so.segments) > 0)
                exports = [f.name for f in parsed_so.exported_functions]
                target_sym = f"bbr_{hex(lief.parse(elf_path).header.entrypoint)[2:]}"
                if target_sym in exports:
                    is_sym_resolved = True
                    entry_sym = target_sym
            except Exception:
                pass

        # 4. Execution in unicorn_x86_64
        x86_res = run_unicorn_x86(elf_path)

        # 5. Execution in unicorn_aarch64
        arm_res = run_unicorn_arm64(so_path, elf_path)
        is_executed = arm_res.get("success", False)

        # 6. Output match
        is_matched = False
        if is_executed and x86_res.get("success", False):
            is_matched = (arm_res["return_value_uint64"] == x86_res["return_value_uint64"] and arm_res.get("trap_code", 1) == 0)

        if not is_matched:
            all_mandatory_passed = False

        status_label = "PASS (MATCHED)" if is_matched else "FAILED"
        log(f"{fid:<26} | {'YES' if is_compiled else 'NO':<5} | {'YES' if is_linked else 'NO':<5} | {'YES' if is_loaded else 'NO':<5} | {'YES' if is_sym_resolved else 'NO':<5} | {'YES' if is_executed else 'NO':<5} | {'YES' if is_matched else 'NO':<5} | {'N/T':<7} | {status_label}")

        report_entry = {
            "fixture": fid,
            "description": fix["description"],
            "compiled": is_compiled,
            "linked": is_linked,
            "loaded": is_loaded,
            "symbol_resolved": is_sym_resolved,
            "executed": is_executed,
            "matched": is_matched,
            "execution_environment": "unicorn_aarch64",
            "reference_environment": "unicorn_x86_64",
            "physical_device_environment": "physical_android_arm64",
            "physical_device_status": "NOT_TESTED",
            "expected_result": {
                "hex": x86_res.get("return_value_hex"),
                "uint64": x86_res.get("return_value_uint64"),
                "execution_time_ms": x86_res.get("execution_time_ms")
            },
            "actual_result": {
                "hex": arm_res.get("return_value_hex"),
                "uint64": arm_res.get("return_value_uint64"),
                "trap_code": arm_res.get("trap_code"),
                "exit_code": arm_res.get("exit_code"),
                "execution_time_ms": arm_res.get("execution_time_ms")
            },
            "hashes": {
                "input_elf_sha256": elf_sha,
                "recompiled_obj_sha256": obj_sha,
                "linked_so_sha256": so_sha
            },
            "error": arm_res.get("error") if not is_executed else None
        }
        fixture_reports.append(report_entry)

    log("-" * 85)
    matched_count = sum(1 for r in fixture_reports if r["matched"])
    log(f"[*] Summary: {matched_count}/{len(fixtures)} Fixtures Matched Bit-Exact.")
    log(f"[*] Physical Hardware Testing: NOT_TESTED (Realme 12 Pro+ not attached).")

    final_json = {
        "report_id": "P3R-AUTOTEST-321-001",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "phase": "3.2.1-evidence-validation",
        "toolchain": toolchain,
        "physical_hardware": {
            "target": "realme 12 Pro+ 5G (Snapdragon 7s Gen 2)",
            "attached": adb_status["attached"],
            "status": adb_status["status"],
            "reason": adb_status["reason"]
        },
        "apk_packaging": {
            "path": APK_PATH,
            "sha256": apk_sha,
            "exists": apk_exists
        },
        "summary": {
            "total_fixtures": len(fixtures),
            "compiled_count": sum(1 for r in fixture_reports if r["compiled"]),
            "linked_count": sum(1 for r in fixture_reports if r["linked"]),
            "loaded_count": sum(1 for r in fixture_reports if r["loaded"]),
            "symbol_resolved_count": sum(1 for r in fixture_reports if r["symbol_resolved"]),
            "executed_count": sum(1 for r in fixture_reports if r["executed"]),
            "matched_count": matched_count,
            "all_mandatory_passed": all_mandatory_passed
        },
        "fixtures": fixture_reports
    }

    report_out = os.path.join(RESULTS_DIR, "validation_report.json")
    with open(report_out, "w", encoding="utf-8") as rf:
        json.dump(final_json, rf, indent=2)

    log_out = os.path.join(RESULTS_DIR, "validation_log.txt")
    with open(log_out, "w", encoding="utf-8") as lf:
        lf.write("\n".join(log_lines) + "\n")

    log(f"[+] Output written to:\n    JSON: {report_out}\n    LOG:  {log_out}")
    log("=" * 85)

    if not all_mandatory_passed or not apk_exists:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
