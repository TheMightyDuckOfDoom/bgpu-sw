from bgpu_emu import EmuMemory, BgpuEmu as CU


class BGPUDriver:
    def __init__(self):
        self.mem = EmuMemory()
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
        warp_width = tblock_size # assuming warp width equals local size for now
        num_blocks = global_size[0]
        print(f"Executing kernel with warp width: {warp_width} and tblock size: {tblock_size}")
        cu = CU(warp_width)

        cu.dispatch_and_execute(kernel_address, parameter_address, tblock_size, num_blocks, 0, self.mem.get_memory())

        print("Kernel execution completed.")

    def alloc(self, size: int):
        return self.mem.alloc(size)

    def copy_h2d(self, dest, src:memoryview):
        self.mem.copy_h2d(dest, src)

    def copy_d2h(self, dest:memoryview, src):
        self.mem.copy_d2h(dest, src)
