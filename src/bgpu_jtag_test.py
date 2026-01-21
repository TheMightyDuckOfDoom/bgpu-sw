#!/usr/bin/env python3

from pygdbmi.gdbcontroller import GdbController
from bgpu_driver import Bgpu
from bgpu_emu import EmuJtag
from bgpu_jtag import GdbJtag

Tblocks = 0
TblockSize = 0
DataPerMatrix = 0
prog = []

ex_prog = 'add_2'
emu = False
inorder = False

if ex_prog == 'add_16':
    DataPerMatrix = 16 ** 2
    Tblocks = 16
    TblockSize = 4
    prog = [
        0x46000000,
        0x46010001,
        0x46020002,
        0x0C030001,
        0x0C040002,
        0x0C050003,
        0x0C060004,
        0x0C070010,
        0x02080000,
        0x00090000,
        0x0B0A0807,
        0x0B070906,
        0x04060A07,
        0x04070603,
        0x12030702,
        0x04030103,
        0x42080303,
        0x04030604,
        0x12040302,
        0x04040104,
        0x42090404,
        0x04040605,
        0x12050402,
        0x04050105,
        0x420A0505,
        0x12050602,
        0x04050105,
        0x42010505,
        0x12050702,
        0x04050205,
        0x420B0505,
        0x12050302,
        0x04050205,
        0x420C0505,
        0x12050402,
        0x04050205,
        0x420D0505,
        0x12050602,
        0x04050205,
        0x42020505,
        0x12050702,
        0x04050005,
        0x12070302,
        0x04070007,
        0x12030402,
        0x04030003,
        0x12040602,
        0x04040004,
        0x0400080B,
        0x0406090C,
        0x04080A0D,
        0x04090102,
        0x45050500,
        0x45070706,
        0x45030308,
        0x45040409,
        0xBF000000
    ]

if ex_prog == 'add_8':
    DataPerMatrix = 8 ** 2
    Tblocks = 4
    TblockSize = 4
    prog = [
        0x46000000,
        0x46010001,
        0x46020002,
        0x0C030001,
        0x0C040002,
        0x0C050003,
        0x0C060004,
        0x0C070010,
        0x02080000,
        0x00090000,
        0x0B0A0807,
        0x0B070906,
        0x04060A07,
        0x04070603,
        0x12030702,
        0x04030103,
        0x42080303,
        0x04030604,
        0x12040302,
        0x04040104,
        0x42090404,
        0x04040605,
        0x12050402,
        0x04050105,
        0x420A0505,
        0x12050602,
        0x04050105,
        0x42010505,
        0x12050702,
        0x04050205,
        0x420B0505,
        0x12050302,
        0x04050205,
        0x420C0505,
        0x12050402,
        0x04050205,
        0x420D0505,
        0x12050602,
        0x04050205,
        0x42020505,
        0x12050702,
        0x04050005,
        0x12070302,
        0x04070007,
        0x12030402,
        0x04030003,
        0x12040602,
        0x04040004,
        0x0400080B,
        0x0406090C,
        0x04080A0D,
        0x04090102,
        0x45050500,
        0x45070706,
        0x45030308,
        0x45040409,
        0xBF000000
    ]

if ex_prog == 'add_4':
    Tblocks = 1
    TblockSize = 4
    DataPerMatrix = 4 ** 2
    prog = [
        0x46000000,
        0x46010001,
        0x46020002,
        0x0C030001,
        0x0C040002,
        0x0C050003,
        0x0C060004,
        0x00070000,
        0x0B080706,
        0x04060803,
        0x12030602,
        0x04030103,
        0x42070303,
        0x04030804,
        0x12040302,
        0x04040104,
        0x42090404,
        0x04040805,
        0x12050402,
        0x04050105,
        0x420A0505,
        0x12050802,
        0x04050105,
        0x42010505,
        0x12050602,
        0x04050205,
        0x420B0505,
        0x12050302,
        0x04050205,
        0x420C0505,
        0x12050402,
        0x04050205,
        0x420D0505,
        0x12050802,
        0x04050205,
        0x42020505,
        0x12050602,
        0x04050005,
        0x12060302,
        0x04060006,
        0x12030402,
        0x04030003,
        0x12040802,
        0x04040004,
        0x0400070B,
        0x0407090C,
        0x04080A0D,
        0x04090102,
        0x45050500,
        0x45060607,
        0x45030308,
        0x45040409,
        0xBF000000
    ]

