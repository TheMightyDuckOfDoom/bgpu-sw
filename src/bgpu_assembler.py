from util import ParsedInstruction, ModifierType, Modifier, OperandType, Operand
from parser import Parser
from bgpu_instructions import *
from bgpu_util import float_to_hex

class ValidInstruction:
    def __init__(self, name: str, allowed_modifiers: list[list[ModifierType]], allowed_operands: list[list[OperandType]], enc_fun, transform_function=None):
        self.name = name
        self.allowed_modifiers = allowed_modifiers
        self.allowed_operands = allowed_operands
        self.enc_fun = enc_fun
        self.transform_function = transform_function

    def matches_name(self, name: str) -> bool:
        return self.name == name

    def is_valid(self, parsed_inst: ParsedInstruction) -> bool:
        if parsed_inst.instruction != self.name:
            return False

        found_mod_groups = [0 for _ in self.allowed_modifiers]
        for mod in parsed_inst.modifiers:
            for idx, required_mods in enumerate(self.allowed_modifiers):
                for req_mod_ty in required_mods:
                    if mod.type == req_mod_ty:
                        found_mod_groups[idx] += 1
                        break

        # Check if all required modifier groups are found
        for idx, required_mods in enumerate(self.allowed_modifiers):
            if found_mod_groups[idx] != 1:
                return False
        
        # Check operands
        if len(parsed_inst.operands) != len(self.allowed_operands):
            return False

        for i, op in enumerate(parsed_inst.operands):
            operand_types = self.allowed_operands[i]
            missmatch = False
            if isinstance(operand_types, list):
                if op.type not in operand_types:
                    missmatch = True
            else:
                if op.type != operand_types:
                    missmatch = True

            if missmatch:
                return False

        return True

    def transform(self, parsed_inst: ParsedInstruction) -> ParsedInstruction:
        if self.transform_function is not None:
            transformed = self.transform_function(parsed_inst)
            if transformed is not None:
                return transformed
        return [parsed_inst]

class AssemblerExecutionUnit:
    def get_instructions(self) -> list[ValidInstruction]:
        return self.instructions

    def expand_instruction(self, parsed_inst: ParsedInstruction) -> list[ParsedInstruction]:
        # Check if instruction is valid
        for instr in self.instructions:
            if instr.matches_name(parsed_inst.instruction):
                if instr.is_valid(parsed_inst):
                    expanded = instr.transform(parsed_inst)
                    return expanded
        return []
    
    def encode_instruction(self, parsed_inst: ParsedInstruction) -> int:
        for instr in self.instructions:
            if instr.matches_name(parsed_inst.instruction) and instr.is_valid(parsed_inst):
                encoded = instr.enc_fun(parsed_inst)
                if encoded is not None:
                    return self.eu_enc << 30 | encoded
                else:
                    break
        return None

def encode_dest_reg(reg_operand: Operand) -> int:
    assert reg_operand.type == OperandType.REGISTER, "Destination operand must be a register."
    return (reg_operand.register & 0xFF) << 16

def encode_register(reg_operand: Operand, position: int) -> int:
    assert reg_operand.type == OperandType.REGISTER, "Operand must be a register."
    return (reg_operand.register & 0xFF) << (position * 8)

def encode_subtype(subtype) -> int:
    return (subtype.value & 0x3F) << 24

def encode_large_immediate(op) -> int:
    assert op.type == OperandType.INT_IMMEDIATE, f"Operand must be an integer immediate.: {op}"
    assert 0 <= op.immediate <= (1 << 16), f"Immediate value out of range. {op.immediate}"
    return op.immediate & ((1 << 16) - 1)

def encode_small_immediate(op) -> int:
    assert op.type == OperandType.INT_IMMEDIATE, "Operand must be an integer immediate."
    assert 0 <= op.immediate <= (1 << 8), "Immediate value out of range."
    return (op.immediate & 0xFF)


