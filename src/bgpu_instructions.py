from enum import Enum

class IUSubtype(Enum):
    TID = 0x00
    WID = 0x01
    BID = 0x02
    TBID = 0x03

    ADD = 0x04
    SUB = 0x05
    AND = 0x06
    OR = 0x07
    XOR = 0x08
    SHL = 0x09
    SHR = 0x0A
    MUL = 0x0B

    LDI = 0x0C
    ADDI = 0x0D
    SUBI = 0x0E
    ANDI = 0x1F
    ORI = 0x10
    XORI = 0x11
    SHLI = 0x12
    SHRI = 0x13
    MULI = 0x14

    CMPLT = 0x15
    CMPLTI = 0x16
    CMPNE = 0x17
    CMPNEI = 0x18

    MAX = 0x19
    DIV = 0x1A
    DIVI = 0x1B

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
    FCMPLT = 0x07
    FDIV = 0x08
    FCAST_FROM_INT = 0x09
    FCAST_TO_INT = 0x0A

class BRUSubtype(Enum):
    BRNZ = 0x00
    BRZ = 0x01
    SYNC_THREADS = 0x02
    JMP = 0x03
    STOP = 0b111111

class EU(Enum):
    IU  = 0
    LSU = 1
    BRU = 2
    FPU = 3
