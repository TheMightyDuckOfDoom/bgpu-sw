#!/usr/bin/env python3

from pygdbmi.gdbcontroller import GdbController
from bgpu_emu import CU

tblocks = 0
DataPerMatrix = 0
prog = []

ex_prog = 'add_8'
emu = False
inorder = True

if ex_prog == 'add_8':
    DataPerMatrix = 8 ** 2
    Tblocks = 4
    prog = [
        0x04000000, # special                   r0, %param
        0x42010000, # ld.int32.param            r1,   r0
        0x0c020004, # add.ri.int32              r2,   r0, 4
        0x42020200, # ld.int32.param            r2,   r2
        0x0c030008, # add.ri.int32              r3,   r0, 8
        0x42030300, # ld.int32.param            r3,   r3
        0x02000000, # special                   r0, %gidx0
        0x00040000, # special                   r4, %lidx0
        0x0e050004, # shl.ri.int32              r5,   r0,    4
        0x0e060402, # shl.ri.int32              r6,   r4,    2
        0x05070506, # add.rr.int32              r7,   r5,   r6
        0x0e050702, # shl.ri.int32              r5,   r7,    2
        0x05050205, # add.rr.int32              r5,   r2,   r5
        0x42060500, # ld.int32.global           r6,   r5
        0x0e050702, # shl.ri.int32              r5,   r7,    2
        0x05050305, # add.rr.int32              r5,   r3,   r5
        0x42080500, # ld.int32.global           r8,   r5
        0x0c050701, # add.ri.int32              r5,   r7,    1
        0x0e090502, # shl.ri.int32              r9,   r5,    2
        0x05090209, # add.rr.int32              r9,   r2,   r9
        0x420a0900, # ld.int32.global          r10,   r9
        0x0e090502, # shl.ri.int32              r9,   r5,    2
        0x05090309, # add.rr.int32              r9,   r3,   r9
        0x420b0900, # ld.int32.global          r11,   r9
        0x0c090702, # add.ri.int32              r9,   r7,    2
        0x0e0c0902, # shl.ri.int32             r12,   r9,    2
        0x050c020c, # add.rr.int32             r12,   r2,  r12
        0x420d0c00, # ld.int32.global          r13,  r12
        0x0e0c0902, # shl.ri.int32             r12,   r9,    2
        0x050c030c, # add.rr.int32             r12,   r3,  r12
        0x420e0c00, # ld.int32.global          r14,  r12
        0x0c0c0703, # add.ri.int32             r12,   r7,    3
        0x0e0f0c02, # shl.ri.int32             r15,  r12,    2
        0x050f020f, # add.rr.int32             r15,   r2,  r15
        0x42020f00, # ld.int32.global           r2,  r15
        0x0e0f0c02, # shl.ri.int32             r15,  r12,    2
        0x050f030f, # add.rr.int32             r15,   r3,  r15
        0x42030f00, # ld.int32.global           r3,  r15
        0x0e0f0502, # shl.ri.int32             r15,   r5,    2
        0x050f010f, # add.rr.int32             r15,   r1,  r15
        0x0e050902, # shl.ri.int32              r5,   r9,    2
        0x05050105, # add.rr.int32              r5,   r1,   r5
        0x0e090c02, # shl.ri.int32              r9,  r12,    2
        0x05090109, # add.rr.int32              r9,   r1,   r9
        0x0e0c0702, # shl.ri.int32             r12,   r7,    2
        0x050c010c, # add.rr.int32             r12,   r1,  r12
        0x05010a0b, # add.rr.int32              r1,  r10,  r11
        0x450f0f01, # st.int32.global          r15,   r1
        0x05010d0e, # add.rr.int32              r1,  r13,  r14
        0x45050501, # st.int32.global           r5,   r1
        0x05010203, # add.rr.int32              r1,   r2,   r3
        0x45090901, # st.int32.global           r9,   r1
        0x05010608, # add.rr.int32              r1,   r6,   r8
        0x450c0c01, # st.int32.global          r12,   r1
        0xff000000  # stop
    ]