class AssemblerIntegerUnit(AssemblerExecutionUnit):
    def encode_iu_alu(self, inst: ParsedInstruction, rr_subtype: IUSubtype, ri_subtype: IUSubtype) -> int:
        dest = encode_dest_reg(inst.operands[0])
        src1 = encode_register(inst.operands[1], 1)
        sub = 0
        if inst.is_rr():
            src2 = encode_register(inst.operands[2], 0)
            sub = encode_subtype(rr_subtype)
        else:
            src2 = encode_small_immediate(inst.operands[2])
            sub = encode_subtype(ri_subtype)
        return dest | src1 | src2 | sub

    def encode_special(self, inst: ParsedInstruction) -> int:
        dest = encode_dest_reg(inst.operands[0])
        assert inst.operands[1].type == OperandType.SPECIAL, "Second operand must be a special operand."
        if inst.operands[1].special == "l":
            subtype = IUSubtype.TID
        elif inst.operands[1].special == "g":
            subtype = IUSubtype.BID
        else:
            assert False, f"Unknown special operand: {inst.operands[1].special}"
        return dest | encode_subtype(subtype)

    def expand_mov(self, parsed_inst: ParsedInstruction) -> list[ParsedInstruction]:
        if parsed_inst.is_rr():
            return [ParsedInstruction("add", [Modifier("ri"), Modifier("int32")], parsed_inst.operands[:2] + [Operand(str(0))], parsed_inst.source_line, parsed_inst.label)]

        imm_op = parsed_inst.operands[1]
        dest_reg = parsed_inst.operands[0]

        type_mod = parsed_inst.get_dtype_modifiers()[0]
        if imm_op.type == OperandType.FLOAT_IMMEDIATE:
            imm_op.type = OperandType.INT_IMMEDIATE
            imm_op.immediate = int(float_to_hex(imm_op.immediate), 16)
            type_mod = Modifier("int32")

        # Check if the immediate fits in 16 bits
        if 0 <= imm_op.immediate <= 0xFFFF:
            return None

        # Split into multiple instructions
        inst_mod = [Modifier("ri"), type_mod]
        instructions = []
        upper_value = (imm_op.immediate >> 16) & 0xFFFF
        instructions.append(ParsedInstruction("mov", inst_mod, [dest_reg, Operand(str(upper_value))], parsed_inst.source_line, parsed_inst.label))
        instructions.append(ParsedInstruction("shl", inst_mod, [dest_reg, dest_reg, Operand(str(8))], parsed_inst.source_line))

        next_8_bits = (imm_op.immediate >> 8) & 0xFF
        instructions.append(ParsedInstruction("or", inst_mod, [dest_reg, dest_reg, Operand(str(next_8_bits))], parsed_inst.source_line))
        instructions.append(ParsedInstruction("shl", inst_mod, [dest_reg, dest_reg, Operand(str(8))], parsed_inst.source_line))

        last_8_bits = imm_op.immediate & 0xFF
        instructions.append(ParsedInstruction("or", inst_mod, [dest_reg, dest_reg, Operand(str(last_8_bits))], parsed_inst.source_line))

        return instructions

    def __init__(self):
        self.name = "IU"
        self.eu_enc = 0
        self.instructions = [
            ValidInstruction("mov", [[ModifierType.REGISTER_IMMEDIATE, ModifierType.REGISTER_REGISTER], [ModifierType.IDTYPE, ModifierType.FDTYPE]], [OperandType.REGISTER, [OperandType.REGISTER, OperandType.INT_IMMEDIATE, OperandType.FLOAT_IMMEDIATE]],
                lambda inst: 
                    (encode_dest_reg(inst.operands[0]) | encode_large_immediate(inst.operands[1]) | encode_subtype(IUSubtype.LDI)) if inst.is_ri() else None, lambda inst: self.expand_mov(inst)),
            ValidInstruction("add", [[ModifierType.REGISTER_IMMEDIATE, ModifierType.REGISTER_REGISTER], [ModifierType.IDTYPE]], [OperandType.REGISTER, OperandType.REGISTER, [OperandType.REGISTER, OperandType.INT_IMMEDIATE]], lambda inst: self.encode_iu_alu(inst, IUSubtype.ADD, IUSubtype.ADDI)),
            ValidInstruction("sub", [[ModifierType.REGISTER_IMMEDIATE, ModifierType.REGISTER_REGISTER], [ModifierType.IDTYPE]], [OperandType.REGISTER, OperandType.REGISTER, [OperandType.REGISTER, OperandType.INT_IMMEDIATE]], lambda inst: self.encode_iu_alu(inst, IUSubtype.SUB, IUSubtype.SUBI)),
            ValidInstruction("shl", [[ModifierType.REGISTER_IMMEDIATE, ModifierType.REGISTER_REGISTER], [ModifierType.IDTYPE]], [OperandType.REGISTER, OperandType.REGISTER, [OperandType.REGISTER, OperandType.INT_IMMEDIATE]], lambda inst: self.encode_iu_alu(inst, IUSubtype.SHL, IUSubtype.SHLI)),
            ValidInstruction("shr", [[ModifierType.REGISTER_IMMEDIATE, ModifierType.REGISTER_REGISTER], [ModifierType.IDTYPE]], [OperandType.REGISTER, OperandType.REGISTER, [OperandType.REGISTER, OperandType.INT_IMMEDIATE]], lambda inst: self.encode_iu_alu(inst, IUSubtype.SHR, IUSubtype.SHRI)),
            ValidInstruction("and", [[ModifierType.REGISTER_IMMEDIATE, ModifierType.REGISTER_REGISTER], [ModifierType.IDTYPE]], [OperandType.REGISTER, OperandType.REGISTER, [OperandType.REGISTER, OperandType.INT_IMMEDIATE]], lambda inst: self.encode_iu_alu(inst, IUSubtype.AND, IUSubtype.ANDI)),
            ValidInstruction("or", [[ModifierType.REGISTER_IMMEDIATE, ModifierType.REGISTER_REGISTER], [ModifierType.IDTYPE]], [OperandType.REGISTER, OperandType.REGISTER, [OperandType.REGISTER, OperandType.INT_IMMEDIATE]], lambda inst: self.encode_iu_alu(inst, IUSubtype.OR, IUSubtype.ORI)),
            ValidInstruction("mul", [[ModifierType.REGISTER_IMMEDIATE, ModifierType.REGISTER_REGISTER], [ModifierType.IDTYPE]], [OperandType.REGISTER, OperandType.REGISTER, [OperandType.REGISTER, OperandType.INT_IMMEDIATE]], lambda inst: self.encode_iu_alu(inst, IUSubtype.MUL, IUSubtype.MULI)),
            ValidInstruction("special", [], [OperandType.REGISTER, OperandType.SPECIAL], lambda inst: self.encode_special(inst)),
            ValidInstruction("cmplt", [[ModifierType.REGISTER_IMMEDIATE, ModifierType.REGISTER_REGISTER], [ModifierType.IDTYPE]], [OperandType.REGISTER, OperandType.REGISTER, [OperandType.REGISTER, OperandType.INT_IMMEDIATE]], lambda inst: self.encode_iu_alu(inst, IUSubtype.CMPLT, IUSubtype.CMPLTI) if inst.get_dtype_modifiers()[0].value == "int32" else None),
        ]

