# Copyright 2025 Tobias Senti

from enum import Enum
from bgpu_util import hex_to_float

class OperandType(Enum):
    REGISTER = 0
    INT_IMMEDIATE = 1
    FLOAT_IMMEDIATE = 2
    SPECIAL = 3

class Operand:
    def __init__(self, value: str):
        self.type = None
        if value.startswith('r'):
            self.type = OperandType.REGISTER
            assert value[1:].isdigit(), f"Invalid register format: {value}"
            self.register = int(value[1:])
            assert 0 <= self.register <= 255, f"Register out of range: {self.register}"
        elif value.endswith('U') and (value[:-1].isdigit() or (value[:-1].startswith('-') and value[1:-1].isdigit())):
            self.type = OperandType.INT_IMMEDIATE
            self.immediate = int(value[:-1])
        elif value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
            self.type = OperandType.INT_IMMEDIATE
            self.immediate = int(value)
        elif '.' in value:
            self.type = OperandType.FLOAT_IMMEDIATE
            self.immediate = float(value)
        elif value.startswith('0f'):
            self.type = OperandType.FLOAT_IMMEDIATE
            self.immediate = hex_to_float(int(value[2:], 16))
        elif value.startswith('%'):
            self.type = OperandType.SPECIAL
            self.special = value[1:]
        else:
            assert False, f"Unknown operand format: {value}"

    def __str__(self):
        if self.type == OperandType.REGISTER:
            return f"r{self.register}"
        elif self.type == OperandType.INT_IMMEDIATE:
            return str(self.immediate)
        elif self.type == OperandType.FLOAT_IMMEDIATE:
            return str(self.immediate)
        elif self.type == OperandType.SPECIAL:
            return f"%{self.special}"
        else:
            assert False, f"Cannot stringify operand of type {self.type}"

class ModifierType(Enum):
    IDTYPE = 0
    REGISTER_REGISTER = 1
    REGISTER_IMMEDIATE = 2
    MEMORY_TYPE = 3
    CONDITION = 4
    LABEL = 5
    FDTYPE = 6
    BDTYPE = 7
    SYNC_DOMAIN = 8

class Modifier:
    def __init__(self, value: str):
        self.value = value
        if value in ["int32", "uint32", "int16", "uint16", "int8", "uint8", "long"]:
            self.type = ModifierType.IDTYPE
        elif value in ["float32"]:
            self.type = ModifierType.FDTYPE
        elif value == "rr":
            self.type = ModifierType.REGISTER_REGISTER
        elif value == "ri":
            self.type = ModifierType.REGISTER_IMMEDIATE
        elif value in ["global", "param"]:
            self.type = ModifierType.MEMORY_TYPE
        elif value in ["ez", "nz"]:
            self.type = ModifierType.CONDITION
        elif value == "bool":
            self.type = ModifierType.BDTYPE
        elif value in ['threads']:
            self.type = ModifierType.SYNC_DOMAIN
        else:
            self.type = ModifierType.LABEL

    def get_dtype_width(self) -> int:
        if self.value == "int32" or self.value == "float32" or self.value == "uint32" or self.value == "long":
            return 4
        elif self.value == "int16" or self.value == "uint16":
            return 2
        elif self.value == "int8" or self.value == "uint8":
            return 1
        else:
            assert False, f"Unknown data type modifier: {self.value}"

class ParsedInstruction:
    def __init__(self, instruction: str, modifiers: list[Modifier], operands: list[Operand], source_line: str, label: str = None):
        self.instruction = instruction
        self.operands = operands
        self.modifiers = modifiers
        self.source_line = source_line
        self.label = label
        self.addr = None  # to be filled in later during assembly

    def __str__(self):
        mods = '.'.join([mod.value for mod in self.modifiers])
        ops = ', '.join([str(op) for op in self.operands])
        string = f"{self.instruction}{'.' if len(mods) > 0 else ''}{mods} {ops} // {self.source_line}"
        if self.label is not None:
            string = f"// {self.label}:\n" + string
        return string

    def has_modifier(self, mod_type: ModifierType) -> bool:
        for mod in self.modifiers:
            if mod.type == mod_type:
                return True
        return False

    def find_modifiers(self, mod_type: ModifierType) -> list[Modifier]:
        mods = []
        for mod in self.modifiers:
            if mod.type == mod_type:
                mods.append(mod)
        return mods

    def get_condition_modifiers(self) -> list[Modifier]:
        return self.find_modifiers(ModifierType.CONDITION)

    def get_label_modifiers(self) -> list[Modifier]:
        return self.find_modifiers(ModifierType.LABEL)

    def get_dtype_modifiers(self) -> list[Modifier]:
        return self.find_modifiers(ModifierType.IDTYPE) + self.find_modifiers(ModifierType.FDTYPE) + self.find_modifiers(ModifierType.BDTYPE)

    def is_ri(self) -> bool:
        for mod in self.modifiers:
            if mod.type == ModifierType.REGISTER_IMMEDIATE:
                return True
        return False

    def is_rr(self) -> bool:
        for mod in self.modifiers:
            if mod.type == ModifierType.REGISTER_REGISTER:
                return True
        return False
