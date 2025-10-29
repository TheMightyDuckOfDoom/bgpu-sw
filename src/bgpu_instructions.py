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
    MUL = 0x0C

    LDI = 0x0D
    ADDI = 0x0E
    SUBI = 0x0F
    ANDI = 0x10
    ORI = 0x11
    XORI = 0x12
    SHLI = 0x13
    SHRI = 0x14
    MULI = 0x15

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
    FMAX = 0x03
    FEXP2 = 0x04
    FLOG2 = 0x05
    FRECIP = 0x06

class BRUSubtype(Enum):
    BRNZ = 0x00
    BRZ = 0x01
    STOP = 0b111111

class EU(Enum):
    IU  = 0
    LSU = 1
    BRU = 2
    FPU = 3
