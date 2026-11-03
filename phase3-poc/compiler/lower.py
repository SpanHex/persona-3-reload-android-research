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
    BBR_TRAP_MISS, BBR_TRAP_UNLIFTABLE, BBR_TRAP_DIV_ZERO, BBR_TRAP_OVERFLOW
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
    # 8-bit high (bits 8..15 of RAX, RCX, RDX, RBX)
    "ah": 1, "ch": 9, "dh": 17, "bh": 25,
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
    # 8-bit low & high
    "al": 8, "cl": 8, "dl": 8, "bl": 8, "spl": 8, "bpl": 8, "sil": 8, "dil": 8,
    "r8b": 8, "r9b": 8, "r10b": 8, "r11b": 8, "r12b": 8, "r13b": 8, "r14b": 8, "r15b": 8,
    "ah": 8, "ch": 8, "dh": 8, "bh": 8,
}

XMM_OFFSETS = {f"xmm{i}": 168 + i * 16 for i in range(16)}

MEM_BASE_OFFSET = 696
FLAGS_OFFSET = 136

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

        # Condition flags state
        self.ptr_zf = None
        self.ptr_sf = None
        self.ptr_cf = None
        self.ptr_of = None
        self.last_cmp_lhs = None
        self.last_cmp_rhs = None
        self.last_test_val = None

    def _state_gep(self, builder: ir.IRBuilder, byte_offset: int, dest_type: ir.Type) -> ir.Value:
        ptr = builder.gep(self.state_arg, [ir.Constant(self.i64, byte_offset)], name=f"off_{byte_offset}")
        return builder.bitcast(ptr, ir.PointerType(dest_type))

    def _get_mem_base(self, builder: ir.IRBuilder) -> ir.Value:
        ptr = self._state_gep(builder, MEM_BASE_OFFSET, self.i64)
        return builder.load(ptr, name="mem_base")

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
            return builder.load(ptr, name=f"{reg_name}_val")
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
            # 8-bit store preserves other bytes in GPR (including AH/CH/DH/BH at offset 1, 9, 17, 25)
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
            if b_val.type != self.i64:
                b_val = builder.zext(b_val, self.i64)
            addr = builder.add(addr, b_val)
        if index_reg:
            idx_val = self._load_gpr(builder, index_reg)
            if idx_val.type != self.i64:
                idx_val = builder.zext(idx_val, self.i64)
            if scale > 1:
                idx_val = builder.mul(idx_val, ir.Constant(self.i64, scale))
            addr = builder.add(addr, idx_val)
        if disp != 0:
            addr = builder.add(addr, ir.Constant(self.i64, disp))
        return addr

    def _get_host_ptr(self, builder: ir.IRBuilder, vaddr: ir.Value, elem_type: ir.Type) -> ir.Value:
        mem_base = self._get_mem_base(builder)
        host_addr = builder.add(mem_base, vaddr, name="host_addr")
        return builder.inttoptr(host_addr, ir.PointerType(elem_type))

    def _load_operand(self, builder: ir.IRBuilder, insn, op, target_type: Optional[ir.Type] = None) -> ir.Value:
        if op.type == capstone.x86.X86_OP_REG:
            reg_name = insn.reg_name(op.reg).lower()
            if reg_name.startswith("xmm"):
                t = target_type or self.v4f32
                return self._load_xmm(builder, reg_name, t)
            val = self._load_gpr(builder, reg_name)
            if target_type and val.type != target_type:
                if isinstance(target_type, ir.IntType) and isinstance(val.type, ir.IntType):
                    return builder.trunc(val, target_type) if val.type.width > target_type.width else builder.zext(val, target_type)
            return val
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

            ptr = self._get_host_ptr(builder, vaddr, elem_type)
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
            if width == 128 and val.type not in (self.v4f32, self.v4i32, self.v2f64, self.v2i64):
                elem_type = self.v4f32
            elif width == 64 and val.type not in (self.i64, self.f64):
                elem_type = self.i64
            elif width == 32 and val.type not in (self.i32, self.f32):
                elem_type = self.i32
            elif width == 16 and val.type != self.i16:
                elem_type = self.i16
            elif width == 8 and val.type != self.i8:
                elem_type = self.i8
            else:
                elem_type = val.type

            ptr = self._get_host_ptr(builder, vaddr, elem_type)
            if val.type != elem_type:
                if isinstance(elem_type, ir.IntType) and isinstance(val.type, ir.IntType):
                    val = builder.trunc(val, elem_type) if val.type.width > elem_type.width else builder.zext(val, elem_type)
            builder.store(val, ptr)
        else:
            raise ValueError(f"Cannot store to operand type: {op.type}")

    def _update_flags_arith(self, builder: ir.IRBuilder, res: ir.Value, lhs: ir.Value, rhs: ir.Value,
                            is_sub: bool = False, is_logic: bool = False, is_inc: bool = False, is_dec: bool = False):
        zero = ir.Constant(res.type, 0)
        zf = builder.icmp_unsigned("==", res, zero, name="zf")
        sf = builder.icmp_signed("<", res, zero, name="sf")
        builder.store(zf, self.ptr_zf)
        builder.store(sf, self.ptr_sf)

        if is_logic:
            builder.store(ir.Constant(self.i1, 0), self.ptr_cf)
            builder.store(ir.Constant(self.i1, 0), self.ptr_of)
        elif is_sub:
            cf = builder.icmp_unsigned("<", lhs, rhs, name="cf")
            lhs_neg = builder.icmp_signed("<", lhs, zero)
            rhs_neg = builder.icmp_signed("<", rhs, zero)
            res_neg = sf
            diff_signs = builder.xor(lhs_neg, rhs_neg)
            res_diff_lhs = builder.xor(res_neg, lhs_neg)
            of = builder.and_(diff_signs, res_diff_lhs, name="of")
            builder.store(cf, self.ptr_cf)
            builder.store(of, self.ptr_of)
        elif is_inc:
            lhs_neg = builder.icmp_signed("<", lhs, zero)
            res_neg = sf
            of = builder.and_(builder.not_(lhs_neg), res_neg, name="of")
            builder.store(of, self.ptr_of)
        elif is_dec:
            lhs_neg = builder.icmp_signed("<", lhs, zero)
            res_neg = sf
            of = builder.and_(lhs_neg, builder.not_(res_neg), name="of")
            builder.store(of, self.ptr_of)
        else: # add
            cf = builder.icmp_unsigned("<", res, lhs, name="cf")
            lhs_neg = builder.icmp_signed("<", lhs, zero)
            rhs_neg = builder.icmp_signed("<", rhs, zero)
            res_neg = sf
            same_signs = builder.not_(builder.xor(lhs_neg, rhs_neg))
            res_diff_lhs = builder.xor(res_neg, lhs_neg)
            of = builder.and_(same_signs, res_diff_lhs, name="of")
            builder.store(cf, self.ptr_cf)
            builder.store(of, self.ptr_of)

    def _sync_flags_to_state(self, builder: ir.IRBuilder):
        """Packs condition flags into GuestState.flags (offset 136)"""
        zf = builder.load(self.ptr_zf, name="cur_zf")
        sf = builder.load(self.ptr_sf, name="cur_sf")
        cf = builder.load(self.ptr_cf, name="cur_cf")
        of = builder.load(self.ptr_of, name="cur_of")
        cf_val = builder.zext(cf, self.i64)
        zf_val = builder.shl(builder.zext(zf, self.i64), ir.Constant(self.i64, 6))
        sf_val = builder.shl(builder.zext(sf, self.i64), ir.Constant(self.i64, 7))
        of_val = builder.shl(builder.zext(of, self.i64), ir.Constant(self.i64, 11))
        packed = builder.or_(builder.or_(cf_val, zf_val), builder.or_(sf_val, of_val))
        flags_ptr = self._state_gep(builder, FLAGS_OFFSET, self.i64)
        builder.store(packed, flags_ptr)

    def lift(self) -> ir.Function:
        """Main translation loop for the function with CFG basic-block graph"""
        entry_bb = self.fn.append_basic_block(name="entry")
        builder = ir.IRBuilder(entry_bb)

        # Allocate flag slots in entry block for SSA dominance across all BBs
        self.ptr_zf = builder.alloca(self.i1, name="flag_zf")
        self.ptr_sf = builder.alloca(self.i1, name="flag_sf")
        self.ptr_cf = builder.alloca(self.i1, name="flag_cf")
        self.ptr_of = builder.alloca(self.i1, name="flag_of")
        builder.store(ir.Constant(self.i1, 0), self.ptr_zf)
        builder.store(ir.Constant(self.i1, 0), self.ptr_sf)
        builder.store(ir.Constant(self.i1, 0), self.ptr_cf)
        builder.store(ir.Constant(self.i1, 0), self.ptr_of)

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
            if m.startswith("lock "):
                m = m[5:]
            ops = insn.operands
            next_addr = instructions[i + 1].address if i + 1 < len(instructions) else None

            # Skip NOPs and spin hints
            if m.startswith("nop") or m == "pause":
                pass

            # 1. MOV / MOVZX / MOVSX / MOVSXD
            elif m in ("mov", "movabs"):
                val = self._load_operand(builder, insn, ops[1])
                self._store_operand(builder, insn, ops[0], val)

            elif m == "movzx" or m.startswith("movzb"):
                src = self._load_operand(builder, insn, ops[1])
                dst_reg = insn.reg_name(ops[0].reg).lower() if ops[0].type == capstone.x86.X86_OP_REG else None
                dst_width = REG_WIDTHS.get(dst_reg, 64) if dst_reg else 64
                dst_type = ir.IntType(dst_width)
                if src.type.width > dst_width:
                    zext_val = builder.trunc(src, dst_type)
                elif src.type.width < dst_width:
                    zext_val = builder.zext(src, dst_type)
                else:
                    zext_val = src
                self._store_operand(builder, insn, ops[0], zext_val)

            elif m in ("movsx", "movsxd", "movslq") or m.startswith("movsb"):
                src = self._load_operand(builder, insn, ops[1], target_type=self.i32 if m in ("movsxd", "movslq") else None)
                dst_reg = insn.reg_name(ops[0].reg).lower() if ops[0].type == capstone.x86.X86_OP_REG else None
                dst_width = REG_WIDTHS.get(dst_reg, 64) if dst_reg else 64
                dst_type = ir.IntType(dst_width)
                if src.type.width > dst_width:
                    sext_val = builder.trunc(src, dst_type)
                elif src.type.width < dst_width:
                    sext_val = builder.sext(src, dst_type)
                else:
                    sext_val = src
                self._store_operand(builder, insn, ops[0], sext_val)

            elif m == "cqto" or m == "cqo":
                # Sign-extend RAX into RDX:RAX
                rax = self._load_gpr(builder, "rax")
                sign = builder.ashr(rax, ir.Constant(self.i64, 63), name="cqto_sign")
                self._store_gpr(builder, "rdx", sign)

            elif m == "cdq":
                # Sign-extend EAX into EDX:EAX
                eax = self._load_gpr(builder, "eax")
                eax32 = builder.trunc(eax, self.i32)
                sign32 = builder.ashr(eax32, ir.Constant(self.i32, 31))
                self._store_gpr(builder, "edx", builder.zext(sign32, self.i64))

            elif m == "cdqe":
                # Sign-extend EAX into RAX
                eax = self._load_gpr(builder, "eax")
                eax32 = builder.trunc(eax, self.i32)
                self._store_gpr(builder, "rax", builder.sext(eax32, self.i64))

            elif m == "lea":
                eff_addr = self._resolve_mem_addr(builder, ops[1], insn.address, insn.size)
                self._store_operand(builder, insn, ops[0], eff_addr)

            # 2. Integer Arithmetic
            elif m == "add":
                lhs = self._load_operand(builder, insn, ops[0])
                rhs = self._load_operand(builder, insn, ops[1], target_type=lhs.type)
                res = builder.add(lhs, rhs, name="add_res")
                self._store_operand(builder, insn, ops[0], res)
                self._update_flags_arith(builder, res, lhs, rhs, is_sub=False)
                self._sync_flags_to_state(builder)

            elif m == "sub":
                lhs = self._load_operand(builder, insn, ops[0])
                rhs = self._load_operand(builder, insn, ops[1], target_type=lhs.type)
                res = builder.sub(lhs, rhs, name="sub_res")
                self._store_operand(builder, insn, ops[0], res)
                self._update_flags_arith(builder, res, lhs, rhs, is_sub=True)
                self._sync_flags_to_state(builder)

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
                
                # Check zero divisor
                is_zero = builder.icmp_unsigned("==", divisor, ir.Constant(divisor.type, 0))
                with builder.if_then(is_zero):
                    builder.call(self.trap_fn, [self.state_arg, ir.Constant(self.i64, BBR_TRAP_DIV_ZERO)])

                if divisor.type.width == 64:
                    rax_val = self._load_gpr(builder, "rax")
                    rdx_val = self._load_gpr(builder, "rdx")
                    
                    if m == "idiv":
                        # Check signed division overflow: INT64_MIN / -1
                        is_int_min = builder.icmp_signed("==", rax_val, ir.Constant(self.i64, -0x8000000000000000))
                        is_neg_one = builder.icmp_signed("==", divisor, ir.Constant(self.i64, -1))
                        is_rdx_sign = builder.icmp_signed("==", rdx_val, ir.Constant(self.i64, -1))
                        overflow = builder.and_(builder.and_(is_int_min, is_neg_one), is_rdx_sign)
                        with builder.if_then(overflow):
                            builder.call(self.trap_fn, [self.state_arg, ir.Constant(self.i64, BBR_TRAP_OVERFLOW)])

                        # Assemble 128-bit dividend: (RDX << 64) | RAX
                        dividend128 = builder.or_(
                            builder.shl(builder.zext(rdx_val, self.i128), ir.Constant(self.i128, 64)),
                            builder.zext(rax_val, self.i128)
                        )
                        div128 = builder.sext(divisor, self.i128)
                        q = builder.trunc(builder.sdiv(dividend128, div128), self.i64)
                        r = builder.trunc(builder.srem(dividend128, div128), self.i64)
                    else:
                        dividend128 = builder.or_(
                            builder.shl(builder.zext(rdx_val, self.i128), ir.Constant(self.i128, 64)),
                            builder.zext(rax_val, self.i128)
                        )
                        div128 = builder.zext(divisor, self.i128)
                        q = builder.trunc(builder.udiv(dividend128, div128), self.i64)
                        r = builder.trunc(builder.urem(dividend128, div128), self.i64)

                    self._store_gpr(builder, "rax", q)
                    self._store_gpr(builder, "rdx", r)

                else: # 32-bit division
                    eax_val = builder.trunc(self._load_gpr(builder, "eax"), self.i32)
                    edx_val = builder.trunc(self._load_gpr(builder, "edx"), self.i32)
                    div32 = builder.trunc(divisor, self.i32) if divisor.type.width > 32 else divisor

                    if m == "idiv":
                        dividend64 = builder.or_(
                            builder.shl(builder.zext(edx_val, self.i64), ir.Constant(self.i64, 32)),
                            builder.zext(eax_val, self.i64)
                        )
                        div64 = builder.sext(div32, self.i64)
                        q = builder.trunc(builder.sdiv(dividend64, div64), self.i32)
                        r = builder.trunc(builder.srem(dividend64, div64), self.i32)
                    else:
                        dividend64 = builder.or_(
                            builder.shl(builder.zext(edx_val, self.i64), ir.Constant(self.i64, 32)),
                            builder.zext(eax_val, self.i64)
                        )
                        div64 = builder.zext(div32, self.i64)
                        q = builder.trunc(builder.udiv(dividend64, div64), self.i32)
                        r = builder.trunc(builder.urem(dividend64, div64), self.i32)

                    self._store_gpr(builder, "eax", q)
                    self._store_gpr(builder, "edx", r)

            elif m == "neg":
                val = self._load_operand(builder, insn, ops[0])
                res = builder.neg(val)
                self._store_operand(builder, insn, ops[0], res)
                self._update_flags_arith(builder, res, ir.Constant(val.type, 0), val, is_sub=True)
                self._sync_flags_to_state(builder)

            elif m == "not":
                val = self._load_operand(builder, insn, ops[0])
                res = builder.not_(val)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "inc":
                val = self._load_operand(builder, insn, ops[0])
                res = builder.add(val, ir.Constant(val.type, 1))
                self._store_operand(builder, insn, ops[0], res)
                self._update_flags_arith(builder, res, val, ir.Constant(val.type, 1), is_inc=True)
                self._sync_flags_to_state(builder)

            elif m == "dec":
                val = self._load_operand(builder, insn, ops[0])
                res = builder.sub(val, ir.Constant(val.type, 1))
                self._store_operand(builder, insn, ops[0], res)
                self._update_flags_arith(builder, res, val, ir.Constant(val.type, 1), is_dec=True)
                self._sync_flags_to_state(builder)

            # 3. Bitwise & Shifts
            elif m == "and":
                lhs = self._load_operand(builder, insn, ops[0])
                rhs = self._load_operand(builder, insn, ops[1], target_type=lhs.type)
                res = builder.and_(lhs, rhs)
                self._store_operand(builder, insn, ops[0], res)
                self._update_flags_arith(builder, res, lhs, rhs, is_logic=True)
                self._sync_flags_to_state(builder)

            elif m == "or":
                lhs = self._load_operand(builder, insn, ops[0])
                rhs = self._load_operand(builder, insn, ops[1], target_type=lhs.type)
                res = builder.or_(lhs, rhs)
                self._store_operand(builder, insn, ops[0], res)
                self._update_flags_arith(builder, res, lhs, rhs, is_logic=True)
                self._sync_flags_to_state(builder)

            elif m == "xor":
                lhs = self._load_operand(builder, insn, ops[0])
                rhs = self._load_operand(builder, insn, ops[1], target_type=lhs.type)
                res = builder.xor(lhs, rhs)
                self._store_operand(builder, insn, ops[0], res)
                self._update_flags_arith(builder, res, lhs, rhs, is_logic=True)
                self._sync_flags_to_state(builder)

            elif m == "shl":
                lhs = self._load_operand(builder, insn, ops[0])
                shift = self._load_operand(builder, insn, ops[1], target_type=lhs.type)
                # x86 shift count masking eliminates UB
                shift_mask = ir.Constant(shift.type, lhs.type.width - 1)
                safe_shift = builder.and_(shift, shift_mask)
                res = builder.shl(lhs, safe_shift)
                self._store_operand(builder, insn, ops[0], res)
                self._update_flags_arith(builder, res, lhs, shift, is_logic=True)

            elif m == "shr":
                lhs = self._load_operand(builder, insn, ops[0])
                shift = self._load_operand(builder, insn, ops[1], target_type=lhs.type)
                shift_mask = ir.Constant(shift.type, lhs.type.width - 1)
                safe_shift = builder.and_(shift, shift_mask)
                res = builder.lshr(lhs, safe_shift)
                self._store_operand(builder, insn, ops[0], res)
                self._update_flags_arith(builder, res, lhs, shift, is_logic=True)

            elif m == "sar":
                lhs = self._load_operand(builder, insn, ops[0])
                shift = self._load_operand(builder, insn, ops[1], target_type=lhs.type)
                shift_mask = ir.Constant(shift.type, lhs.type.width - 1)
                safe_shift = builder.and_(shift, shift_mask)
                res = builder.ashr(lhs, safe_shift)
                self._store_operand(builder, insn, ops[0], res)
                self._update_flags_arith(builder, res, lhs, shift, is_logic=True)

            # 4. Compare & Test
            elif m == "cmp":
                self.last_cmp_lhs = self._load_operand(builder, insn, ops[0])
                self.last_cmp_rhs = self._load_operand(builder, insn, ops[1], target_type=self.last_cmp_lhs.type)
                sub_res = builder.sub(self.last_cmp_lhs, self.last_cmp_rhs)
                self._update_flags_arith(builder, sub_res, self.last_cmp_lhs, self.last_cmp_rhs, is_sub=True)
                self._sync_flags_to_state(builder)
                self.last_test_val = None

            elif m == "test":
                lhs = self._load_operand(builder, insn, ops[0])
                rhs = self._load_operand(builder, insn, ops[1], target_type=lhs.type)
                self.last_test_val = builder.and_(lhs, rhs)
                self._update_flags_arith(builder, self.last_test_val, lhs, rhs, is_logic=True)
                self._sync_flags_to_state(builder)
                self.last_cmp_lhs = None
                self.last_cmp_rhs = None

            # 5. Conditional Moves (cmovcc)
            elif m.startswith("cmov"):
                pred = self._build_branch_predicate(builder, "j" + m[4:])
                src = self._load_operand(builder, insn, ops[1])
                dst = self._load_operand(builder, insn, ops[0])
                if src.type != dst.type:
                    src = builder.zext(src, dst.type) if src.type.width < dst.type.width else builder.trunc(src, dst.type)
                val = builder.select(pred, src, dst)
                self._store_operand(builder, insn, ops[0], val)

            # 6. Conditional Sets (setcc)
            elif m.startswith("set"):
                pred = self._build_branch_predicate(builder, "j" + m[3:])
                byte_val = builder.zext(pred, self.i8)
                self._store_operand(builder, insn, ops[0], byte_val)

            # 7. Conditional Branches
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

            # 8. Unconditional Jumps
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
                    default_bb = self.fn.append_basic_block(name=f"disp_fallback_{hex(insn.address)[2:]}")
                    sw = builder.switch(target_vaddr_val, default_bb)
                    for b_addr, b_block in block_map.items():
                        sw.add_case(ir.Constant(self.i64, b_addr), b_block)
                    builder.position_at_end(default_bb)
                    builder.call(self.dispatch_fn, [self.state_arg, target_vaddr_val])
                    builder.ret_void()

            # 9. Function Calls
            elif m == "call":
                # Push return address to guest stack
                rsp = self._load_gpr(builder, "rsp")
                new_rsp = builder.sub(rsp, ir.Constant(self.i64, 8))
                self._store_gpr(builder, "rsp", new_rsp)
                ret_addr = ir.Constant(self.i64, insn.address + insn.size)
                ptr = self._get_host_ptr(builder, new_rsp, self.i64)
                builder.store(ret_addr, ptr)

                if ops[0].type == capstone.x86.X86_OP_IMM:
                    target_vaddr = ops[0].imm
                    self._emit_call_or_jump(builder, target_vaddr, is_call=True)
                else:
                    target_vaddr_val = self._load_operand(builder, insn, ops[0])
                    builder.call(self.dispatch_fn, [self.state_arg, target_vaddr_val])

            # 10. Function Return
            elif m in ("ret", "retf"):
                # Pop return address from guest stack
                rsp = self._load_gpr(builder, "rsp")
                new_rsp = builder.add(rsp, ir.Constant(self.i64, 8))
                self._store_gpr(builder, "rsp", new_rsp)
                builder.ret_void()

            # 11. Stack Push / Pop
            elif m == "push":
                val = self._load_operand(builder, insn, ops[0])
                if val.type != self.i64:
                    val = builder.zext(val, self.i64) if val.type.width < 64 else builder.trunc(val, self.i64)
                rsp = self._load_gpr(builder, "rsp")
                new_rsp = builder.sub(rsp, ir.Constant(self.i64, 8))
                self._store_gpr(builder, "rsp", new_rsp)
                ptr = self._get_host_ptr(builder, new_rsp, self.i64)
                builder.store(val, ptr)

            elif m == "pop":
                rsp = self._load_gpr(builder, "rsp")
                ptr = self._get_host_ptr(builder, rsp, self.i64)
                val = builder.load(ptr, name="pop_val")
                new_rsp = builder.add(rsp, ir.Constant(self.i64, 8))
                self._store_gpr(builder, "rsp", new_rsp)
                self._store_operand(builder, insn, ops[0], val)

            # 12. Vector / SSE Operations
            elif m in ("movaps", "movups", "movapd", "movupd", "movdqa", "movdqu"):
                val = self._load_operand(builder, insn, ops[1], target_type=self.v4f32)
                self._store_operand(builder, insn, ops[0], val)

            elif m in ("movss", "movsd"):
                t = self.f32 if m == "movss" else self.f64
                if ops[0].type == capstone.x86.X86_OP_REG and insn.reg_name(ops[0].reg).lower().startswith("xmm"):
                    if ops[1].type == capstone.x86.X86_OP_MEM:
                        # Memory to XMM: load scalar, zero upper elements
                        s_val = self._load_operand(builder, insn, ops[1], target_type=t)
                        if m == "movss":
                            zero_v = ir.Constant(self.v4f32, [ir.Constant(self.f32, 0.0)] * 4)
                        else:
                            zero_v = ir.Constant(self.v2f64, [ir.Constant(self.f64, 0.0)] * 2)
                        res = builder.insert_element(zero_v, s_val, ir.Constant(self.i32, 0))
                        self._store_operand(builder, insn, ops[0], res)
                    else:
                        # XMM to XMM: copy low element, preserve upper elements
                        s_val = self._load_operand(builder, insn, ops[1], target_type=t)
                        vec_t = self.v4f32 if m == "movss" else self.v2f64
                        d_v = self._load_operand(builder, insn, ops[0], target_type=vec_t)
                        res = builder.insert_element(d_v, s_val, ir.Constant(self.i32, 0))
                        self._store_operand(builder, insn, ops[0], res)
                else:
                    # XMM to Memory
                    val = self._load_operand(builder, insn, ops[1], target_type=t)
                    self._store_operand(builder, insn, ops[0], val)

            elif m == "unpcklps":
                lhs = self._load_operand(builder, insn, ops[0], target_type=self.v4f32)
                rhs = self._load_operand(builder, insn, ops[1], target_type=self.v4f32)
                mask = ir.Constant(ir.VectorType(self.i32, 4), [0, 4, 1, 5])
                res = builder.shuffle_vector(lhs, rhs, mask)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "unpckhpd":
                lhs = self._load_operand(builder, insn, ops[0], target_type=self.v2f64)
                rhs = self._load_operand(builder, insn, ops[1], target_type=self.v2f64)
                mask = ir.Constant(ir.VectorType(self.i32, 2), [1, 3])
                res = builder.shuffle_vector(lhs, rhs, mask)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "movlhps":
                lhs = self._load_operand(builder, insn, ops[0], target_type=self.v4f32)
                rhs = self._load_operand(builder, insn, ops[1], target_type=self.v4f32)
                mask = ir.Constant(ir.VectorType(self.i32, 4), [0, 1, 4, 5])
                res = builder.shuffle_vector(lhs, rhs, mask)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "shufps":
                lhs = self._load_operand(builder, insn, ops[0], target_type=self.v4f32)
                rhs = self._load_operand(builder, insn, ops[1], target_type=self.v4f32)
                imm = ops[2].imm if len(ops) > 2 else 0
                i0 = imm & 3
                i1 = (imm >> 2) & 3
                i2 = 4 + ((imm >> 4) & 3)
                i3 = 4 + ((imm >> 6) & 3)
                mask = ir.Constant(ir.VectorType(self.i32, 4), [i0, i1, i2, i3])
                res = builder.shuffle_vector(lhs, rhs, mask)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "pshufd":
                src = self._load_operand(builder, insn, ops[1], target_type=self.v4i32)
                imm = ops[2].imm if len(ops) > 2 else 0
                i0 = imm & 3
                i1 = (imm >> 2) & 3
                i2 = (imm >> 4) & 3
                i3 = (imm >> 6) & 3
                mask = ir.Constant(ir.VectorType(self.i32, 4), [i0, i1, i2, i3])
                res = builder.shuffle_vector(src, src, mask)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "punpckldq":
                lhs = self._load_operand(builder, insn, ops[0], target_type=self.v4i32)
                rhs = self._load_operand(builder, insn, ops[1], target_type=self.v4i32)
                mask = ir.Constant(ir.VectorType(self.i32, 4), [0, 4, 1, 5])
                res = builder.shuffle_vector(lhs, rhs, mask)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "movd":
                if ops[0].type == capstone.x86.X86_OP_REG and insn.reg_name(ops[0].reg).lower().startswith("xmm"):
                    src_val = self._load_operand(builder, insn, ops[1], target_type=self.i32)
                    zero_vec = ir.Constant(self.v4i32, [ir.Constant(self.i32, 0)] * 4)
                    res = builder.insert_element(zero_vec, src_val, ir.Constant(self.i32, 0))
                    self._store_operand(builder, insn, ops[0], res)
                else:
                    src_vec = self._load_operand(builder, insn, ops[1], target_type=self.v4i32)
                    res = builder.extract_element(src_vec, ir.Constant(self.i32, 0))
                    self._store_operand(builder, insn, ops[0], res)

            elif m == "movq":
                dst_name = insn.reg_name(ops[0].reg).lower() if ops[0].type == capstone.x86.X86_OP_REG else ""
                src_name = insn.reg_name(ops[1].reg).lower() if ops[1].type == capstone.x86.X86_OP_REG else ""
                if dst_name.startswith("xmm"):
                    if src_name.startswith("xmm"):
                        src_v2 = self._load_operand(builder, insn, ops[1], target_type=self.v2i64)
                        e0 = builder.extract_element(src_v2, ir.Constant(self.i32, 0))
                        zero_v2 = ir.Constant(self.v2i64, [ir.Constant(self.i64, 0)] * 2)
                        res = builder.insert_element(zero_v2, e0, ir.Constant(self.i32, 0))
                        self._store_operand(builder, insn, ops[0], res)
                    else:
                        src_val = self._load_operand(builder, insn, ops[1], target_type=self.i64)
                        zero_v2 = ir.Constant(self.v2i64, [ir.Constant(self.i64, 0)] * 2)
                        res = builder.insert_element(zero_v2, src_val, ir.Constant(self.i32, 0))
                        self._store_operand(builder, insn, ops[0], res)
                elif src_name.startswith("xmm"):
                    src_v2 = self._load_operand(builder, insn, ops[1], target_type=self.v2i64)
                    res = builder.extract_element(src_v2, ir.Constant(self.i32, 0))
                    self._store_operand(builder, insn, ops[0], res)
                else:
                    val = self._load_operand(builder, insn, ops[1], target_type=self.i64)
                    self._store_operand(builder, insn, ops[0], val)

            elif m == "paddq":
                lhs = self._load_operand(builder, insn, ops[0], target_type=self.v2i64)
                rhs = self._load_operand(builder, insn, ops[1], target_type=self.v2i64)
                res = builder.add(lhs, rhs)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "pcmpgtd":
                lhs = self._load_operand(builder, insn, ops[0], target_type=self.v4i32)
                rhs = self._load_operand(builder, insn, ops[1], target_type=self.v4i32)
                cmp = builder.icmp_signed(">", lhs, rhs)
                res = builder.sext(cmp, self.v4i32)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "psllq":
                lhs = self._load_operand(builder, insn, ops[0], target_type=self.v2i64)
                shift_imm = ops[1].imm if ops[1].type == capstone.x86.X86_OP_IMM else 0
                shift_vec = ir.Constant(self.v2i64, [ir.Constant(self.i64, shift_imm), ir.Constant(self.i64, shift_imm)])
                res = builder.shl(lhs, shift_vec)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "cvtdq2pd":
                src = self._load_operand(builder, insn, ops[1], target_type=self.v4i32)
                e0 = builder.extract_element(src, ir.Constant(self.i32, 0))
                e1 = builder.extract_element(src, ir.Constant(self.i32, 1))
                f0 = builder.sitofp(e0, self.f64)
                f1 = builder.sitofp(e1, self.f64)
                zero_v2 = ir.Constant(self.v2f64, [ir.Constant(self.f64, 0.0)] * 2)
                v_tmp = builder.insert_element(zero_v2, f0, ir.Constant(self.i32, 0))
                res = builder.insert_element(v_tmp, f1, ir.Constant(self.i32, 1))
                self._store_operand(builder, insn, ops[0], res)

            elif m in ("xorps", "xorpd"):
                if ops[0].type == capstone.x86.X86_OP_REG and ops[1].type == capstone.x86.X86_OP_REG and ops[0].reg == ops[1].reg:
                    # Self-XOR = zero register
                    elem_t = self.f32 if m == "xorps" else self.f64
                    vec_t = self.v4f32 if m == "xorps" else self.v2f64
                    count = 4 if m == "xorps" else 2
                    zero = ir.Constant(vec_t, [ir.Constant(elem_t, 0.0)] * count)
                    self._store_operand(builder, insn, ops[0], zero)
                else:
                    lhs = self._load_operand(builder, insn, ops[0], target_type=self.v4i32 if m == "xorps" else self.v2i64)
                    rhs = self._load_operand(builder, insn, ops[1], target_type=self.v4i32 if m == "xorps" else self.v2i64)
                    res = builder.xor(lhs, rhs)
                    self._store_operand(builder, insn, ops[0], res)

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

            # 13. Scalar Floats & Conversions
            elif m == "addss":
                lhs = self._load_operand(builder, insn, ops[0], target_type=self.f32)
                rhs = self._load_operand(builder, insn, ops[1], target_type=self.f32)
                res = builder.fadd(lhs, rhs)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "subss":
                lhs = self._load_operand(builder, insn, ops[0], target_type=self.f32)
                rhs = self._load_operand(builder, insn, ops[1], target_type=self.f32)
                res = builder.fsub(lhs, rhs)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "mulss":
                lhs = self._load_operand(builder, insn, ops[0], target_type=self.f32)
                rhs = self._load_operand(builder, insn, ops[1], target_type=self.f32)
                res = builder.fmul(lhs, rhs)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "divss":
                lhs = self._load_operand(builder, insn, ops[0], target_type=self.f32)
                rhs = self._load_operand(builder, insn, ops[1], target_type=self.f32)
                res = builder.fdiv(lhs, rhs)
                self._store_operand(builder, insn, ops[0], res)

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

            elif m in ("ucomisd", "ucomiss"):
                t = self.f64 if m == "ucomisd" else self.f32
                lhs = self._load_operand(builder, insn, ops[0], target_type=t)
                rhs = self._load_operand(builder, insn, ops[1], target_type=t)
                eq = builder.fcmp_ordered("==", lhs, rhs)
                lt = builder.fcmp_ordered("<", lhs, rhs)
                uno = builder.fcmp_unordered("uno", lhs, rhs)
                zf = builder.or_(eq, uno)
                cf = builder.or_(lt, uno)
                builder.store(zf, self.ptr_zf)
                builder.store(cf, self.ptr_cf)
                builder.store(ir.Constant(self.i1, 0), self.ptr_sf)
                builder.store(ir.Constant(self.i1, 0), self.ptr_of)
                self._sync_flags_to_state(builder)

            elif m == "cvtss2sd":
                src = self._load_operand(builder, insn, ops[1], target_type=self.f32)
                res = builder.fpext(src, self.f64)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "cvtsd2ss":
                src = self._load_operand(builder, insn, ops[1], target_type=self.f64)
                res = builder.fptrunc(src, self.f32)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "cvtsi2sd":
                src = self._load_operand(builder, insn, ops[1], target_type=self.i64)
                res = builder.sitofp(src, self.f64)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "cvtsi2ss":
                src = self._load_operand(builder, insn, ops[1], target_type=self.i32)
                res = builder.sitofp(src, self.f32)
                self._store_operand(builder, insn, ops[0], res)

            elif m == "cvttsd2si":
                src = self._load_operand(builder, insn, ops[1], target_type=self.f64)
                dst_reg = insn.reg_name(ops[0].reg).lower() if ops[0].type == capstone.x86.X86_OP_REG else None
                dst_width = REG_WIDTHS.get(dst_reg, 64) if dst_reg else 64
                res = builder.fptosi(src, ir.IntType(dst_width))
                self._store_operand(builder, insn, ops[0], res)

            elif m == "cvttss2si":
                src = self._load_operand(builder, insn, ops[1], target_type=self.f32)
                dst_reg = insn.reg_name(ops[0].reg).lower() if ops[0].type == capstone.x86.X86_OP_REG else None
                dst_width = REG_WIDTHS.get(dst_reg, 64) if dst_reg else 64
                res = builder.fptosi(src, ir.IntType(dst_width))
                self._store_operand(builder, insn, ops[0], res)

            # 14. Atomics
            elif m == "xadd":
                vaddr = self._resolve_mem_addr(builder, ops[0], insn.address, insn.size)
                width = ops[0].size * 8 if ops[0].type == capstone.x86.X86_OP_MEM else 64
                op_type = ir.IntType(width)
                ptr = self._get_host_ptr(builder, vaddr, op_type)
                add_val = self._load_operand(builder, insn, ops[1], target_type=op_type)
                old_val = builder.atomic_rmw("add", ptr, add_val, ordering="seq_cst")
                self._store_operand(builder, insn, ops[1], old_val)
                res = builder.add(old_val, add_val)
                self._update_flags_arith(builder, res, old_val, add_val)

            elif m == "cmpxchg":
                vaddr = self._resolve_mem_addr(builder, ops[0], insn.address, insn.size)
                width = ops[0].size * 8 if ops[0].type == capstone.x86.X86_OP_MEM else 64
                op_type = ir.IntType(width)
                ptr = self._get_host_ptr(builder, vaddr, op_type)
                expected = self._load_gpr(builder, "rax" if width == 64 else ("eax" if width == 32 else "ax"))
                if expected.type != op_type:
                    expected = builder.trunc(expected, op_type) if expected.type.width > width else builder.zext(expected, op_type)
                new_val = self._load_operand(builder, insn, ops[1], target_type=op_type)
                pair = builder.cmpxchg(ptr, expected, new_val, ordering="seq_cst", failordering="seq_cst")
                loaded_val = builder.extract_value(pair, 0)
                success = builder.extract_value(pair, 1)
                self._store_gpr(builder, "rax" if width == 64 else "eax", loaded_val)
                builder.store(success, self.ptr_zf)
                builder.store(ir.Constant(self.i1, 0), self.ptr_sf)
                builder.store(ir.Constant(self.i1, 0), self.ptr_cf)
                builder.store(ir.Constant(self.i1, 0), self.ptr_of)
                self._sync_flags_to_state(builder)

            elif m == "xchg":
                if ops[0].type == capstone.x86.X86_OP_MEM:
                    vaddr = self._resolve_mem_addr(builder, ops[0], insn.address, insn.size)
                    width = ops[0].size * 8
                    op_type = ir.IntType(width)
                    ptr = self._get_host_ptr(builder, vaddr, op_type)
                    reg_val = self._load_operand(builder, insn, ops[1], target_type=op_type)
                    old_mem = builder.atomic_rmw("xchg", ptr, reg_val, ordering="seq_cst")
                    self._store_operand(builder, insn, ops[1], old_mem)
                elif ops[1].type == capstone.x86.X86_OP_MEM:
                    vaddr = self._resolve_mem_addr(builder, ops[1], insn.address, insn.size)
                    width = ops[1].size * 8
                    op_type = ir.IntType(width)
                    ptr = self._get_host_ptr(builder, vaddr, op_type)
                    reg_val = self._load_operand(builder, insn, ops[0], target_type=op_type)
                    old_mem = builder.atomic_rmw("xchg", ptr, reg_val, ordering="seq_cst")
                    self._store_operand(builder, insn, ops[0], old_mem)
                else:
                    val0 = self._load_operand(builder, insn, ops[0])
                    val1 = self._load_operand(builder, insn, ops[1], target_type=val0.type)
                    self._store_operand(builder, insn, ops[0], val1)
                    self._store_operand(builder, insn, ops[1], val0)

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
        """Constructs boolean condition for branch, cmov, and set instructions using local SSA flag slots"""
        cond = mnemonic.lower()
        if cond.startswith("j") or cond.startswith("set"):
            cond = cond[1:] if cond.startswith("j") else cond[3:]
        elif cond.startswith("cmov"):
            cond = cond[4:]

        # Flag-based evaluation loaded from local alloca slots
        zf = builder.load(self.ptr_zf, name="cur_zf")
        sf = builder.load(self.ptr_sf, name="cur_sf")
        cf = builder.load(self.ptr_cf, name="cur_cf")
        of = builder.load(self.ptr_of, name="cur_of")

        if cond in ("e", "z"):
            return zf
        elif cond in ("ne", "nz"):
            return builder.not_(zf)
        elif cond == "s":
            return sf
        elif cond == "ns":
            return builder.not_(sf)
        elif cond in ("b", "c"):
            return cf
        elif cond in ("ae", "nc", "nb"):
            return builder.not_(cf)
        elif cond in ("be", "na"):
            return builder.or_(cf, zf)
        elif cond in ("a", "nbe"):
            return builder.and_(builder.not_(cf), builder.not_(zf))
        elif cond == "l":
            return builder.xor(sf, of)
        elif cond == "ge":
            return builder.not_(builder.xor(sf, of))
        elif cond == "le":
            return builder.or_(zf, builder.xor(sf, of))
        elif cond == "g":
            return builder.and_(builder.not_(zf), builder.not_(builder.xor(sf, of)))
        elif cond in ("np", "po"):
            return ir.Constant(self.i1, 1)
        elif cond in ("p", "pe"):
            return ir.Constant(self.i1, 0)

        return ir.Constant(self.i1, 1)

    def _emit_call_or_jump(self, builder: ir.IRBuilder, target_vaddr: int, is_call: bool):
        target_fn_name = f"bbr_{hex(target_vaddr)[2:]}"
        try:
            target_fn = self.module.get_global(target_fn_name)
        except KeyError:
            target_fn = ir.Function(self.module, self.fn_type, name=target_fn_name)

        builder.call(target_fn, [self.state_arg])