class AssemblerLoadStoreUnit(AssemblerExecutionUnit):
    def encode_ld(self, inst: ParsedInstruction) -> int:
        dest = encode_dest_reg(inst.operands[0])
        addr = encode_register(inst.operands[1], 1) | encode_register(inst.operands[1], 0)
        subtype = None
        assert len(inst.get_dtype_modifiers()) == 1, "Load instruction must have one data type modifier."
        width = inst.get_dtype_modifiers()[0].get_dtype_width()
        if width == 1:
            subtype = LSUSubtype.LOAD_BYTE
        elif width == 2:
            subtype = LSUSubtype.LOAD_HALF
        elif width == 4:
            subtype = LSUSubtype.LOAD_WORD
        else:
            assert False, f"Invalid data width for load instruction: {width}"
        return dest | addr | encode_subtype(subtype)

    def encode_st(self, inst: ParsedInstruction) -> int:
        dest = encode_dest_reg(inst.operands[0])
        addr = encode_register(inst.operands[0], 1) | encode_register(inst.operands[1], 0)
        subtype = None
        assert len(inst.get_dtype_modifiers()) == 1, "Store instruction must have one data type modifier."
        width = inst.get_dtype_modifiers()[0].get_dtype_width()
        if width == 1:
            subtype = LSUSubtype.STORE_BYTE
        elif width == 2:
            subtype = LSUSubtype.STORE_HALF
        elif width == 4:
            subtype = LSUSubtype.STORE_WORD
        else:
            assert False, f"Invalid data width for store instruction: {width}"
        return dest | addr | encode_subtype(subtype)

    def __init__(self):
        self.name = "LSU"
        self.eu_enc = 1
        self.instructions = [
            ValidInstruction("ldparam", [], [OperandType.REGISTER, OperandType.INT_IMMEDIATE],
                lambda inst: encode_subtype(LSUSubtype.LOAD_PARAM) | encode_dest_reg(inst.operands[0]) | encode_large_immediate(inst.operands[1])),
            ValidInstruction("ld", [[ModifierType.IDTYPE, ModifierType.FDTYPE], [ModifierType.MEMORY_TYPE]], [OperandType.REGISTER, OperandType.REGISTER], lambda inst: self.encode_ld(inst)),
            ValidInstruction("st", [[ModifierType.IDTYPE, ModifierType.FDTYPE], [ModifierType.MEMORY_TYPE]], [OperandType.REGISTER, OperandType.REGISTER], lambda inst: self.encode_st(inst)),
        ]

