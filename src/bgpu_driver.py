from bgpu_emu import CU

class EmulatorMemory:
    def __init__(self):
        self.mem = []
        self.allocations = []

    def alloc(self, size: int):
        print(f"Allocating {size} bytes of BGPU memory.")
        # Find next available address -> outside memory
        addr = len(self.mem)
        # Expand memory
        size_in_mem = size + (4 - (size % 4)) % 4  # align to 4 bytes
        self.mem.extend([0] * size_in_mem)
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
        self.mem[addr:addr+src_size] = src

        for idx, data in enumerate(self.mem[addr:addr+src_size]):
            print(f"{idx}: {data}")

        print(f"Copied data to device memory at address {addr:#010x}.")

    def copy_d2h(self, dest:memoryview, src):
        addr, src_size = src
        print(f"Copying {len(dest)} bytes from device at address {addr:#010x} to host.")
        dest_len = len(dest)
        assert dest_len <= src_size, "Destination buffer is smaller than source data."
        for idx, data in enumerate(self.mem[addr:addr+dest_len]):
            dest[idx] = data
        print(f"Copied data from device memory at address {addr:#010x} to host.")

    def get_memory(self):
        return self.mem

class BGPUDriver:
    def __init__(self):
        self.mem = EmulatorMemory()
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
        warp_width = local_size[0]
        num_blocks = global_size[0]
        print(f"Executing kernel with warp width: {warp_width}")
        cu = CU(warp_width)

        cu.dispatch_and_execute(kernel_address, parameter_address, num_blocks, 0, self.mem.get_memory())

        print("Kernel execution completed.")

    def alloc(self, size: int):
        return self.mem.alloc(size)

    def copy_h2d(self, dest, src:memoryview):
        self.mem.copy_h2d(dest, src)

    def copy_d2h(self, dest:memoryview, src):
        self.mem.copy_d2h(dest, src)
