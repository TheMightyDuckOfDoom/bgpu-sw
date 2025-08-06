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

    LDI = 0x0B
    ADDI = 0x0C
    SUBI = 0x0D
    SHLI = 0x0E

    STOP = 0b111111

class LSUSubtype(Enum):
    LOAD_BYTE = 0x00
    LOAD_HALF = 0x01
    LOAD_WORD = 0x02

    STORE_BYTE = 0x03
    STORE_HALF = 0x04
    STORE_WORD = 0x05

class EU(Enum):
    IU  = 0
    LSU = 1
    BRU = 2
    STOP = 3

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
               {"%param": IUSubtype.DPA, "%gidx0": IUSubtype.BID, "%lidx0": IUSubtype.TID}[op2] if op2 in {"%param", "%gidx0", "%lidx0"} else None)
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
            self.op2 = dst
            self.op1 = op2
        else:
            self.op1 = op1
            self.op2 = op2
        self.subtype = None

        if len(opcode.value) > 2:
            if callable(opcode.value[2]):
                self.subtype = opcode.value[2](op1, op2, width, is_ri) 
            else:
                self.subtype = opcode.value[2]

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
            else:
                assert int(self.op1) >= 0, f"Immediate value must be non-negative: {self.op1}"
                assert int(self.op1) < 256, f"Immediate value must be less than 256: {self.op1}"
                enc |= int(self.op1) & 0xFF  # Ensure it fits in

        return f"{enc:08x}"
