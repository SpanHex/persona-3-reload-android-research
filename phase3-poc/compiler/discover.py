# SPDX-License-Identifier: MIT
"""
Iterative Function Discovery Engine
Re-implementation of discover.cpp and jumptable.cpp
"""

import capstone
from typing import Dict, List, Set, Tuple, Optional

class Function:
    def __init__(self, start_addr: int, end_addr: int = 0, kind: int = 0):
        self.start = start_addr
        self.end = end_addr
        self.kind = kind  # 0 = FDE / baseline, 3 = pseudo-function / discovered gap
        self.basic_blocks: List[Tuple[int, int]] = []  # (start, end)
        self.outgoing_targets: Set[int] = set()
        self.indirect_branch_sites: List[int] = []
        self.jump_tables: Dict[int, List[int]] = {}  # site -> list of targets
        self.sub_entries: Set[int] = set()

class DiscoveryEngine:
    def __init__(self, cs_mode=capstone.CS_MODE_64):
        self.md = capstone.Cs(capstone.CS_ARCH_X86, cs_mode)
        self.md.detail = True
        self.functions: Dict[int, Function] = {}
        self.extra_entries: Set[int] = set()
        self.all_discovered_targets: Set[int] = set()

    def load_extra_entries_file(self, path: str):
        """Matches readEntryList() in discover.cpp line 26"""
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("miss "):
                    line = line[5:].strip()
                if line.startswith("+"):
                    line = line[1:].strip()
                try:
                    addr = int(line, 16)
                    self.extra_entries.add(addr)
                except ValueError:
                    continue

    def discover_from_code(self, code_bytes: bytes, base_vaddr: int, known_entries: List[int]) -> Dict[int, Function]:
        """
        Iterative discovery loop matching discoverEntries() in discover.cpp line 49.
        Executes up to 16 rounds of discovery until reaching a fixpoint.
        """
        frontier: Set[int] = set(known_entries) | set(self.extra_entries)
        processed: Set[int] = set()

        for round_idx in range(16):
            new_candidates: Set[int] = set()
            
            for entry in sorted(frontier):
                if entry in processed:
                    continue
                processed.add(entry)

                offset = entry - base_vaddr
                if offset < 0 or offset >= len(code_bytes):
                    continue

                fn = Function(start_addr=entry, kind=0 if round_idx == 0 else 3)
                curr_offset = offset
                curr_vaddr = entry
                fn_end = len(code_bytes) + base_vaddr

                # Disassemble instructions sequentially
                instructions = list(self.md.disasm(code_bytes[curr_offset:], curr_vaddr))
                if not instructions:
                    continue

                block_start = curr_vaddr
                max_reach = entry

                for insn in instructions:
                    curr_vaddr = insn.address
                    mnemonic = insn.mnemonic.lower()

                    # 1. Direct Calls
                    if mnemonic == "call":
                        if insn.operands and insn.operands[0].type == capstone.x86.X86_OP_IMM:
                            target = insn.operands[0].imm
                            fn.outgoing_targets.add(target)
                            new_candidates.add(target)
                        else:
                            # Indirect call (e.g. call rax, call [rip+disp])
                            fn.indirect_branch_sites.append(insn.address)

                    # 2. Direct Unconditional & Conditional Jumps
                    elif mnemonic.startswith("j") and mnemonic != "jmp":
                        # Conditional jump (jcc)
                        if insn.operands and insn.operands[0].type == capstone.x86.X86_OP_IMM:
                            target = insn.operands[0].imm
                            fn.outgoing_targets.add(target)
                            if entry <= target < entry + 0x4000:
                                max_reach = max(max_reach, target)
                            else:
                                new_candidates.add(target)

                    elif mnemonic == "jmp":
                        if insn.operands and insn.operands[0].type == capstone.x86.X86_OP_IMM:
                            target = insn.operands[0].imm
                            fn.outgoing_targets.add(target)
                            if entry <= target < entry + 0x4000:
                                max_reach = max(max_reach, target)
                            else:
                                new_candidates.add(target)
                            if curr_vaddr >= max_reach:
                                fn_end = insn.address + insn.size
                                break
                        else:
                            # Indirect jump (switch table or tail call)
                            fn.indirect_branch_sites.append(insn.address)
                            if curr_vaddr >= max_reach:
                                fn_end = insn.address + insn.size
                                break

                    elif mnemonic in ("ret", "retf"):
                        if curr_vaddr >= max_reach:
                            fn_end = insn.address + insn.size
                            break

                    elif mnemonic in ("ud2", "int3"):
                        if curr_vaddr >= max_reach:
                            fn_end = insn.address + insn.size
                            break

                fn.end = fn_end
                self.functions[entry] = fn

            # Find candidates that lie outside current functions or inside gaps
            frontier = set()
            for cand in new_candidates:
                if cand not in self.functions and (base_vaddr <= cand < base_vaddr + len(code_bytes)):
                    frontier.add(cand)

            if not frontier:
                break

        return self.functions
