import struct

def float_to_hex(f):
    return hex(struct.unpack('<I', struct.pack('<f', f))[0])