if ex_prog == 'add_2':
    Tblocks = 1
    TblockSize = 1
    DataPerMatrix = 2 ** 2
    prog = [
        0x46000000,
        0x46010001,
        0x46020002,
        0x0C030000,
        0x0C040001,
        0x0C050002,
        0x0C060003,
        0x12070302,
        0x04070107,
        0x42080707,
        0x12070402,
        0x04070107,
        0x42090707,
        0x12070502,
        0x04070107,
        0x420A0707,
        0x12070602,
        0x04070107,
        0x42010707,
        0x12070302,
        0x04070207,
        0x420B0707,
        0x12070402,
        0x04070207,
        0x420C0707,
        0x12070502,
        0x04070207,
        0x420D0707,
        0x12070602,
        0x04070207,
        0x42020707,
        0x12070302,
        0x04070007,
        0x12030402,
        0x04030003,
        0x12040502,
        0x04040004,
        0x12050602,
        0x04050005,
        0x0400080B,
        0x0406090C,
        0x04080A0D,
        0x04090102,
        0x45070700,
        0x45030306,
        0x45040408,
        0x45050509,
        0xBF000000
    ]

con = None
if emu:
    print("Using BGPU emulator")
    con = EmuJtag()
else:
    con = GdbJtag()

bgpu = Bgpu(con)

running = bgpu.dispatch_status()[1]
assert not running, "GPU is already running, please stop it first."

# for i in range(len(prog)):
#     con.write(i * 4, prog[i], check=False)
#     value = con.read(i * 4)
#     print(f"Program {i}: {value:#010x} (expected {prog[i]:#010x})")

offset = 0
print("Writing data to memory:")
matrix_start = offset
for j in range(3):
    print(f"Matrix {j}:")
    for i in range(DataPerMatrix):
        data = i + 1 # + (j << 24)
        print(f"{i}: {offset:#010x} = {data:#010x}")
        con.write(offset, data)
        offset += 4

print("Writing program to memory:")
pc_start = offset
for inst in prog:
    print(f"{offset:#010x} = {inst:#010x}")
    try:
        con.write(offset, inst)
    except ValueError as e:
        print(f"Error writing instruction {inst:#010x} at offset {offset:#010x}: {e}")
    offset += 4

print("Writing matrix addresses to memory:")
dp_address = offset
for j in range(3):
    matrix_address = matrix_start + j * DataPerMatrix * 4
    print(f"Matrix {j} address: {matrix_address:#010x}, {offset:#010x} = {matrix_address:#010x}")
    con.write(offset, matrix_address)
    offset += 4

print("Dispatching threads...")
bgpu.dispatch_threads(pc_start, dp_address, TblockSize, Tblocks, 42, inorder)

print("Waiting for completion...")
while True:
    start_dispatch, running, finished, num_dispatched, num_finished = bgpu.dispatch_status()
    if finished:
        break

print("Checking program:")
for i in range(len(prog)):
    value = con.read(pc_start + i * 4)
    if value != prog[i]:
        print(f"Program mismatch at {i}: expected {prog[i]:#010x}, got {value:#010x}")
    else:
        print(f"Program match at {i}: {value:#010x}")

print("Reading back data from memory:")
for j in range(3):
    print(f"Matrix {j}:")
    for i in range(DataPerMatrix):
        value = con.read(matrix_start + j * DataPerMatrix * 4 + i * 4)
        print(f"{i}: {value:#010x}")