class AssemblerBranchUnit(AssemblerExecutionUnit):
    def encode_branch(self, inst: ParsedInstruction) -> int:
        assert self.label_addresses is not None, "Label addresses not set in Branch Unit."
        assert inst.addr is not None, "Instruction address not set."
        assert inst.has_modifier(ModifierType.LABEL), "Branch instruction must have a label operand."
        assert inst.has_modifier(ModifierType.CONDITION), "Branch instruction must have a condition modifier."

        label_mods = inst.get_label_modifiers()
        assert len(label_mods) == 1, "Branch instruction must have exactly one label"
        label_mod = label_mods[0]

        dest_addr = self.label_addresses.get(label_mod.value, None)
        assert dest_addr is not None, f"Label not found: {label_mod.value}"
        offset = dest_addr - (inst.addr + 1)

        cond_mods = inst.get_condition_modifiers()
        assert len(cond_mods) == 1, "Branch instruction must have exactly one condition"

        subtype = None
        cond_mod = cond_mods[0]
        if cond_mod.value == "nz":
            subtype = BRUSubtype.BRNZ
        if cond_mod.value == "ez":
            subtype = BRUSubtype.BRZ
        assert subtype is not None, f"Unknown branch condition modifier: {cond_mod.value}"

        return encode_subtype(subtype) | encode_register(inst.operands[0], 1) | encode_small_immediate(Operand(str(offset)))

    def __init__(self):
        self.name = "BRU"
        self.label_addresses = None
        self.eu_enc = 2
        self.instructions = [
            ValidInstruction("stop", [], [], lambda inst: encode_subtype(BRUSubtype.STOP)),
            ValidInstruction("sync", [[ModifierType.SYNC_DOMAIN]], [], lambda inst: encode_subtype(BRUSubtype.SYNC_THREADS) if inst.modifiers[0].value == 'threads' else None),
            ValidInstruction("br", [[ModifierType.CONDITION], [ModifierType.LABEL]], [OperandType.REGISTER], lambda inst: self.encode_branch(inst)),
        ]

