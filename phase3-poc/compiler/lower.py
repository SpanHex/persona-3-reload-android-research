# SPDX-License-Identifier: MIT
"""
Instruction Lifter: x86-64 machine code -> LLVM IR
Implements CFG lowering logic matching Bloodborne-android-rebuild-tool:
- lower_ops.cpp: scalar arithmetic, basic-block CFG branching, safe division
- lower_vector.cpp: SSE/SSE2 packed float, int, and double operations
- docs/RECOMP_ABI.md: GuestState ABI v2 passing convention
"""

import capstone
import llvmlite.ir as ir
from typing import Dict, List, Optional, Tuple, Set

from abi import (
    GuestState, GPR_NAMES,
    RAX, RCX, RDX, RBX, RSP, RBP, RSI, RDI,
    R8, R9, R10, R11, R12, R13, R14, R15,
    BBR_TRAP_MISS, BBR_TRAP_UNLIFTABLE
)

# GPR Offset Table (in bytes from start of GuestState)
GPR_OFFSETS = {
    # 64-bit
    "rax": 0, "rcx": 8, "rdx": 16, "rbx": 24, "rsp": 32, "rbp": 40, "rsi": 48, "rdi": 56,
    "r8": 64, "r9": 72, "r10": 80, "r11": 88, "r12": 96, "r13": 104, "r14": 112, "r15": 120,
    # 32-bit
    "eax": 0, "ecx": 8, "edx": 16, "ebx": 24, "esp": 32, "ebp": 40, "esi": 48, "edi": 56,
    "r8d": 64, "r9d": 72, "r10d": 80, "r11d": 88, "r12d": 96, "r13d": 104, "r14d": 112, "r15d": 120,
    # 16-bit
    "ax": 0, "cx": 8, "dx": 16, "bx": 24, "sp": 32, "bp": 40, "si": 48, "di": 56,
    "r8w": 64, "r9w": 72, "r10w": 80, "r11w": 88, "r12w": 96, "r13w": 104, "r14w": 112, "r15w": 120,
    # 8-bit low
    "al": 0, "cl": 8, "dl": 16, "bl": 24, "spl": 32, "bpl": 40, "sil": 48, "dil": 56,
    "r8b": 64, "r9b": 72, "r10b": 80, "r11b": 88, "r12b": 96, "r13b": 104, "r14b": 112, "r15b": 120,
}

REG_WIDTHS = {
    # 64-bit
    "rax": 64, "rcx": 64, "rdx": 64, "rbx": 64, "rsp": 64, "rbp": 64, "rsi": 64, "rdi": 64,
    "r8": 64, "r9": 64, "r10": 64, "r11": 64, "r12": 64, "r13": 64, "r14": 64, "r15": 64,
    # 32-bit
    "eax": 32, "ecx": 32, "edx": 32, "ebx": 32, "esp": 32, "ebp": 32, "esi": 32, "edi": 32,
    "r8d": 32, "r9d": 32, "r10d": 32, "r11d": 32, "r12d": 32, "r13d": 32, "r14d": 32, "r15d": 32,
    # 16-bit
    "ax": 16, "cx": 16, "dx": 16, "bx": 16, "sp": 16, "bp": 16, "si": 16, "di": 16,
    "r8w": 16, "r9w": 16, "r10w": 16, "r11w": 16, "r12w": 16, "r13w": 16, "r14w": 16, "r15w": 16,
    # 8-bit
    "al": 8, "cl": 8, "dl": 8, "bl": 8, "spl": 8, "bpl": 8, "sil": 8, "dil": 8,
    "r8b": 8, "r9b": 8, "r10b": 8, "r11b": 8, "r12b": 8, "r13b": 8, "r14b": 8, "r15b": 8,
}

XMM_OFFSETS = {f"xmm{i}": 168 + i * 16 for i in range(16)}

