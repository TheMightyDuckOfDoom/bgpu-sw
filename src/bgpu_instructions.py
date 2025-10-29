from enum import Enum

class IUSubtype(Enum):
    TID = 0x00
    WID = 0x01
    BID = 0x02
    TBID = 0x03
    DPA = 0x04

    ADD = 0x05
    SUB = 0x06
    AND = 0x07
    OR = 0x08
    XOR = 0x09
    SHL = 0x0A
    SHR = 0x0B

    LDI = 0x0C
    ADDI = 0x0D
    SUBI = 0x0E
    ANDI = 0x0F
    ORI = 0x10
    XORI = 0x11
    SHLI = 0x12
    SHRI = 0x13


class LSUSubtype(Enum):
    LOAD_BYTE = 0x00
    LOAD_HALF = 0x01
    LOAD_WORD = 0x02

    STORE_BYTE = 0x03
    STORE_HALF = 0x04
    STORE_WORD = 0x05

    LOAD_PARAM = 0x06

class FPUSubtype(Enum):
    FADD = 0x00
    FSUB = 0x01
    FMUL = 0x02

class BRUSubtype(Enum):
    BRNZ = 0x00
    BRZ = 0x01
    STOP = 0b111111

class EU(Enum):
    IU  = 0
    LSU = 1
    BRU = 2
    FPU = 3

def get_load_store_subtype(op1, op2, width, normal):
    if width == "int32" or width == "uint32" or width == "float32":
        return normal[32]
    elif width == "int16" or width == "uint16":
        return normal[16]
    elif width == "int8" or width == "uint8":
        return normal[8]
    else:
        raise ValueError(f"Invalid width: {width}. Expected one of: int32, uint32, int16, uint16, int8, uint8. Got: {width}")

fpu_types = ["float32"]

class OpCode(Enum):
    SPECIAL = ("special", lambda op1, op2, width, is_ri, mod: 
               (EU.IU, {"%param": IUSubtype.DPA, "%g": IUSubtype.BID, "%l": IUSubtype.TID}[op2] if op2 in {"%param", "%g", "%l"} else None))
    LD = ("ld", lambda op1, op2, width, is_ri, mod:
            (EU.LSU, get_load_store_subtype(op1, op2, width, {
                32: LSUSubtype.LOAD_WORD,
                16: LSUSubtype.LOAD_HALF,
                8: LSUSubtype.LOAD_BYTE
            }) if not is_ri else None))
    ST = ("st", lambda op1, op2, width, is_ri, mod:
            (EU.LSU, get_load_store_subtype(op1, op2, width, {
                32: LSUSubtype.STORE_WORD,
                16: LSUSubtype.STORE_HALF,
                8: LSUSubtype.STORE_BYTE
            }) if not is_ri else None))

    LDPARAM = ("ldparam", lambda op1, op2, width, is_ri, mod: (EU.LSU, LSUSubtype.LOAD_PARAM))

    ADD = ("add", lambda op1, op2, width, is_ri, mod: (EU.FPU, FPUSubtype.FADD) if width in fpu_types else (EU.IU, IUSubtype.ADDI if is_ri else IUSubtype.ADD))
    SUB = ("sub", lambda op1, op2, width, is_ri, mod: (EU.IU, IUSubtype.SUBI if is_ri else IUSubtype.SUB) if width not in fpu_types else None)
    AND = ("and", lambda op1, op2, width, is_ri, mod: (EU.IU, IUSubtype.ANDI if is_ri else IUSubtype.AND) if width not in fpu_types else None)
    OR  = ("or", lambda op1, op2, width, is_ri, mod: (EU.IU, IUSubtype.ORI if is_ri else IUSubtype.OR) if width not in fpu_types else None)
    XOR = ("xor", lambda op1, op2, width, is_ri, mod: (EU.IU, IUSubtype.XORI if is_ri else IUSubtype.XOR) if width not in fpu_types else None)
    SHL = ("shl", lambda op1, op2, width, is_ri, mod: (EU.IU, IUSubtype.SHLI if is_ri else IUSubtype.SHL) if width not in fpu_types else None)
    SHR = ("shr", lambda op1, op2, width, is_ri, mod: (EU.IU, IUSubtype.SHRI if is_ri else IUSubtype.SHR) if width not in fpu_types else None)
    MOV = ("mov", lambda op1, op2, width, is_ri, mod: (EU.IU, IUSubtype.LDI if is_ri else IUSubtype.ADDI))

    MUL = ("mul", lambda op1, op2, width, is_ri, mod: (EU.FPU, FPUSubtype.FMUL))

    STOP = ("stop", lambda op1, op2, width, is_ri, mod: (EU.BRU, BRUSubtype.STOP))

    BR = ("br", lambda op1, op2, width, is_ri, mod: (EU.BRU, BRUSubtype.BRNZ if "nz" in mod else BRUSubtype.BRZ))