class AssemblerFPUnit(AssemblerExecutionUnit):
    def __init__(self):
        self.name = "FPU"
        self.eu_enc = 3
        self.instructions = [
            ValidInstruction("add", [[ModifierType.REGISTER_REGISTER], [ModifierType.FDTYPE]], [OperandType.REGISTER, OperandType.REGISTER, OperandType.REGISTER], lambda inst: encode_dest_reg(inst.operands[0]) | encode_register(inst.operands[1], 1) | encode_register(inst.operands[2], 0) | encode_subtype(FPUSubtype.FADD)),
            ValidInstruction("sub", [[ModifierType.REGISTER_REGISTER], [ModifierType.FDTYPE]], [OperandType.REGISTER, OperandType.REGISTER, OperandType.REGISTER], lambda inst: encode_dest_reg(inst.operands[0]) | encode_register(inst.operands[1], 1) | encode_register(inst.operands[2], 0) | encode_subtype(FPUSubtype.FSUB)),
            ValidInstruction("mul", [[ModifierType.REGISTER_REGISTER], [ModifierType.FDTYPE]], [OperandType.REGISTER, OperandType.REGISTER, OperandType.REGISTER], lambda inst: encode_dest_reg(inst.operands[0]) | encode_register(inst.operands[1], 1) | encode_register(inst.operands[2], 0) | encode_subtype(FPUSubtype.FMUL)),
            ValidInstruction("max", [[ModifierType.REGISTER_REGISTER], [ModifierType.FDTYPE]], [OperandType.REGISTER, OperandType.REGISTER, OperandType.REGISTER], lambda inst: encode_dest_reg(inst.operands[0]) | encode_register(inst.operands[1], 1) | encode_register(inst.operands[2], 0) | encode_subtype(FPUSubtype.FMAX)),
            ValidInstruction("exp2", [[ModifierType.REGISTER_REGISTER], [ModifierType.FDTYPE]], [OperandType.REGISTER, OperandType.REGISTER], lambda inst: encode_dest_reg(inst.operands[0]) | encode_register(inst.operands[1], 1) | encode_register(inst.operands[1], 0) | encode_subtype(FPUSubtype.FEXP2)),
            ValidInstruction("log2", [[ModifierType.REGISTER_REGISTER], [ModifierType.FDTYPE]], [OperandType.REGISTER, OperandType.REGISTER], lambda inst: encode_dest_reg(inst.operands[0]) | encode_register(inst.operands[1], 1) | encode_register(inst.operands[1], 0) | encode_subtype(FPUSubtype.FLOG2)),
            ValidInstruction("recip", [[ModifierType.REGISTER_REGISTER], [ModifierType.FDTYPE]], [OperandType.REGISTER, OperandType.REGISTER], lambda inst: encode_dest_reg(inst.operands[0]) | encode_register(inst.operands[1], 1) | encode_register(inst.operands[1], 0) | encode_subtype(FPUSubtype.FRECIP)),
            ValidInstruction("cmplt", [[ModifierType.REGISTER_REGISTER], [ModifierType.FDTYPE]], [OperandType.REGISTER, OperandType.REGISTER, OperandType.REGISTER], lambda inst: encode_dest_reg(inst.operands[0]) | encode_register(inst.operands[1], 1) | encode_register(inst.operands[2], 0) | encode_subtype(FPUSubtype.FCMPLT)),
        ]

class BGPUAssembler():
    def __init__(self):
        self.parser = Parser()
        self.executions_units = [AssemblerIntegerUnit(), AssemblerLoadStoreUnit(), AssemblerBranchUnit(), AssemblerFPUnit()]

    def expand_instruction(self, parsed_inst: ParsedInstruction) -> list[ParsedInstruction]:
        expand = []
        for eu in self.executions_units:
            expand = eu.expand_instruction(parsed_inst)
            if expand != []:
                return expand

        print(f"Failed to expand instruction: {parsed_inst}:")
        for op in parsed_inst.operands:
            print(f"  Operand: {op.type}")
        for mod in parsed_inst.modifiers:
            print(f"  Modifier: {mod.type}")
        assert False, f"Could not expand instruction: {parsed_inst}"

    def assemble_file(self, filepath: str) -> bytearray:
        return self.assemble(self.parser.parse_file(filepath))

    def assemble_lines(self, lines: list[str]) -> bytearray:
        return self.assemble(self.parser.parse_lines(lines))

    def assemble(self, parsed_instructions: list[ParsedInstruction]) -> bytearray:
        # exapand instructions
        expanded_instructions = []
        for parsed_inst in parsed_instructions:
            print(f"Expanding instruction: {parsed_inst}")
            expanded_instructions.extend(self.expand_instruction(parsed_inst))

        print("Expanded instructions:")
        for inst in expanded_instructions:
            print(inst)

        # Search for labels
        label_addresses = {}
        for addr, inst in enumerate(expanded_instructions):
            inst.addr = addr
            if inst.label is not None:
                label_addresses[inst.label] = addr

        # Print labels
        print("Labels found:")
        for label, addr in label_addresses.items():
            print(f"  {label}: {addr}")

        # Push label to BRU
        self.executions_units[2].label_addresses = label_addresses

        # Encode instructions
        machine_code = bytearray()
        for inst in expanded_instructions:
            print(f"Encoding instruction: {str(inst)}")
            encoded = False
            for eu in self.executions_units:
                enc_inst = eu.encode_instruction(inst)
                if enc_inst is not None:
                    bytecode = enc_inst.to_bytes(4, byteorder='little')
                    machine_code.extend(bytecode)
                    encoded = True
                    print(f"Encoded instruction to machine code: 0x{enc_inst.to_bytes(4, byteorder='big').hex()}")
                    break
            if not encoded:
                raise ValueError(f"Could not encode instruction: {inst}")

        for i, byte in enumerate(machine_code):
            print(f"Byte {i}: 0x{byte:02X}")

        # Output machine code
        return machine_code