class FunctionLifter:
    """
    Translates an x86-64 basic block or function into an LLVM IR function:
    void bbr_<vaddr>(GuestState* state)
    """
    def __init__(self, module: ir.Module, vaddr: int, code_bytes: bytes, md: capstone.Cs):
        self.module = module
        self.vaddr = vaddr
        self.code_bytes = code_bytes
        self.md = md

        # Types
        self.i1 = ir.IntType(1)
        self.i8 = ir.IntType(8)
        self.i16 = ir.IntType(16)
        self.i32 = ir.IntType(32)
        self.i64 = ir.IntType(64)
        self.i128 = ir.IntType(128)
        self.f32 = ir.FloatType()
        self.f64 = ir.DoubleType()
        self.v4f32 = ir.VectorType(self.f32, 4)
        self.v4i32 = ir.VectorType(self.i32, 4)
        self.v2f64 = ir.VectorType(self.f64, 2)
        self.v2i64 = ir.VectorType(self.i64, 2)

        self.state_ptr_t = ir.PointerType(self.i8)
        self.fn_type = ir.FunctionType(ir.VoidType(), [self.state_ptr_t])
        fn_name = f"bbr_{hex(vaddr)[2:]}"
        try:
            self.fn = self.module.get_global(fn_name)
        except KeyError:
            self.fn = ir.Function(self.module, self.fn_type, name=fn_name)
        self.state_arg = self.fn.args[0]
        self.state_arg.name = "guest_state"

        # Dispatch helper prototype: void bbr_dispatch(GuestState* s, uint64_t target_vaddr)
        dispatch_t = ir.FunctionType(ir.VoidType(), [self.state_ptr_t, self.i64])
        try:
            self.dispatch_fn = self.module.get_global("bbr_dispatch")
        except KeyError:
            self.dispatch_fn = ir.Function(self.module, dispatch_t, name="bbr_dispatch")

        # Trap helper prototype: void bbr_trap(GuestState* s, uint64_t trap_code)
        trap_t = ir.FunctionType(ir.VoidType(), [self.state_ptr_t, self.i64])
        try:
            self.trap_fn = self.module.get_global("bbr_trap")
        except KeyError:
            self.trap_fn = ir.Function(self.module, trap_t, name="bbr_trap")

        self.last_cmp_lhs = None
        self.last_cmp_rhs = None
        self.last_test_val = None

    def _state_gep(self, builder: ir.IRBuilder, byte_offset: int, dest_type: ir.Type) -> ir.Value:
        ptr = builder.gep(self.state_arg, [ir.Constant(self.i64, byte_offset)], name=f"off_{byte_offset}")
        return builder.bitcast(ptr, ir.PointerType(dest_type))

    def _load_gpr(self, builder: ir.IRBuilder, reg_name: str) -> ir.Value:
        reg_name = reg_name.lower()
        if reg_name not in GPR_OFFSETS:
            raise ValueError(f"Unsupported GPR: {reg_name}")
        offset = GPR_OFFSETS[reg_name]
        width = REG_WIDTHS[reg_name]

        if width == 64:
            ptr = self._state_gep(builder, offset, self.i64)
            return builder.load(ptr, name=f"{reg_name}_val")
        elif width == 32:
            ptr = self._state_gep(builder, offset, self.i32)
            val32 = builder.load(ptr, name=f"{reg_name}_val")
            return builder.zext(val32, self.i64, name=f"{reg_name}_zext")
        elif width == 16:
            ptr = self._state_gep(builder, offset, self.i16)
            return builder.load(ptr, name=f"{reg_name}_val")
        elif width == 8:
            ptr = self._state_gep(builder, offset, self.i8)
            return builder.load(ptr, name=f"{reg_name}_val")

    def _store_gpr(self, builder: ir.IRBuilder, reg_name: str, val: ir.Value):
        reg_name = reg_name.lower()
        if reg_name not in GPR_OFFSETS:
            raise ValueError(f"Unsupported GPR: {reg_name}")
        offset = GPR_OFFSETS[reg_name]
        width = REG_WIDTHS[reg_name]

        if width == 64:
            ptr = self._state_gep(builder, offset, self.i64)
            if val.type != self.i64:
                val = builder.zext(val, self.i64) if val.type.width < 64 else builder.trunc(val, self.i64)
            builder.store(val, ptr)
        elif width == 32:
            # x86-64 Rule: 32-bit register write ZERO-EXTENDS into 64-bit GPR!
            ptr64 = self._state_gep(builder, offset, self.i64)
            if val.type != self.i32:
                val32 = builder.trunc(val, self.i32)
            else:
                val32 = val
            val64 = builder.zext(val32, self.i64, name=f"{reg_name}_zeroext")
            builder.store(val64, ptr64)
        elif width == 16:
            ptr16 = self._state_gep(builder, offset, self.i16)
            val16 = builder.trunc(val, self.i16) if val.type.width > 16 else val
            builder.store(val16, ptr16)
        elif width == 8:
            ptr8 = self._state_gep(builder, offset, self.i8)
            val8 = builder.trunc(val, self.i8) if val.type.width > 8 else val
            builder.store(val8, ptr8)

    def _load_xmm(self, builder: ir.IRBuilder, xmm_name: str, as_type: ir.Type) -> ir.Value:
        offset = XMM_OFFSETS[xmm_name.lower()]
        ptr = self._state_gep(builder, offset, as_type)
        return builder.load(ptr, name=f"{xmm_name}_val")

    def _store_xmm(self, builder: ir.IRBuilder, xmm_name: str, val: ir.Value):
        offset = XMM_OFFSETS[xmm_name.lower()]
        ptr = self._state_gep(builder, offset, val.type)
        builder.store(val, ptr)

    def _resolve_mem_addr(self, builder: ir.IRBuilder, mem_op, insn_addr: int, insn_size: int) -> ir.Value:
        base_reg = self.md.reg_name(mem_op.mem.base) if mem_op.mem.base else None
        index_reg = self.md.reg_name(mem_op.mem.index) if mem_op.mem.index else None
        scale = mem_op.mem.scale
        disp = mem_op.mem.disp

        if base_reg == "rip":
            target_vaddr = insn_addr + insn_size + disp
            return ir.Constant(self.i64, target_vaddr)

        addr = ir.Constant(self.i64, 0)
        if base_reg:
            b_val = self._load_gpr(builder, base_reg)
            addr = builder.add(addr, b_val)
        if index_reg:
            idx_val = self._load_gpr(builder, index_reg)
            if scale > 1:
                idx_val = builder.mul(idx_val, ir.Constant(self.i64, scale))
            addr = builder.add(addr, idx_val)
        if disp != 0:
            addr = builder.add(addr, ir.Constant(self.i64, disp))
        return addr

    def _load_operand(self, builder: ir.IRBuilder, insn, op, target_type: Optional[ir.Type] = None) -> ir.Value:
        if op.type == capstone.x86.X86_OP_REG:
            reg_name = insn.reg_name(op.reg).lower()
            if reg_name.startswith("xmm"):
                t = target_type or self.v4f32
                return self._load_xmm(builder, reg_name, t)
            return self._load_gpr(builder, reg_name)
        elif op.type == capstone.x86.X86_OP_IMM:
            t = target_type or self.i64
            return ir.Constant(t, op.imm)
        elif op.type == capstone.x86.X86_OP_MEM:
            vaddr = self._resolve_mem_addr(builder, op, insn.address, insn.size)
            width = op.size * 8
            if target_type:
                elem_type = target_type
            elif width == 128:
                elem_type = self.v4f32
            elif width == 64:
                elem_type = self.i64
            elif width == 32:
                elem_type = self.i32
            elif width == 16:
                elem_type = self.i16
            else:
                elem_type = self.i8

            ptr = builder.inttoptr(vaddr, ir.PointerType(elem_type))
            val = builder.load(ptr, name=f"mem_ld_{hex(insn.address)}")
            if elem_type == self.i32 and target_type == self.i64:
                return builder.zext(val, self.i64)
            return val
        raise ValueError(f"Unknown operand type: {op.type}")

    def _store_operand(self, builder: ir.IRBuilder, insn, op, val: ir.Value):
        if op.type == capstone.x86.X86_OP_REG:
            reg_name = insn.reg_name(op.reg).lower()
            if reg_name.startswith("xmm"):
                self._store_xmm(builder, reg_name, val)
            else:
                self._store_gpr(builder, reg_name, val)
        elif op.type == capstone.x86.X86_OP_MEM:
            vaddr = self._resolve_mem_addr(builder, op, insn.address, insn.size)
            width = op.size * 8
            if width == 128 and val.type != self.v4f32 and val.type != self.v4i32 and val.type != self.v2f64:
                elem_type = self.v4f32
            elif width == 64 and val.type != self.i64 and val.type != self.f64:
                elem_type = self.i64
            elif width == 32 and val.type != self.i32 and val.type != self.f32:
                elem_type = self.i32
            else:
                elem_type = val.type

            ptr = builder.inttoptr(vaddr, ir.PointerType(elem_type))
            if val.type != elem_type:
                if isinstance(elem_type, ir.IntType) and isinstance(val.type, ir.IntType):
                    val = builder.trunc(val, elem_type) if val.type.width > elem_type.width else builder.zext(val, elem_type)
            builder.store(val, ptr)
        else:
            raise ValueError(f"Cannot store to operand type: {op.type}")

    def lift(self) -> ir.Function:
        """Main translation loop for the function with CFG basic-block graph"""
        entry_bb = self.fn.append_basic_block(name="entry")
        builder = ir.IRBuilder(entry_bb)

        instructions = list(self.md.disasm(self.code_bytes, self.vaddr))
        if not instructions:
            builder.ret_void()
            return self.fn

        # 1. Pre-allocate basic blocks for all instruction addresses
        block_map: Dict[int, ir.Block] = {}
        for insn in instructions:
            block_map[insn.address] = self.fn.append_basic_block(name=f"loc_{hex(insn.address)[2:]}")

        # Branch from entry block to first instruction block
        builder.branch(block_map[instructions[0].address])

        # 2. Lift instruction blocks
        for i, insn in enumerate(instructions):
            curr_bb = block_map[insn.address]
            builder.position_at_end(curr_bb)

            m = insn.mnemonic.lower()
            ops = insn.operands
            next_addr = instructions[i + 1].address if i + 1 < len(instructions) else None

            # 1. MOV / MOVZX / MOVSX
            if m in ("mov", "movabs"):
                val = self._load_operand(builder, insn, ops[1])
                self._store_operand(builder, insn, ops[0], val)

            elif m == "movzx":
                src = self._load_operand(builder, insn, ops[1])
                dst_width = REG_WIDTHS.get(insn.reg_name(ops[0].reg).lower(), 64)
                zext_val = builder.zext(src, ir.IntType(dst_width))
                self._store_operand(builder, insn, ops[0], zext_val)

            elif m == "movsx":
                src = self._load_operand(builder, insn, ops[1])
                dst_width = REG_WIDTHS.get(insn.reg_name(ops[0].reg).lower(), 64)
                sext_val = builder.sext(src, ir.IntType(dst_width))
                self._store_operand(builder, insn, ops[0], sext_val)

            elif m == "lea":
                eff_addr = self._resolve_mem_addr(builder, ops[1], insn.address, insn.size)
                self._store_operand(builder, insn, ops[0], eff_addr)

            # 2. Integer Arithmetic
            elif m == "add":
                lhs = self._load_operand(builder, insn, ops[0])
                rhs = self._load_operand(builder, insn, ops[1], target_type=lhs.type)
                res = builder.add(lhs, rhs, name="add_res")
                self._store_operand(builder, insn, ops[0], res)

            elif m == "sub":
                lhs = self._load_operand(builder, insn, ops[0])
                rhs = self._load_operand(builder, insn, ops[1], target_type=lhs.type)
                res = builder.sub(lhs, rhs, name="sub_res")
                self._store_operand(builder, insn, ops[0], res)

            elif m == "imul":
                if len(ops) == 2:
                    lhs = self._load_operand(builder, insn, ops[0])
                    rhs = self._load_operand(builder, insn, ops[1], target_type=lhs.type)
                    res = builder.mul(lhs, rhs, name="imul_res")
                    self._store_operand(builder, insn, ops[0], res)
                elif len(ops) == 3:
                    lhs = self._load_operand(builder, insn, ops[1])
                    rhs = self._load_operand(builder, insn, ops[2], target_type=lhs.type)
                    res = builder.mul(lhs, rhs, name="imul_res")
                    self._store_operand(builder, insn, ops[0], res)

            elif m in ("idiv", "div"):
                divisor = self._load_operand(builder, insn, ops[0])
                rax_val = self._load_gpr(builder, "rax")
                
                # Check zero divisor
                is_zero = builder.icmp_unsigned("==", divisor, ir.Constant(divisor.type, 0))
                with builder.if_then(is_zero):
                    builder.call(self.trap_fn, [self.state_arg, ir.Constant(self.i64, BBR_TRAP_UNLIFTABLE)])

                if m == "idiv":
                    q = builder.sdiv(rax_val, divisor)
                    r = builder.srem(rax_val, divisor)
                else:
                    q = builder.udiv(rax_val, divisor)
                    r = builder.urem(rax_val, divisor)
                self._store_gpr(builder, "rax", q)
                self._store_gpr(builder, "rdx", r)

            elif m == "neg":
                val = self._load_operand(builder, insn, ops[0])
                res = builder.neg(val)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "not":
                val = self._load_operand(builder, insn, ops[0])
                res = builder.not_(val)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "inc":
                val = self._load_operand(builder, insn, ops[0])
                res = builder.add(val, ir.Constant(val.type, 1))
                self._store_operand(builder, insn, ops[0], res)

            elif m == "dec":
                val = self._load_operand(builder, insn, ops[0])
                res = builder.sub(val, ir.Constant(val.type, 1))
                self._store_operand(builder, insn, ops[0], res)

            # 3. Bitwise & Shifts
            elif m == "and":
                lhs = self._load_operand(builder, insn, ops[0])
                rhs = self._load_operand(builder, insn, ops[1], target_type=lhs.type)
                res = builder.and_(lhs, rhs)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "or":
                lhs = self._load_operand(builder, insn, ops[0])
                rhs = self._load_operand(builder, insn, ops[1], target_type=lhs.type)
                res = builder.or_(lhs, rhs)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "xor":
                lhs = self._load_operand(builder, insn, ops[0])
                rhs = self._load_operand(builder, insn, ops[1], target_type=lhs.type)
                res = builder.xor(lhs, rhs)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "shl":
                lhs = self._load_operand(builder, insn, ops[0])
                shift = self._load_operand(builder, insn, ops[1], target_type=lhs.type)
                res = builder.shl(lhs, shift)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "shr":
                lhs = self._load_operand(builder, insn, ops[0])
                shift = self._load_operand(builder, insn, ops[1], target_type=lhs.type)
                res = builder.lshr(lhs, shift)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "sar":
                lhs = self._load_operand(builder, insn, ops[0])
                shift = self._load_operand(builder, insn, ops[1], target_type=lhs.type)
                res = builder.ashr(lhs, shift)
                self._store_operand(builder, insn, ops[0], res)

            # 4. Compare & Test
            elif m == "cmp":
                self.last_cmp_lhs = self._load_operand(builder, insn, ops[0])
                self.last_cmp_rhs = self._load_operand(builder, insn, ops[1], target_type=self.last_cmp_lhs.type)
                self.last_test_val = None

            elif m == "test":
                lhs = self._load_operand(builder, insn, ops[0])
                rhs = self._load_operand(builder, insn, ops[1], target_type=lhs.type)
                self.last_test_val = builder.and_(lhs, rhs)
                self.last_cmp_lhs = None
                self.last_cmp_rhs = None

            # 5. Conditional Branches
            elif m in ("je", "jz", "jne", "jnz", "jl", "jge", "jg", "jle", "jb", "ja", "jbe", "jae", "js", "jns"):
                target_vaddr = ops[0].imm
                pred = self._build_branch_predicate(builder, m)
                
                if target_vaddr in block_map and next_addr in block_map:
                    builder.cbranch(pred, block_map[target_vaddr], block_map[next_addr])
                else:
                    # Target is outside or dynamic
                    then_bb = self.fn.append_basic_block(name=f"br_take_{hex(target_vaddr)[2:]}")
                    fall_bb = block_map[next_addr] if next_addr in block_map else self.fn.append_basic_block("fall")
                    builder.cbranch(pred, then_bb, fall_bb)
                    builder.position_at_end(then_bb)
                    self._emit_call_or_jump(builder, target_vaddr, is_call=False)
                    builder.ret_void()

            # 6. Unconditional Jumps
            elif m == "jmp":
                if ops[0].type == capstone.x86.X86_OP_IMM:
                    target_vaddr = ops[0].imm
                    if target_vaddr in block_map:
                        builder.branch(block_map[target_vaddr])
                    else:
                        self._emit_call_or_jump(builder, target_vaddr, is_call=False)
                        builder.ret_void()
                else:
                    target_vaddr_val = self._load_operand(builder, insn, ops[0])
                    builder.call(self.dispatch_fn, [self.state_arg, target_vaddr_val])
                    builder.ret_void()

            # 7. Function Calls
            elif m == "call":
                if ops[0].type == capstone.x86.X86_OP_IMM:
                    target_vaddr = ops[0].imm
                    self._emit_call_or_jump(builder, target_vaddr, is_call=True)
                else:
                    target_vaddr_val = self._load_operand(builder, insn, ops[0])
                    builder.call(self.dispatch_fn, [self.state_arg, target_vaddr_val])

            # 8. Function Return
            elif m in ("ret", "retf"):
                builder.ret_void()

            # 9. Stack Push / Pop
            elif m == "push":
                val = self._load_operand(builder, insn, ops[0])
                rsp = self._load_gpr(builder, "rsp")
                new_rsp = builder.sub(rsp, ir.Constant(self.i64, 8))
                self._store_gpr(builder, "rsp", new_rsp)
                ptr = builder.inttoptr(new_rsp, ir.PointerType(self.i64))
                builder.store(val, ptr)

            elif m == "pop":
                rsp = self._load_gpr(builder, "rsp")
                ptr = builder.inttoptr(rsp, ir.PointerType(self.i64))
                val = builder.load(ptr)
                new_rsp = builder.add(rsp, ir.Constant(self.i64, 8))
                self._store_gpr(builder, "rsp", new_rsp)
                self._store_operand(builder, insn, ops[0], val)

            # 10. Vector / SSE Operations
            elif m in ("movaps", "movups", "movdqa", "movdqu"):
                val = self._load_operand(builder, insn, ops[1], target_type=self.v4f32)
                self._store_operand(builder, insn, ops[0], val)

            elif m == "addps":
                lhs = self._load_operand(builder, insn, ops[0], target_type=self.v4f32)
                rhs = self._load_operand(builder, insn, ops[1], target_type=self.v4f32)
                res = builder.fadd(lhs, rhs)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "subps":
                lhs = self._load_operand(builder, insn, ops[0], target_type=self.v4f32)
                rhs = self._load_operand(builder, insn, ops[1], target_type=self.v4f32)
                res = builder.fsub(lhs, rhs)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "mulps":
                lhs = self._load_operand(builder, insn, ops[0], target_type=self.v4f32)
                rhs = self._load_operand(builder, insn, ops[1], target_type=self.v4f32)
                res = builder.fmul(lhs, rhs)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "paddd":
                lhs = self._load_operand(builder, insn, ops[0], target_type=self.v4i32)
                rhs = self._load_operand(builder, insn, ops[1], target_type=self.v4i32)
                res = builder.add(lhs, rhs)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "psubd":
                lhs = self._load_operand(builder, insn, ops[0], target_type=self.v4i32)
                rhs = self._load_operand(builder, insn, ops[1], target_type=self.v4i32)
                res = builder.sub(lhs, rhs)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "pxor":
                lhs = self._load_operand(builder, insn, ops[0], target_type=self.v4i32)
                rhs = self._load_operand(builder, insn, ops[1], target_type=self.v4i32)
                res = builder.xor(lhs, rhs)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "mulpd":
                lhs = self._load_operand(builder, insn, ops[0], target_type=self.v2f64)
                rhs = self._load_operand(builder, insn, ops[1], target_type=self.v2f64)
                res = builder.fmul(lhs, rhs)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "subpd":
                lhs = self._load_operand(builder, insn, ops[0], target_type=self.v2f64)
                rhs = self._load_operand(builder, insn, ops[1], target_type=self.v2f64)
                res = builder.fsub(lhs, rhs)
                self._store_operand(builder, insn, ops[0], res)

            # 11. Scalar Floats
            elif m == "addsd":
                lhs = self._load_operand(builder, insn, ops[0], target_type=self.f64)
                rhs = self._load_operand(builder, insn, ops[1], target_type=self.f64)
                res = builder.fadd(lhs, rhs)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "subsd":
                lhs = self._load_operand(builder, insn, ops[0], target_type=self.f64)
                rhs = self._load_operand(builder, insn, ops[1], target_type=self.f64)
                res = builder.fsub(lhs, rhs)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "mulsd":
                lhs = self._load_operand(builder, insn, ops[0], target_type=self.f64)
                rhs = self._load_operand(builder, insn, ops[1], target_type=self.f64)
                res = builder.fmul(lhs, rhs)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "divsd":
                lhs = self._load_operand(builder, insn, ops[0], target_type=self.f64)
                rhs = self._load_operand(builder, insn, ops[1], target_type=self.f64)
                res = builder.fdiv(lhs, rhs)
                self._store_operand(builder, insn, ops[0], res)

            # 12. Atomics
            elif m == "xadd":
                vaddr = self._resolve_mem_addr(builder, ops[0], insn.address, insn.size)
                ptr = builder.inttoptr(vaddr, ir.PointerType(self.i64))
                add_val = self._load_operand(builder, insn, ops[1])
                old_val = builder.atomic_rmw("add", ptr, add_val, ordering="seq_cst")
                self._store_operand(builder, insn, ops[1], old_val)

            elif m == "cmpxchg":
                vaddr = self._resolve_mem_addr(builder, ops[0], insn.address, insn.size)
                ptr = builder.inttoptr(vaddr, ir.PointerType(self.i64))
                expected = self._load_gpr(builder, "rax")
                new_val = self._load_operand(builder, insn, ops[1])
                pair = builder.cmpxchg(ptr, expected, new_val, ordering="seq_cst", failordering="seq_cst")
                loaded_val = builder.extract_value(pair, 0)
                success = builder.extract_value(pair, 1)
                self._store_gpr(builder, "rax", loaded_val)
                zf_val = builder.zext(success, self.i64)
                flags_ptr = self._state_gep(builder, 136, self.i64)
                builder.store(zf_val, flags_ptr)

            else:
                builder.call(self.trap_fn, [self.state_arg, ir.Constant(self.i64, BBR_TRAP_UNLIFTABLE)])

            # If this instruction did not terminate the block, fall through to next instruction
            if not builder.block.is_terminated and next_addr in block_map:
                builder.branch(block_map[next_addr])

        # Final termination guard
        for bb in self.fn.basic_blocks:
            if not bb.is_terminated:
                b_fix = ir.IRBuilder(bb)
                b_fix.ret_void()

        return self.fn

    def _build_branch_predicate(self, builder: ir.IRBuilder, mnemonic: str) -> ir.Value:
        """Constructs boolean condition for branch instructions"""
        if self.last_test_val is not None:
            zero = ir.Constant(self.last_test_val.type, 0)
            if mnemonic in ("je", "jz"):
                return builder.icmp_unsigned("==", self.last_test_val, zero)
            elif mnemonic in ("jne", "jnz"):
                return builder.icmp_unsigned("!=", self.last_test_val, zero)
            elif mnemonic == "js":
                return builder.icmp_signed("<", self.last_test_val, zero)
            elif mnemonic == "jns":
                return builder.icmp_signed(">=", self.last_test_val, zero)

        if self.last_cmp_lhs is not None and self.last_cmp_rhs is not None:
            lhs = self.last_cmp_lhs
            rhs = self.last_cmp_rhs
            if mnemonic in ("je", "jz"):
                return builder.icmp_unsigned("==", lhs, rhs)
            elif mnemonic in ("jne", "jnz"):
                return builder.icmp_unsigned("!=", lhs, rhs)
            elif mnemonic == "jl":
                return builder.icmp_signed("<", lhs, rhs)
            elif mnemonic == "jge":
                return builder.icmp_signed(">=", lhs, rhs)
            elif mnemonic == "jg":
                return builder.icmp_signed(">", lhs, rhs)
            elif mnemonic == "jle":
                return builder.icmp_signed("<=", lhs, rhs)
            elif mnemonic == "jb":
                return builder.icmp_unsigned("<", lhs, rhs)
            elif mnemonic == "jae":
                return builder.icmp_unsigned(">=", lhs, rhs)
            elif mnemonic == "ja":
                return builder.icmp_unsigned(">", lhs, rhs)
            elif mnemonic == "jbe":
                return builder.icmp_unsigned("<=", lhs, rhs)

        return ir.Constant(self.i1, 1)

    def _emit_call_or_jump(self, builder: ir.IRBuilder, target_vaddr: int, is_call: bool):
        target_fn_name = f"bbr_{hex(target_vaddr)[2:]}"
        try:
            target_fn = self.module.get_global(target_fn_name)
        except KeyError:
            target_fn = ir.Function(self.module, self.fn_type, name=target_fn_name)

        builder.call(target_fn, [self.state_arg])