if ex_prog == 'add_4':
    Tblocks = 1
    DataPerMatrix = 4 ** 2
    prog = [
        0x04000000, # special                   r0, %param
        0x42010000, # ld.int32.param            r1,   r0
        0x0c020004, # add.ri.int32              r2,   r0, 4
        0x42020200, # ld.int32.param            r2,   r2
        0x0c030008, # add.ri.int32              r3,   r0, 8
        0x42030300, # ld.int32.param            r3,   r3
        0x00000000, # special                   r0, %lidx0
        0x0e040002, # shl.ri.int32              r4,   r0,    2

        0x0e050402, # shl.ri.int32              r5,   r4,    2
        0x05050205, # add.rr.int32              r5,   r2,   r5
        0x42060500, # ld.int32.global           r6,   r5
        0x0e050402, # shl.ri.int32              r5,   r4,    2
        0x05050305, # add.rr.int32              r5,   r3,   r5
        0x42070500, # ld.int32.global           r7,   r5
        0x0c050401, # add.ri.int32              r5,   r4,    1
        0x0e080502, # shl.ri.int32              r8,   r5,    2
        0x05080208, # add.rr.int32              r8,   r2,   r8
        0x42090800, # ld.int32.global           r9,   r8
        0x0e080502, # shl.ri.int32              r8,   r5,    2
        0x05080308, # add.rr.int32              r8,   r3,   r8
        0x420a0800, # ld.int32.global          r10,   r8
        0x0c080402, # add.ri.int32              r8,   r4,    2
        0x0e0b0802, # shl.ri.int32             r11,   r8,    2
        0x050b020b, # add.rr.int32             r11,   r2,  r11
        0x420c0b00, # ld.int32.global          r12,  r11
        0x0e0b0802, # shl.ri.int32             r11,   r8,    2
        0x050b030b, # add.rr.int32             r11,   r3,  r11
        0x420d0b00, # ld.int32.global          r13,  r11
        0x0c0b0403, # add.ri.int32             r11,   r4,    3
        0x0e0e0b02, # shl.ri.int32             r14,  r11,    2
        0x050e020e, # add.rr.int32             r14,   r2,  r14
        0x42020e00, # ld.int32.global           r2,  r14
        0x0e0e0b02, # shl.ri.int32             r14,  r11,    2
        0x050e030e, # add.rr.int32             r14,   r3,  r14
        0x42030e00, # ld.int32.global           r3,  r14
        0x0e0e0502, # shl.ri.int32             r14,   r5,    2 # This is causing an infinite loop
        0x050e010e, # add.rr.int32             r14,   r1,  r14
        0x0e050802, # shl.ri.int32              r5,   r8,    2
        0x05050105, # add.rr.int32              r5,   r1,   r5
        0x0e080b02, # shl.ri.int32              r8,  r11,    2
        0x05080108, # add.rr.int32              r8,   r1,   r8
        0x0e0b0402, # shl.ri.int32             r11,   r4,    2
        0x050b010b, # add.rr.int32             r11,   r1,  r11
        0x0501090a, # add.rr.int32              r1,   r9,  r10
        0x450e0e01, # st.int32.global          r14,   r1
        0x05010c0d, # add.rr.int32              r1,  r12,  r13
        0x45050501, # st.int32.global           r5,   r1
        0x05010203, # add.rr.int32              r1,   r2,   r3
        0x45080801, # st.int32.global           r8,   r1
        0x05010607, # add.rr.int32              r1,   r6,   r7
        0x450b0b01, # st.int32.global          r11,   r1
        0xff000000  # stop
    ]

