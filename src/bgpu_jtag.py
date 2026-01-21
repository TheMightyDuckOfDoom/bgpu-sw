#!/usr/bin/env python3

from pygdbmi.gdbcontroller import GdbController

class GdbJtag:
    def __init__(self):
        import sys
        bin = 'gdb' if sys.platform == 'darwin' else 'gdb-multiarch'
        self.gdb = GdbController([bin, '--interpreter=mi3', '--nx', '--quiet'])
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