class Instruction:
    def __init__(self, opcode: OpCode, dst: str, op1, op2, width, is_ri, modifiers):
        self.text = opcode.value[0]
        self.dst = dst
        if opcode == OpCode.ST:
            self.op2 = dst
            self.op1 = op2
        elif opcode == OpCode.LDPARAM or (opcode == OpCode.MOV and is_ri):
            self.op1 = op2
            self.op2 = op2
        else:
            self.op1 = op1
            self.op2 = op2
        self.modifiers = modifiers
        self.width = width

        eu_subtype = opcode.value[1](op1, op2, width, is_ri, modifiers)
        assert eu_subtype is not None, f"Invalid opcode: {opcode.value[0]} with operands {op1}, {op2} and width {width}"
        self.eu, self.subtype = eu_subtype
        print(f"Computed EU: {self.eu}, Subtype: {self.subtype} for opcode {self.text}")

        assert self.subtype is not None, f"Invalid opcode: {opcode.value[0]} with operands {op1}, {op2} and width {width}"

        if dst != "":
            assert dst.startswith("r"), f"Destination register must start with 'r': {dst}"
            assert dst[1:].isdigit(), f"Invalid destination register: {dst}"

    def __str__(self):
        return f"{self.text} {self.dst}"

    def encode(self) -> str:
        # Turn instruction into a binary representation
        enc = 0
        enc |= int(self.eu.value) << 30
        if isinstance(self.subtype.value, tuple):
            enc |= int(self.subtype.value[0]) << 24
        else:
            enc |= int(self.subtype.value) << 24

        if self.dst != "":
            assert self.dst.startswith("r"), f"Destination register must start with 'r': {self.dst}"
            assert int(self.dst[1:]) >= 0, f"Destination register must be non-negative: {self.dst}"
            assert int(self.dst[1:]) < 256, f"Destination register must be less than 256: {self.dst}"
            enc |= int(self.dst[1:]) << 16

        # can only be a register
        if self.op2 != "" and self.op2.startswith("r"):
            assert self.op2[1:].isdigit(), f"Invalid operand 1 register: {self.op2}"
            assert int(self.op2[1:]) >= 0, f"Operand 1 register must be non-negative: {self.op2}"
            assert int(self.op2[1:]) < 256, f"Operand 1 register must be less than 256: {self.op2}"
            enc |= int(self.op2[1:]) << 8

        # can be a register or an immediate value
        if self.op1 != "" :
            if self.op1.startswith("r"):
                assert int(self.op1[1:]) >= 0, f"Operand 2 register must be non-negative: {self.op1}"
                assert int(self.op1[1:]) < 256, f"Operand 2 register must be less than 256: {self.op1}"
                enc |= int(self.op1[1:])
            elif 'f' not in self.op1:
                assert int(self.op1) >= 0, f"Immediate value must be non-negative: {self.op1}"
                assert int(self.op1) < 256, f"Immediate value must be less than 256: {self.op1}"
                enc |= int(self.op1) & 0xFF  # Ensure it fits in

        return f"{enc:08x}"
