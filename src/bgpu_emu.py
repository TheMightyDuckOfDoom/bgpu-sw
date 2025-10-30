from bgpu_instructions import *
from bgpu_util import float_to_hex, hex_to_float
import json
import math

class CU:
    def __init__(self, warp_width=4):
        self.pc = [0] * warp_width # one pc per thread
        self.stopped = [False] * warp_width
        self.syncing = [False] * warp_width
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
            self.pc = [pc] * self.warp_width
            self.stopped = [False] * self.warp_width
            self.syncing = [False] * self.warp_width
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

    def execute_iu(self, instruction, dst, op1, op2, tidx):
        print(f"Executing IU instruction: {instruction}, Dst=r{dst}, Op2={op2}, Op1={op1}")
        if instruction == IUSubtype.TID:
            self.regs[tidx][dst] = tidx
        elif instruction == IUSubtype.WID:
            self.regs[tidx][dst] = 0 # We only emulate a single warp
        elif instruction == IUSubtype.BID:
            self.regs[tidx][dst] = self.tb_id
        elif instruction == IUSubtype.TBID:
            self.regs[tidx][dst] = self.tb_id * self.warp_width + i
        elif instruction == IUSubtype.DPA:
            self.regs[tidx][dst] = self.dp_addr
        elif instruction == IUSubtype.ADD:
            self.regs[tidx][dst] = self.regs[tidx][op2] + self.regs[tidx][op1]
        elif instruction == IUSubtype.ADDI:
            self.regs[tidx][dst] = self.regs[tidx][op2] + op1
        elif instruction == IUSubtype.SUB:
            self.regs[tidx][dst] = self.regs[tidx][op2] - self.regs[tidx][op1]
        elif instruction == IUSubtype.SUBI:
            self.regs[tidx][dst] = self.regs[tidx][op2] - op1
        elif instruction == IUSubtype.LDI:
            self.regs[tidx][dst] = op2 << 8 | op1
        elif instruction == IUSubtype.OR:
            self.regs[tidx][dst] = self.regs[tidx][op2] | self.regs[tidx][op1]
        elif instruction == IUSubtype.ORI:
            self.regs[tidx][dst] = self.regs[tidx][op2] | op1
        elif instruction == IUSubtype.AND:
            self.regs[tidx][dst] = self.regs[tidx][op2] & self.regs[tidx][op1]
        elif instruction == IUSubtype.XOR:
            self.regs[tidx][dst] = self.regs[tidx][op2] ^ self.regs[tidx][op1]
        elif instruction == IUSubtype.SHL:
            self.regs[tidx][dst] = self.regs[tidx][op2] << self.regs[tidx][op1]
        elif instruction == IUSubtype.SHLI:
            self.regs[tidx][dst] = self.regs[tidx][op2] << op1
        elif instruction == IUSubtype.SHR:
            self.regs[tidx][dst] = self.regs[tidx][op2] >> self.regs[tidx][op1]
        elif instruction == IUSubtype.SHRI:
            self.regs[tidx][dst] = self.regs[tidx][op2] >> op1
        elif instruction == IUSubtype.MUL:
            self.regs[tidx][dst] = self.regs[tidx][op2] * self.regs[tidx][op1]
        elif instruction == IUSubtype.MULI:
            self.regs[tidx][dst] = self.regs[tidx][op2] * op1
        elif instruction == IUSubtype.CMPLT:
            print(f"Thread {tidx} CMPLT: r{op2}={self.regs[tidx][op2]} < r{op1}={self.regs[tidx][op1]}")
            op1_se = self.regs[tidx][op1] if self.regs[tidx][op1] < 0x80000000 else self.regs[tidx][op1] - 0x100000000
            op2_se = self.regs[tidx][op2] if self.regs[tidx][op2] < 0x80000000 else self.regs[tidx][op2] - 0x100000000
            print(f"Thread {tidx} CMPLT signed values: r{op2}={op2_se} < r{op1}={op1_se}")
            self.regs[tidx][dst] = 1 if op2_se < op1_se else 0
        else:
            raise ValueError(f"Unknown IU instruction: {instruction}") 

        print(f"Thread {tidx} Dst=r{dst} set to {self.regs[tidx][dst]:#010x}, op2 if reg was r{op2}={self.regs[tidx][op2]:#010x}, op1 if reg was r{op1}={self.regs[tidx][op1]:#010x}")

        # Increment the program counter
        self.pc[tidx] += 4
    
    def execute_lsu(self, instruction, dst, op1, op2, memory, tidx):
        print(f"Executing LSU instruction: {instruction}, Dst=r{dst}, Op2={op2}, Op1={op1}")
        address = self.regs[tidx][op2]
        if instruction is not LSUSubtype.LOAD_PARAM:
            print(f"Thread {tidx} accessing memory at address {address:#010x}")
        if instruction == LSUSubtype.LOAD_BYTE:
            if address < 0 or address >= len(memory):
                raise ValueError(f"Memory access out of bounds: {address:#010x}")
            self.regs[tidx][dst] = memory[address]
        elif instruction == LSUSubtype.LOAD_HALF:
            if address < 0 or address + 1 >= len(memory):
                raise ValueError(f"Memory access out of bounds: {address:#010x}")
            if address % 2 != 0:
                raise ValueError(f"Unaligned memory access: {address:#010x}")
            self.regs[tidx][dst] = memory[address] | (memory[address + 1] << 8)
        elif instruction == LSUSubtype.LOAD_WORD:
            if address < 0 or address + 3 >= len(memory):
                raise ValueError(f"Memory access out of bounds: {address:#010x}")
            if address % 4 != 0:
                raise ValueError(f"Unaligned memory access: {address:#010x}")
            self.regs[tidx][dst] = memory[address] | (memory[address + 1] << 8) | (memory[address + 2] << 16) | (memory[address + 3] << 24)
        elif instruction == LSUSubtype.STORE_BYTE:
            data = self.regs[tidx][op1]
            if address < 0 or address >= len(memory):
                raise ValueError(f"Memory access out of bounds: {address:#010x}")
            memory[address] = data & 0xFF
            # Clear the destination register
            self.regs[tidx][dst] = 0
        elif instruction == LSUSubtype.STORE_HALF:
            data = self.regs[tidx][op1]
            if address < 0 or address + 1 >= len(memory):
                raise ValueError(f"Memory access out of bounds: {address:#010x}")
            if address % 2 != 0:
                raise ValueError(f"Unaligned memory access: {address:#010x}")
            memory[address] = data & 0xFF
            memory[address + 1] = (data >> 8) & 0xFF
            # Clear the destination register
            self.regs[tidx][dst] = 0
        elif instruction == LSUSubtype.STORE_WORD:
            data = self.regs[tidx][op1]
            if address < 0 or address + 3 >= len(memory):
                raise ValueError(f"Memory access out of bounds: {address:#010x}")
            if address % 4 != 0:
                raise ValueError(f"Unaligned memory access: {address:#010x}")
            memory[address] = data & 0xFF
            memory[address + 1] = (data >> 8) & 0xFF
            memory[address + 2] = (data >> 16) & 0xFF
            memory[address + 3] = (data >> 24) & 0xFF
            # Clear the destination register
            self.regs[tidx][dst] = 0
        elif instruction == LSUSubtype.LOAD_PARAM:
            address = self.dp_addr + op1 * 4
            print(f"Thread {tidx} loading parameter from address {address:#010x} = {self.dp_addr:#010x} + {op1 * 4:#010x}")
            if address < 0 or address + 3 >= len(memory):
                raise ValueError(f"Param memory access out of bounds: {address:#010x}")
            if address % 4 != 0:
                raise ValueError(f"Unaligned paramter memory access: {address:#010x}")
            self.regs[tidx][dst] = memory[address] | (memory[address + 1] << 8) | (memory[address + 2] << 16) | (memory[address + 3] << 24)
        else:
            raise NotImplementedError(f"LSU instruction {instruction} not implemented")

        print(f"Thread {tidx} Dst=r{dst} set to {self.regs[tidx][dst]:#010x}")

        # Increment the program counter
        self.pc[tidx] += 4

    def execute_fpu(self, instruction, dst, op1, op2, tidx):
        print(f"Executing FPU instruction: {instruction}, Dst=r{dst}, Op2={op2}, Op1={op1}")
        # Assume registers hold IEEE 754 float bit patterns
        op1_float = hex_to_float(self.regs[tidx][op1])
        op2_float = hex_to_float(self.regs[tidx][op2])
        result = 0.0
        if instruction == FPUSubtype.FADD:
            print(f"Thread {tidx} FADD: {op2_float} + {op1_float}")
            result = op2_float + op1_float
            print(f"Thread {tidx} FADD result: {result}")
        elif instruction == FPUSubtype.FSUB:
            print(f"Thread {tidx} FSUB: {op2_float} - {op1_float}")
            result = op2_float - op1_float
            print(f"Thread {tidx} FSUB result: {result}")
        elif instruction == FPUSubtype.FMUL:
            print(f"Thread {tidx} FMUL: {op2_float} * {op1_float}")
            result = op2_float * op1_float
            print(f"Thread {tidx} FMUL result: {result}")
        elif instruction == FPUSubtype.FMAX:
            print(f"Thread {tidx} FMAX: {op2_float} {op1_float}")
            result = op2_float if op2_float > op1_float else op1_float
            print(f"Thread {tidx} FMAX result: {result}")
        elif instruction == FPUSubtype.FEXP2:
            print(f"Thread {tidx} FEXP2: 2^{op1_float}")
            result = 2.0 ** op1_float
            print(f"Thread {tidx} FEXP2 result: {result}")
        elif instruction == FPUSubtype.FRECIP:
            print(f"Thread {tidx} FRECIP: 1 / {op1_float}")
            result = 1.0 / op1_float
            print(f"Thread {tidx} FRECIP result: {result}")
        elif instruction == FPUSubtype.FLOG2:
            print(f"Thread {tidx} FLOG2: log2({op1_float})")
            result = math.log2(op1_float)
            print(f"Thread {tidx} FLOG2 result: {result}")
        elif instruction == FPUSubtype.FCMPLT:
            print(f"Thread {tidx} FCMPLT: {op2_float} < {op1_float}")
            result = 1 if op2_float < op1_float else 0
            print(f"Thread {tidx} FCMPLT result: {result}")
        else:
            raise ValueError(f"Unknown FPU instruction: {instruction}") 

        self.regs[tidx][dst] = int(float_to_hex(result), 16)

        print(f"Thread {tidx} Dst=r{dst} set to {self.regs[tidx][dst]:#010x}, op2 if reg was r{op2}={self.regs[tidx][op2]:#010x}, op1 if reg was r{op1}={self.regs[tidx][op1]:#010x}")

        # Increment the program counter
        self.pc[tidx] += 4

    def execute_bru(self, instruction, dst, op1, op2, tidx):
        print(f"Executing BRU instruction: {instruction}, Dst=r{dst}, Op2={op2}, Op1={op1}")

        if instruction == BRUSubtype.SYNC_THREADS:
            print("Syncing threads...")
            # Set this thread as syncing
            self.syncing[tidx] = True
            # Check if all other threads are at a sync point
            num_syncing = sum(1 for s in self.syncing if s)
            if num_syncing == self.warp_width:
                print("All threads synced, continuing execution.")
                # All threads are syncing, clear the syncing flags and continue
                for i in range(self.warp_width):
                    self.syncing[i] = False
                    self.pc[i] += 4
            return
        elif instruction == BRUSubtype.BRZ:
            if self.regs[tidx][op2] == 0:
                print(f"BRZ taken: r{op2}={self.regs[tidx][op2]} == 0, jumping to pc+1+{op1}")
                self.pc[tidx] += (op1 + 1) * 4
            else:
                print(f"BRZ not taken: r{op2}={self.regs[tidx][op2]} != 0, continuing")
                self.pc[tidx] += 4
        else:
            raise ValueError(f"Unknown BRU instruction: {instruction}") 

    def read_instruction_memory(self, memory, address):
        if address < 0 or address + 3 >= len(memory):
            raise ValueError(f"Instruction memory access out of bounds: {address:#010x}")
        instruction = memory[address] | (memory[address + 1] << 8) | (memory[address + 2] << 16) | (memory[address + 3] << 24)
        return instruction

    def execute(self, memory):
        # New reg trace
        self.timestamp = 1
        self.reg_trace = {}

        for i in range(self.warp_width):
            self.reg_trace[i] = {}

        all_stopped = False
        while not all_stopped:
            for tidx in range(self.warp_width):
                instruction = self.read_instruction_memory(memory, self.pc[tidx])
                print(f"Thread {tidx} Executing instruction at PC={self.pc[tidx]:#010x}: {instruction:#010x}")

                eu, subtype, dst, op2, op1 = self.decode_instruction(instruction)

                if eu == EU.BRU and subtype == BRUSubtype.STOP:
                    print("Stopping execution.")
                    self.stopped[tidx] = True
                elif eu == EU.IU:
                    self.execute_iu(subtype, dst, op1, op2, tidx)
                elif eu == EU.LSU:
                    self.execute_lsu(subtype, dst, op1, op2, memory, tidx)
                elif eu == EU.BRU:
                    self.execute_bru(subtype, dst, op1, op2, tidx)
                elif eu == EU.FPU:
                    self.execute_fpu(subtype, dst, op1, op2, tidx)
                else:
                    raise ValueError(f"Unknown EU: {eu}")

                if self.syncing[tidx]:
                    # If the thread is syncing, do not record register changes or increment timestamp
                    continue

                # Update the register trace -> store changed values
                if dst not in self.reg_trace[tidx]:
                    self.reg_trace[tidx][dst] = []
                self.reg_trace[tidx][dst].append((self.timestamp, self.regs[tidx][dst]))
                
                # Increment the timestamp
                self.timestamp += 1

                if self.pc[tidx] >= len(memory):
                    raise Exception(f"PC out of bounds: {self.pc[tidx]:#010x}")

            # Check if all threads have stopped
            all_stopped = True
            for tidx in range(self.warp_width):
                if not self.stopped[tidx]:
                    all_stopped = False
                    break

        return self.reg_trace

        raise Exception(f"PC out of bounds: {self.pc:#010x}")
