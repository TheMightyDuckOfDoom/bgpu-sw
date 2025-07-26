#!/usr/bin/env python3

from enum import Enum

class IUSubtype(Enum):
    TID = 0x00,
    WID = 0x01,
    BID = 0x02,
    TBID = 0x03,
    DPA = 0x04,

    ADD = 0x05,
    SUB = 0x06,
    AND = 0x07,
    OR = 0x08,
    XOR = 0x09,
    SHL = 0x0A,

    LDI = 0x0B,
    ADDI = 0x0C,
    SUBI = 0x0D,
    SHLI = 0x0E,

    STOP = 0b111111

class LSUSubtype(Enum):
    LOAD_BYTE = 0x00,
    LOAD_HALF = 0x01,
    LOAD_WORD = 0x02,

    STORE_BYTE = 0x03,
    STORE_HALF = 0x04,
    STORE_WORD = 0x05,

class EU(Enum):
    IU  = 0,
    LSU = 1,
    BRU = 2,
    STOP = 3,

class Instruction:
    def __init__(self, opcode: str, eu: EU, subtype):
        self.opcode = opcode
        self.eu = eu
        self.subtype = subtype

def get_load_store_subtype(op1, op2, width, normal):
    if width == "int32" or width == "uint32":
        return normal[32]
    elif width == "int16" or width == "uint16":
        return normal[16]
    elif width == "int8" or width == "uint8":
        return normal[8]
    else:
        raise ValueError(f"Invalid width: {width}. Expected one of: int32, uint32, int16, uint16, int8, uint8. Got: {width}")

class OpCode(Enum):
    SPECIAL = ("special", EU.IU, lambda op1, op2, width, is_ri: 
               {"%param": IUSubtype.DPA, "%gidx0": IUSubtype.BID, "%lidx0": IUSubtype.TID}[op1] if op1 in {"%param", "%gidx0", "%lidx0"} else None)
    LD = ("ld", EU.LSU, lambda op1, op2, width, is_ri:
            get_load_store_subtype(op1, op2, width, {
                32: LSUSubtype.LOAD_WORD,
                16: LSUSubtype.LOAD_HALF,
                8: LSUSubtype.LOAD_BYTE
            }) if not is_ri else None)
    ST = ("st", EU.LSU, lambda op1, op2, width, is_ri:
            get_load_store_subtype(op1, op2, width, {
                32: LSUSubtype.STORE_WORD,
                16: LSUSubtype.STORE_HALF,
                8: LSUSubtype.STORE_BYTE
            }) if not is_ri else None)
    ADD = ("add", EU.IU, lambda op1, op2, width, is_ri: IUSubtype.ADDI if is_ri else IUSubtype.ADD)
    SHL = ("shl", EU.IU, lambda op1, op2, width, is_ri: IUSubtype.SHLI if is_ri else IUSubtype.SHL)
    STOP = ("stop", EU.STOP, IUSubtype.STOP)

class Instruction:
    def __init__(self, opcode: OpCode, dst: str, op1, op2, width, is_ri):
        self.text = opcode.value[0]
        self.eu = opcode.value[1]
        self.dst = dst
        if opcode == OpCode.ST:
            self.op1 = dst # In store instructions, dst is actually the source
            self.op2 = op1
        else:
            self.op1 = op1
            self.op2 = op2
        self.subtype = None

        if len(opcode.value) > 2:
            if callable(opcode.value[2]):
                self.subtype = opcode.value[2](op1, op2, width, is_ri) 
            else:
                self.subtype = opcode.value[2]

        if dst != "":
            assert dst.startswith("r"), f"Destination register must start with 'r': {dst}"
            assert dst[1:].isdigit(), f"Invalid destination register: {dst}"

    def __str__(self):
        return f"{self.text} {self.dst}"

    def encode(self) -> str:
        # Turn instruction into a binary representation
        enc = 0
        enc |= int(self.eu.value[0]) << 30
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
        if self.op1 != "" and self.op1.startswith("r"):
            assert self.op1[1:].isdigit(), f"Invalid operand 1 register: {self.op1}"
            assert int(self.op1[1:]) >= 0, f"Operand 1 register must be non-negative: {self.op1}"
            assert int(self.op1[1:]) < 256, f"Operand 1 register must be less than 256: {self.op1}"
            enc |= int(self.op1[1:]) << 8

        # can be a register or an immediate value
        if self.op2 != "" :
            if self.op2.startswith("r"):
                assert int(self.op2[1:]) >= 0, f"Operand 2 register must be non-negative: {self.op2}"
                assert int(self.op2[1:]) < 256, f"Operand 2 register must be less than 256: {self.op2}"
                enc |= int(self.op2[1:])
            else:
                assert int(self.op2) >= 0, f"Immediate value must be non-negative: {self.op2}"
                assert int(self.op2) < 256, f"Immediate value must be less than 256: {self.op2}"
                enc |= int(self.op2) & 0xFF  # Ensure it fits in

        return f"0x{enc:08x}"

