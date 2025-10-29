from bgpu_instructions import *
from bgpu_util import float_to_hex, hex_to_float
import json
import math

class CU:
    def __init__(self, warp_width=4):
        self.pc = 0
        self.dp_addr = 0
        self.tb_id = 0
        self.num_regs = 256 # per thread
        self.regs = [[0] * self.num_regs for _ in range(warp_width)]
        self.warp_width = warp_width

        self.reg_trace = {}

    def dispatch_and_execute(self, pc, dp_addr, tblocks_to_dispatch, tgroup_id, memory):
        print(f"Dispatching and executing: PC={pc:#010x}, DP_ADDR={dp_addr:#010x}, TBlocks={tblocks_to_dispatch}, TGroupID={tgroup_id}")
        
        reg_traces_per_tblock = {}
        for tb in range(tblocks_to_dispatch):
            print(f"Executing TBlock {tb} with TGroupID {tgroup_id}")
            self.pc = pc
            self.dp_addr = dp_addr
            self.tb_id = tb

            reg_traces_per_tblock[tb] = self.execute(memory)
        # Simulate execution logic here
        print("Execution complete.")

        with open(f"reg_trace.log", "w") as f:
            json.dump(reg_traces_per_tblock, f, indent=4)
            print(f"Register trace saved to reg_trace.log")

    def decode_instruction(self, instruction):
        eu = EU(instruction >> 30) # Upper 2 bits for EU
        subtype_value = (instruction >> 24) & 0x3F # Next 6 bits for subtype

        subtype = None
        if eu == EU.IU:
            subtype = IUSubtype(subtype_value)
        elif eu == EU.FPU:
            subtype = FPUSubtype(subtype_value)
        elif eu == EU.LSU:
            subtype = LSUSubtype(subtype_value)
        elif eu == EU.BRU:
            subtype = BRUSubtype(subtype_value)
        else:
            raise ValueError(f"Unknown EU: {eu}")

        dst = (instruction >> 16) & 0xFF # Next 8 bits for destination register
        op2 = (instruction >> 8) & 0xFF # Next 8 bits for operand 2 register
        op1 = instruction & 0xFF # Last 8 bits for operand 1

        print(f"Decoded instruction: EU={eu}, Subtype={subtype}, Dst={dst}, Op2={op2}, Op1={op1}")

        return eu, subtype, dst, op2, op1

    def execute_iu(self, instruction, dst, op1, op2):
        print(f"Executing IU instruction: {instruction}, Dst=r{dst}, Op2={op2}, Op1={op1}")
        for i in range(self.warp_width):
            if instruction == IUSubtype.TID:
                self.regs[i][dst] = i            
            elif instruction == IUSubtype.WID:
                self.regs[i][dst] = 0 # We only emulate a single warp
            elif instruction == IUSubtype.BID:
                self.regs[i][dst] = self.tb_id
            elif instruction == IUSubtype.TBID:
                self.regs[i][dst] = self.tb_id * self.warp_width + i
            elif instruction == IUSubtype.DPA:
                self.regs[i][dst] = self.dp_addr
            elif instruction == IUSubtype.ADD:
                self.regs[i][dst] = self.regs[i][op2] + self.regs[i][op1]
            elif instruction == IUSubtype.ADDI:
                self.regs[i][dst] = self.regs[i][op2] + op1
            elif instruction == IUSubtype.SUB:
                self.regs[i][dst] = self.regs[i][op2] - self.regs[i][op1]
            elif instruction == IUSubtype.SUBI:
                self.regs[i][dst] = self.regs[i][op2] - op1
            elif instruction == IUSubtype.LDI:
                self.regs[i][dst] = op2 << 8 | op1
            elif instruction == IUSubtype.OR:
                self.regs[i][dst] = self.regs[i][op2] | self.regs[i][op1]
            elif instruction == IUSubtype.ORI:
                self.regs[i][dst] = self.regs[i][op2] | op1
            elif instruction == IUSubtype.AND:
                self.regs[i][dst] = self.regs[i][op2] & self.regs[i][op1]
            elif instruction == IUSubtype.XOR:
                self.regs[i][dst] = self.regs[i][op2] ^ self.regs[i][op1]
            elif instruction == IUSubtype.SHL:
                self.regs[i][dst] = self.regs[i][op2] << self.regs[i][op1]
            elif instruction == IUSubtype.SHLI:
                self.regs[i][dst] = self.regs[i][op2] << op1
            elif instruction == IUSubtype.SHR:
                self.regs[i][dst] = self.regs[i][op2] >> self.regs[i][op1]
            elif instruction == IUSubtype.SHRI:
                self.regs[i][dst] = self.regs[i][op2] >> op1
            elif instruction == IUSubtype.MUL:
                self.regs[i][dst] = self.regs[i][op2] * self.regs[i][op1]
            elif instruction == IUSubtype.MULI:
                self.regs[i][dst] = self.regs[i][op2] * op1
            else:
                raise ValueError(f"Unknown IU instruction: {instruction}") 

            print(f"Thread {i} Dst=r{dst} set to {self.regs[i][dst]:#010x}, op2 if reg was r{op2}={self.regs[i][op2]:#010x}, op1 if reg was r{op1}={self.regs[i][op1]:#010x}")

        # Increment the program counter
        self.pc += 4
    
    def execute_lsu(self, instruction, dst, op1, op2, memory):
        print(f"Executing LSU instruction: {instruction}, Dst=r{dst}, Op2={op2}, Op1={op1}")
        for i in range(self.warp_width):
            address = self.regs[i][op2]
            if instruction is not LSUSubtype.LOAD_PARAM:
                print(f"Thread {i} accessing memory at address {address:#010x}")
            if instruction == LSUSubtype.LOAD_BYTE:
                if address < 0 or address >= len(memory):
                    raise ValueError(f"Memory access out of bounds: {address:#010x}")
                self.regs[i][dst] = memory[address]
            elif instruction == LSUSubtype.LOAD_HALF:
                if address < 0 or address + 1 >= len(memory):
                    raise ValueError(f"Memory access out of bounds: {address:#010x}")
                if address % 2 != 0:
                    raise ValueError(f"Unaligned memory access: {address:#010x}")
                self.regs[i][dst] = memory[address] | (memory[address + 1] << 8)
            elif instruction == LSUSubtype.LOAD_WORD:
                if address < 0 or address + 3 >= len(memory):
                    raise ValueError(f"Memory access out of bounds: {address:#010x}")
                if address % 4 != 0:
                    raise ValueError(f"Unaligned memory access: {address:#010x}")
                self.regs[i][dst] = memory[address] | (memory[address + 1] << 8) | (memory[address + 2] << 16) | (memory[address + 3] << 24)
            elif instruction == LSUSubtype.STORE_BYTE:
                data = self.regs[i][op1]
                if address < 0 or address >= len(memory):
                    raise ValueError(f"Memory access out of bounds: {address:#010x}")
                memory[address] = data & 0xFF
                # Clear the destination register
                self.regs[i][dst] = 0
            elif instruction == LSUSubtype.STORE_HALF:
                data = self.regs[i][op1]
                if address < 0 or address + 1 >= len(memory):
                    raise ValueError(f"Memory access out of bounds: {address:#010x}")
                if address % 2 != 0:
                    raise ValueError(f"Unaligned memory access: {address:#010x}")
                memory[address] = data & 0xFF
                memory[address + 1] = (data >> 8) & 0xFF
                # Clear the destination register
                self.regs[i][dst] = 0
            elif instruction == LSUSubtype.STORE_WORD:
                data = self.regs[i][op1]
                if address < 0 or address + 3 >= len(memory):
                    raise ValueError(f"Memory access out of bounds: {address:#010x}")
                if address % 4 != 0:
                    raise ValueError(f"Unaligned memory access: {address:#010x}")
                memory[address] = data & 0xFF
                memory[address + 1] = (data >> 8) & 0xFF
                memory[address + 2] = (data >> 16) & 0xFF
                memory[address + 3] = (data >> 24) & 0xFF
                # Clear the destination register
                self.regs[i][dst] = 0
            elif instruction == LSUSubtype.LOAD_PARAM:
                address = self.dp_addr + op1 * 4
                print(f"Thread {i} loading parameter from address {address:#010x} = {self.dp_addr:#010x} + {op1 * 4:#010x}")
                if address < 0 or address + 3 >= len(memory):
                    raise ValueError(f"Param memory access out of bounds: {address:#010x}")
                if address % 4 != 0:
                    raise ValueError(f"Unaligned paramter memory access: {address:#010x}")
                self.regs[i][dst] = memory[address] | (memory[address + 1] << 8) | (memory[address + 2] << 16) | (memory[address + 3] << 24)
            else:
                raise NotImplementedError(f"LSU instruction {instruction} not implemented")

            print(f"Thread {i} Dst=r{dst} set to {self.regs[i][dst]:#010x}")

        # Increment the program counter
        self.pc += 4


    def execute_fpu(self, instruction, dst, op1, op2):
        print(f"Executing FPU instruction: {instruction}, Dst=r{dst}, Op2={op2}, Op1={op1}")
        for i in range(self.warp_width):
            # Assume registers hold IEEE 754 float bit patterns
            op1_float = hex_to_float(self.regs[i][op1])
            op2_float = hex_to_float(self.regs[i][op2])
            result = 0.0
            if instruction == FPUSubtype.FADD:
                print(f"Thread {i} FADD: {op2_float} + {op1_float}")
                result = op2_float + op1_float
                print(f"Thread {i} FADD result: {result}")
            elif instruction == FPUSubtype.FSUB:
                print(f"Thread {i} FSUB: {op2_float} - {op1_float}")
                result = op2_float - op1_float
                print(f"Thread {i} FSUB result: {result}")
            elif instruction == FPUSubtype.FMUL:
                print(f"Thread {i} FMUL: {op2_float} * {op1_float}")
                result = op2_float * op1_float
                print(f"Thread {i} FMUL result: {result}")
            elif instruction == FPUSubtype.FMAX:
                print(f"Thread {i} FMAX: {op2_float} {op1_float}")
                result = op2_float if op2_float > op1_float else op1_float
                print(f"Thread {i} FMAX result: {result}")
            elif instruction == FPUSubtype.FEXP2:
                print(f"Thread {i} FEXP2: 2^{op1_float}")
                result = 2.0 ** op1_float
                print(f"Thread {i} FEXP2 result: {result}")
            elif instruction == FPUSubtype.FRECIP:
                print(f"Thread {i} FRECIP: 1 / {op1_float}")
                result = 1.0 / op1_float
                print(f"Thread {i} FRECIP result: {result}")
            elif instruction == FPUSubtype.FLOG2:
                print(f"Thread {i} FLOG2: log2({op1_float})")
                result = math.log2(op1_float)
                print(f"Thread {i} FLOG2 result: {result}")
            else:
                raise ValueError(f"Unknown FPU instruction: {instruction}") 

            self.regs[i][dst] = int(float_to_hex(result), 16)

            print(f"Thread {i} Dst=r{dst} set to {self.regs[i][dst]:#010x}, op2 if reg was r{op2}={self.regs[i][op2]:#010x}, op1 if reg was r{op1}={self.regs[i][op1]:#010x}")

        # Increment the program counter
        self.pc += 4
    def execute(self, memory):
        # New reg trace
        self.timestamp = 1
        self.reg_trace = {}

        for i in range(self.warp_width):
            self.reg_trace[i] = {}

        while self.pc < len(memory):
            instruction = memory[self.pc] | (memory[self.pc + 1] << 8) | (memory[self.pc + 2] << 16) | (memory[self.pc + 3] << 24)
            print(f"Executing instruction at PC={self.pc:#010x}: {instruction:#010x}")

            eu, subtype, dst, op2, op1 = self.decode_instruction(instruction)

            if eu == EU.BRU and subtype == BRUSubtype.STOP:
                print("Stopping execution.")
                return self.reg_trace
            elif eu == EU.IU:
                self.execute_iu(subtype, dst, op1, op2)
            elif eu == EU.LSU:
                self.execute_lsu(subtype, dst, op1, op2, memory)
            elif eu == EU.BRU:
                raise NotImplementedError("BRU execution not implemented")
            elif eu == EU.FPU:
                self.execute_fpu(subtype, dst, op1, op2)
            else:
                raise ValueError(f"Unknown EU: {eu}")

            # Update the register trace -> store changed values
            for i in range(self.warp_width):
                if dst not in self.reg_trace[i]:
                    self.reg_trace[i][dst] = []
                self.reg_trace[i][dst].append((self.timestamp, self.regs[i][dst]))
            
            # Increment the timestamp
            self.timestamp += 1

        raise Exception(f"PC out of bounds: {self.pc:#010x}")