if ex_prog == 'add_2':
    Tblocks = 1
    DataPerMatrix = 2 ** 2
    prog = [
        0x04000000,
        0x42010000,
        0x0c020004,
        0x42020200,
        0x0c000008,
        0x42000000,
        0x0c030200,
        0x42030300,
        0x0c040204,
        0x42040400,
        0x0c050208,
        0x42050500,
        0x0c02020c,
        0x42020200,
        0x0c060000,
        0x42060600,
        0x0c070004,
        0x42070700,
        0x0c080008,
        0x42080800,
        0x0c00000c,
        0x42000000,
        0x0c090100,
        0x0c0a0104,
        0x0c0b0108,
        0x0c01010c,
        0x05030306,
        0x45090903,
        0x05030407,
        0x450a0a03,
        0x05030508,
        0x450b0b03,
        0x05000200,
        0x45010100,
        0xff000000,
        0xff000000
    ]

class BGPUEmu:
    def __init__(self, memory_size=1 << 10, warp_width=4):
        self.te_base = 0xFFFFFF00
        self.te_pc = 0
        self.te_dp_addr = 0
        self.te_tblocks_to_dispatch = 0
        self.te_tgroup_id = 0
        self.te_status = 0

        # Byte addressable memory
        self.memory = [0] * memory_size

        self.cu = CU(warp_width)

    def write(self, address, data, check=True):
        if address % 4 != 0:
            raise ValueError(f"Unaligned memory access at address {address:#010x}")

        if address >= 0 and address + 3 < len(self.memory):
            # print(f"Writing to address {address:#010x}: {data:#010x}")
            self.memory[address] = data & 0xFF
            self.memory[address + 1] = (data >> 8) & 0xFF
            self.memory[address + 2] = (data >> 16) & 0xFF
            self.memory[address + 3] = (data >> 24) & 0xFF
            return

        if address >= self.te_base and address < self.te_base + 5 * 4:
            # print(f"Writing to thread engine base address {self.te_base:#010x}")
            if address == self.te_base + 0 * 4:
                self.te_pc = data
            elif address == self.te_base + 1 * 4:
                self.te_dp_addr = data
            elif address == self.te_base + 2 * 4:
                self.te_tblocks_to_dispatch = data
            elif address == self.te_base + 3 * 4:
                self.te_tgroup_id = data
            elif address == self.te_base + 4 * 4:
                # Execute the dispatch
                self.cu.dispatch_and_execute(
                    self.te_pc,
                    self.te_dp_addr,
                    self.te_tblocks_to_dispatch,
                    self.te_tgroup_id,
                    self.memory
                )
                # Update the status
                self.te_status |= 1 << 2 # Finished bit
                self.te_status |= self.te_tblocks_to_dispatch << 4 # Number of dispatched TBlocks
                self.te_status |= self.te_tblocks_to_dispatch << 24 # Number of finished TBlocks
            return

        raise ValueError(f"Invalid address {address:#010x} for write operation")

    def read(self, address):
        if address % 4 != 0:
            raise ValueError(f"Unaligned memory access at address {address:#010x}")

        if address >= 0 and address + 3 < len(self.memory):
            value = self.memory[address] | (self.memory[address + 1] << 8) | (self.memory[address + 2] << 16) | (self.memory[address + 3] << 24)
            # print(f"Reading from address {address:#010x}: {value:#010x}")
            return value

        if address >= self.te_base and address < self.te_base + 5 * 4:
            # print(f"Reading from thread engine base address {self.te_base:#010x}")
            if address == self.te_base + 0 * 4:
                return self.te_pc
            elif address == self.te_base + 1 * 4:
                return self.te_dp_addr
            elif address == self.te_base + 2 * 4:
                return self.te_tblocks_to_dispatch
            elif address == self.te_base + 3 * 4:
                return self.te_tgroup_id
            elif address == self.te_base + 4 * 4:
                return self.te_status

        raise ValueError(f"Invalid address {address:#010x}")

class GDB:
    def __init__(self):
        self.gdb = GdbController(['gdb-multiarch', '--interpreter=mi3', '--nx', '--quiet'])
        self.gdb.write('target extended-remote :3333')

    def write(self, address, data, check=True):
        command = f"set *{address:#010x} = {data:#010x}"
        resp = self.gdb.write(command)
        assert resp[1]['message'] == 'memory-changed', "Memory write failed: " + str(resp)

        read_value = self.read(address)
        if check and read_value != data:
            raise ValueError(f"Data mismatch at address {address:#010x}: expected {data:#010x}, got {read_value:#010x}")

    def read(self, address):
        command = f"x {address:#010x}"
        resp = self.gdb.write(command)
        assert resp[1]['message'] == None, "Memory read failed: " + str(resp)
        value = None
        for r in resp:
            if r['payload'] is not None and not r['payload'].startswith("x "):
                value = int(r['payload'].split('\t')[1], 16)
        return value