def parse_instruction(line: str) -> Instruction:
    print(f"Parsing line: {line.strip()}")
    parts = line.split()
    print(f"Parts: {parts}")
    opcode_str = parts[0].split(".")[0]
    opcode_modifiers = parts[0].split(".")[1:] if "." in parts[0] else []

    dst = parts[1].replace(",", "") if len(parts) > 1 else ""
    op1 = parts[2].replace(",", "") if len(parts) > 2 else ""
    op2 = parts[3].replace(",", "") if len(parts) > 3 else ""

    width = None
    if "int32" in opcode_modifiers:
        width = "int32"
    if "int16" in opcode_modifiers:
        assert width is None, "Cannot specify multiple widths"
        width = "int16"
    if "uint16" in opcode_modifiers:
        assert width is None, "Cannot specify multiple widths"
        width = "uint16"
    if "int8" in opcode_modifiers:
        assert width is None, "Cannot specify multiple widths"
        width = "int8"
    if "uint8" in opcode_modifiers:
        assert width is None, "Cannot specify multiple widths"
        width = "uint8"

    is_ri = False
    if "ri" in opcode_modifiers:
        is_ri = True
        if "rr" in opcode_modifiers:
            raise ValueError("Cannot specify both 'ri' and 'rr' modifiers")

    for opcode in OpCode:
        if opcode_str == opcode.value[0]:
            return Instruction(opcode, dst, op1, op2, width, is_ri)

    raise ValueError(f"Unknown opcode: {opcode_str}") 

def asm2hex(asm_code: str) -> list[str]:
    program = []
    for line in asm_code.splitlines():
        line = line.strip()
        if line == "":
            continue
        inst = parse_instruction(line)
        print(f"Parsed instruction: {inst}")
        program.append(inst)

    for inst in program:
        print(f"Instruction: {inst.encode()} {inst.text}, EU: {inst.eu}, Subtype: {inst.subtype}, Dst: {inst.dst}", end="")
        if inst.op1 != "":
            print(f", Op1: {inst.op1}", end="")
        if inst.op2 != "":
            print(f", Op2: {inst.op2}", end="")
        print()

    return [inst.encode() for inst in program]

example_asm = """
special                   r0, %param
ld.int32.global           r1,   r0
add.ri.int32              r2,   r0, 4
ld.int32.global           r2,   r2
add.ri.int32              r0,   r0, 8
ld.int32.global           r0,   r0
special                   r3, %gidx0
special                   r4, %lidx0
shl.ri.int32              r5,   r3,    4
shl.ri.int32              r6,   r4,    2
add.rr.int32              r5,   r5,   r6
add.rr.int32              r6,   r2,   r5
ld.int32.global           r6,   r6
add.rr.int32              r7,   r0,   r5
ld.int32.global           r7,   r7
add.ri.int32              r8,   r5,    1
add.rr.int32              r9,   r2,   r8
ld.int32.global           r9,   r9
add.rr.int32             r10,   r0,   r8
ld.int32.global          r10,  r10
add.ri.int32             r11,   r5,    2
add.rr.int32             r12,   r2,  r11
ld.int32.global          r12,  r12
add.rr.int32             r13,   r0,  r11
ld.int32.global          r13,  r13
add.ri.int32             r14,   r5,    3
add.rr.int32              r2,   r2,  r14
ld.int32.global           r2,   r2
add.rr.int32              r0,   r0,  r14
ld.int32.global           r0,   r0
add.rr.int32              r8,   r1,   r8
add.rr.int32             r11,   r1,  r11
add.rr.int32             r14,   r1,  r14
add.rr.int32              r1,   r1,   r5
add.rr.int32              r5,   r9,  r10
st.int32.global           r8,   r5
add.rr.int32              r5,  r12,  r13
st.int32.global          r11,   r5
add.rr.int32              r0,   r2,   r0
st.int32.global          r14,   r0
add.rr.int32              r0,   r6,   r7
st.int32.global           r1,   r0
stop
"""

if __name__ == "__main__":
    print("Assembling example ASM code...")
    hex_program = asm2hex(example_asm)
    print("Hex program:")
    for line in hex_program:
        print(line)
    print("Done.")