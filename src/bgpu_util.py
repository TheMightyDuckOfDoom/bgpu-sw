import struct

def float_to_hex(f):
    return hex(struct.unpack('<I', struct.pack('<f', f))[0])

def hex_to_float(h):
    return struct.unpack('<f', struct.pack('<I', h))[0]

