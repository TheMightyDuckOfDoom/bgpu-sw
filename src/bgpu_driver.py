from bgpu_emu import CU, EmuJtag
from bgpu_jtag import GdbJtag

class Bgpu:
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

    def dispatch_threads(self, pc, dp_addr, tblock_size, tblocks_to_dispatch, tgroup_id, inorder):
        print(f"Dispatching threads: PC={pc:#010x}, DP_ADDR={dp_addr:#010x}, TBlockSize={tblock_size}, TBlocks={tblocks_to_dispatch}, TGroupID={tgroup_id}")
        self.write_thread_engine_register(0, pc)
        self.write_thread_engine_register(1, dp_addr)
        self.write_thread_engine_register(2, tblocks_to_dispatch)
        self.write_thread_engine_register(3, tgroup_id)
        self.write_thread_engine_register(4, tblock_size)

        # Dispatch the threads
        print("Dispatching threads...")
        self.write_thread_engine_register(5, 1 if inorder else 0, check=False)

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

class BgpuMemManager:
    def __init__(self, con):
        self.con = con
        self.allocations = []
        self.top_of_mem = 0

    def alloc(self, size: int):
        print(f"Allocating {size} bytes of BGPU memory.")
        assert size % 4 == 0, "Allocation size must be a multiple of 4 bytes."
        # Find next available address -> outside memory
        addr = self.top_of_mem
        # Expand memory
        self.top_of_mem += size
        # Record allocation
        buf = (addr, size)
        self.allocations.append(buf)
        print(f"Allocated buffer at address {addr:#010x} of size {size} bytes.")
        return buf

    def copy_h2d(self, dest, src:memoryview):
        addr, dest_size = dest
        print(f"Copying {len(src)} bytes from host to device at address {addr:#010x}.")
        src_size = len(src)
        assert src_size <= dest_size, "Source data is larger than allocated buffer."
        assert src_size % 4 == 0, "Source data size must be a multiple of 4 bytes."
        for i in range(src_size // 4):
            data = int.from_bytes(src[i*4:i*4+4], byteorder='little')
            self.con.write(addr + i * 4, data)

        print(f"Copied data to device memory at address {addr:#010x}.")

    def copy_d2h(self, dest:memoryview, src):
        addr, src_size = src
        print(f"Copying {len(dest)} bytes from device at address {addr:#010x} to host.")
        dest_len = len(dest)
        assert dest_len <= src_size, "Destination buffer is smaller than source data."
        assert dest_len % 4 == 0, "Destination data size must be a multiple of 4 bytes."
        for i in range(dest_len // 4):
            data = self.con.read(addr + i * 4)
            for j in range(4):
                dest[i*4 + j] = (data >> (j * 8)) & 0xFF

        print(f"Copied data from device memory at address {addr:#010x} to host.")

class BGPUDriver:
    def __init__(self, emu=False):
        if emu:
            self.con = EmuJtag()
        else:
            self.con = GdbJtag()
        self.bgpu = Bgpu(self.con)
        self.mem = BgpuMemManager(self.con)
        print("BGPU Driver initialized.")

    def run_kernel(self, *args, global_size:tuple[int,int,int], local_size:tuple[int,int,int], program, function_name:str):
        print(f"BGPUDriver running kernel: {function_name}")
        print(program)
        print(f"Global size: {global_size}, Local size: {local_size}")
        print(f"Kernel arguments: {args}")

        # Allocate memory for the kernel
        arg_bufs = args[0]
        kernel_len = len(program)
        allocate_len = kernel_len + len(arg_bufs) * 4 # assuming 4 bytes per argument -> pointer size
        kernel_mem = self.mem.alloc(allocate_len)
        kernel_address = kernel_mem[0]

        kernel_bytes = bytearray(allocate_len)
        
        # Copy program
        for i, instr in enumerate(program):
            kernel_bytes[i] = instr
            print(f"Kernel Byte {i}: {instr:#04x}")

        # Copy arguments
        parameter_address = kernel_len
        for i, arg in enumerate(arg_bufs):
            print(f"Argument {i}: {arg}")
            buf_addr, buf_size = arg
            buf_bytes = buf_addr.to_bytes(4, byteorder='little')
            for j in range(4):
                print(f"Arg {i} Byte {j}: {buf_bytes[j]:#04x}")
                kernel_bytes[parameter_address + i*4 + j] = buf_bytes[j]

        # Adjust parameter address to be absolute
        parameter_address += kernel_address

        # Copy kernel to device memory
        self.mem.copy_h2d(kernel_mem, kernel_bytes)

        # Execute kernel
        tblock_size = local_size[0]
        num_blocks = global_size[0]
        print(f"Executing kernel with tblock size: {tblock_size}")

        self.bgpu.dispatch_threads(kernel_address, parameter_address, tblock_size, num_blocks, 0, inorder=True)

        print("Kernel execution completed.")

    def alloc(self, size: int):
        return self.mem.alloc(size)

    def copy_h2d(self, dest, src:memoryview):
        self.mem.copy_h2d(dest, src)

    def copy_d2h(self, dest:memoryview, src):
        self.mem.copy_d2h(dest, src)