class BGPU:
    def __init__(self, con):
        self.con = con
        self.base = 0xFFFFFF00

    def write_thread_engine_register(self, reg, value, check=True):
        address = self.base + reg * 4
        print(f"Writing to thread engine register: {address:#010x} = {value:#010x}")
        self.con.write(address, value, check)

    def read_thread_engine_register(self, reg):
        address = self.base + reg * 4
        return self.con.read(address)

    def dispatch_threads(self, pc, dp_addr, tblocks_to_dispatch, tgroup_id, inorder):
        print(f"Dispatching threads: PC={pc:#010x}, DP_ADDR={dp_addr:#010x}, TBlocks={tblocks_to_dispatch}, TGroupID={tgroup_id}")
        self.write_thread_engine_register(0, pc)
        self.write_thread_engine_register(1, dp_addr)
        self.write_thread_engine_register(2, tblocks_to_dispatch)
        self.write_thread_engine_register(3, tgroup_id)

        # Dispatch the threads
        print("Dispatching threads...")
        self.write_thread_engine_register(4, 1 if inorder else 0, check=False)

    def dispatch_status(self):
        status = self.read_thread_engine_register(4)
        status_bin = bin(status)[2:].zfill(32)

        print(f"Dispatch status: {status:#010x} ({status_bin})")

        # Reverse the status bits
        new_status_bin = ''
        for i in range(32):
            new_status_bin += status_bin[31 - i]

        start_dispatch = new_status_bin[0] == '1'
        running = new_status_bin[1] == '1'
        finished = new_status_bin[2] == '1'
        num_dispatched = (status >> 4) & 0xF
        num_finished = (status >> 24) & 0xF

        print(f"Start: {start_dispatch}, Running: {running}, Finished: {finished}, Dispatched: {num_dispatched}, Finished: {num_finished}")

        return start_dispatch, running, finished, num_dispatched, num_finished

con = None
if emu:
    print("Using BGPU emulator")
    con = BGPUEmu()
else:
    con = GDB()

bgpu = BGPU(con)

running = bgpu.dispatch_status()[1]
assert not running, "GPU is already running, please stop it first."

offset = 0
print("Writing program to memory:")
for inst in prog:
    print(f"{offset:#010x} = {inst:#010x}")
    con.write(offset, inst)
    offset += 4

print("Writing data to memory:")
for j in range(3):
    print(f"Matrix {j}:")
    for i in range(DataPerMatrix):
        data = i + 1 # + (j << 24)
        print(f"{i}: {offset:#010x} = {data:#010x}")
        con.write(offset, data)
        offset += 4

print("Writing matrix addresses to memory:")
dp_address = offset
for j in range(3):
    matrix_address = (len(prog) + j * DataPerMatrix) * 4
    print(f"Matrix {j} address: {matrix_address:#010x}, {offset:#010x} = {matrix_address:#010x}")
    con.write(offset, matrix_address)
    offset += 4

print("Dispatching threads...")
bgpu.dispatch_threads(0, dp_address, Tblocks, 42, inorder)

bgpu.dispatch_status()

print("Checking program:")
for i in range(len(prog)):
    value = con.read(i * 4)
    if value != prog[i]:
        print(f"Program mismatch at {i}: expected {prog[i]:#010x}, got {value:#010x}")
    else:
        print(f"Program match at {i}: {value:#010x}")

print("Reading back data from memory:")
for j in range(3):
    print(f"Matrix {j}:")
    for i in range(DataPerMatrix):
        value = con.read((len(prog) + j * DataPerMatrix + i) * 4)
        print(f"{i}: {value:#010x}")