example_asm = """
E_4:
	ldparam.int32   r0, 0 # define global
	ldparam.int32   r1, 1 # define global
	ldparam.int32   r2, 2 # define global
	mov.ri.int32	  r3, 0 # constant
	mov.ri.int32	  r4, 1 # constant
	mov.ri.int32	  r5, 2 # constant
	mov.ri.int32	  r6, 3 # constant
	shl.ri.int32		  r7,   r3, 2 # index shift
	add.rr.int32		  r7,   r1,   r7 # index
	ld.int32.global		  r8,   r7
	shl.ri.int32		  r9,   r4, 2 # index shift
	add.rr.int32		  r9,   r1,   r9 # index
	ld.int32.global		 r10,   r9
	shl.ri.int32		 r11,   r5, 2 # index shift
	add.rr.int32		 r11,   r1,  r11 # index
	ld.int32.global		 r12,  r11
	shl.ri.int32		 r13,   r6, 2 # index shift
	add.rr.int32		 r13,   r1,  r13 # index
	ld.int32.global		 r14,  r13
	shl.ri.int32		 r15,   r3, 2 # index shift
	add.rr.int32		 r15,   r2,  r15 # index
	ld.int32.global		 r16,  r15
	shl.ri.int32		 r17,   r4, 2 # index shift
	add.rr.int32		 r17,   r2,  r17 # index
	ld.int32.global		 r18,  r17
	shl.ri.int32		 r19,   r5, 2 # index shift
	add.rr.int32		 r19,   r2,  r19 # index
	ld.int32.global		 r20,  r19
	shl.ri.int32		 r21,   r6, 2 # index shift
	add.rr.int32		 r21,   r2,  r21 # index
	ld.int32.global		 r22,  r21
	shl.ri.int32		 r23,   r3, 2 # index shift
	add.rr.int32		 r23,   r0,  r23 # index
	shl.ri.int32		 r24,   r4, 2 # index shift
	add.rr.int32		 r24,   r0,  r24 # index
	shl.ri.int32		 r25,   r5, 2 # index shift
	add.rr.int32		 r25,   r0,  r25 # index
	shl.ri.int32		 r26,   r6, 2 # index shift
	add.rr.int32		 r26,   r0,  r26 # index
	shl.rr.int32		 r27,  r16,   r4
	add.rr.int32		 r28,   r8,  r27
	st.int32.global		 r23,  r28
	shl.rr.int32		 r29,  r18,   r4
	add.rr.int32		 r30,  r10,  r29
	st.int32.global		 r24,  r30
	shl.rr.int32		 r31,  r20,   r4
	add.rr.int32		 r32,  r12,  r31
	st.int32.global		 r25,  r32
	shl.rr.int32		 r33,  r22,   r4
	add.rr.int32		 r34,  r14,  r33
	st.int32.global		 r26,  r34
	stop
"""

if __name__ == "__main__":
    print("Assembling example ASM code...")
    code = BGPUAssembler().assemble_lines(example_asm.splitlines())
    print("Done.")
