#!/usr/bin/env python3

from bgpu_instructions import *

def parse_instruction(line: str) -> Instruction:
    print(f"Parsing line: {line.strip()}")
    parts = line.split()
    print(f"Parts: {parts}")
    opcode_str = parts[0].split(".")[0]
    opcode_modifiers = parts[0].split(".")[1:] if "." in parts[0] else []

    # opcode dst, op2, op1

    dst = parts[1].replace(",", "") if len(parts) > 1 else ""
    op2 = parts[2].replace(",", "") if len(parts) > 2 else ""
    op1 = parts[3].replace(",", "") if len(parts) > 3 else ""

    width = None
    if "int32" in opcode_modifiers:
        width = "int32"
    if "int16" in opcode_modifiers:
        assert width is None, "Cannot specify multiple widths"
        width = "int16"
    if "uint16" in opcode_modifiers:
        assert width is None, "Cannot specify multiple widths"
        width = "uint16"
    if "int8" in opcode_modifiers:
        assert width is None, "Cannot specify multiple widths"
        width = "int8"
    if "uint8" in opcode_modifiers:
        assert width is None, "Cannot specify multiple widths"
        width = "uint8"

    is_ri = False
    if "ri" in opcode_modifiers:
        is_ri = True
        if "rr" in opcode_modifiers:
            raise ValueError("Cannot specify both 'ri' and 'rr' modifiers")

    for opcode in OpCode:
        if opcode_str == opcode.value[0]:
            return Instruction(opcode, dst, op1, op2, width, is_ri)

    raise ValueError(f"Unknown opcode: {opcode_str}") 

def asm2hex(asm_code: str) -> list[str]:
    program = []
    for line in asm_code.splitlines():
        line = line.strip()
        if line == "":
            continue
        inst = parse_instruction(line)
        print(f"Parsed instruction: {inst}")
        program.append(inst)

    for inst in program:
        print(f"Instruction: {inst.encode()} {inst.text}, EU: {inst.eu}, Subtype: {inst.subtype}, Dst: {inst.dst}", end="")
        if inst.op2 != "":
            print(f", Op2: {inst.op2}", end="")
        if inst.op1 != "":
            print(f", Op1: {inst.op1}", end="")
        print()

    return [inst.encode() for inst in program]

# 2x2 matrix addition
# example_asm = """
# special                   r0, %param
# ld.int32.param            r1,   r0
# add.ri.int32              r2,   r0, 4
# ld.int32.param            r2,   r2
# add.ri.int32              r0,   r0, 8
# ld.int32.param            r0,   r0
# add.ri.int32              r3,   r2, 0
# ld.int32.global           r3,   r3
# add.ri.int32              r4,   r2, 4
# ld.int32.global           r4,   r4
# add.ri.int32              r5,   r2, 8
# ld.int32.global           r5,   r5
# add.ri.int32              r2,   r2, 12
# ld.int32.global           r2,   r2
# add.ri.int32              r6,   r0, 0
# ld.int32.global           r6,   r6
# add.ri.int32              r7,   r0, 4
# ld.int32.global           r7,   r7
# add.ri.int32              r8,   r0, 8
# ld.int32.global           r8,   r8
# add.ri.int32              r0,   r0, 12
# ld.int32.global           r0,   r0
# add.ri.int32              r9,   r1, 0
# add.ri.int32             r10,   r1, 4
# add.ri.int32             r11,   r1, 8
# add.ri.int32              r1,   r1, 12
# add.rr.int32              r3,   r3,   r6
# st.int32.global           r9,   r3
# add.rr.int32              r3,   r4,   r7
# st.int32.global          r10,   r3
# add.rr.int32              r3,   r5,   r8
# st.int32.global          r11,   r3
# add.rr.int32              r0,   r2,   r0
# st.int32.global           r1,   r0
# stop
# """

# 4x4 matrix addition
example_asm = """
special                   r0, %param
ld.int32.param            r1,   r0
add.ri.int32              r2,   r0, 4
ld.int32.param            r2,   r2
add.ri.int32              r3,   r0, 8
ld.int32.param            r3,   r3
special                   r0, %lidx0
shl.ri.int32              r4,   r0,    2
shl.ri.int32              r5,   r4,    2
add.rr.int32              r5,   r2,   r5
ld.int32.global           r6,   r5
shl.ri.int32              r5,   r4,    2
add.rr.int32              r5,   r3,   r5
ld.int32.global           r7,   r5
add.ri.int32              r5,   r4,    1
shl.ri.int32              r8,   r5,    2
add.rr.int32              r8,   r2,   r8
ld.int32.global           r9,   r8
shl.ri.int32              r8,   r5,    2
add.rr.int32              r8,   r3,   r8
ld.int32.global          r10,   r8
add.ri.int32              r8,   r4,    2
shl.ri.int32             r11,   r8,    2
add.rr.int32             r11,   r2,  r11
ld.int32.global          r12,  r11
shl.ri.int32             r11,   r8,    2
add.rr.int32             r11,   r3,  r11
ld.int32.global          r13,  r11
add.ri.int32             r11,   r4,    3
shl.ri.int32             r14,  r11,    2
add.rr.int32             r14,   r2,  r14
ld.int32.global           r2,  r14
shl.ri.int32             r14,  r11,    2
add.rr.int32             r14,   r3,  r14
ld.int32.global           r3,  r14
shl.ri.int32             r14,   r5,    2
add.rr.int32             r14,   r1,  r14
shl.ri.int32              r5,   r8,    2
add.rr.int32              r5,   r1,   r5
shl.ri.int32              r8,  r11,    2
add.rr.int32              r8,   r1,   r8
shl.ri.int32             r11,   r4,    2
add.rr.int32             r11,   r1,  r11
add.rr.int32              r1,   r9,  r10
st.int32.global          r14,   r1
add.rr.int32              r1,  r12,  r13
st.int32.global           r5,   r1
add.rr.int32              r1,   r2,   r3
st.int32.global           r8,   r1
add.rr.int32              r1,   r6,   r7
st.int32.global          r11,   r1
stop
"""

# example_asm = """
# special r0, %lidx0
# add.ri.int32 r1, r0, 4
# st.int8.global r0, r1
# stop
# """

example_asm = """
special                   r0, %param
ld.int32.param            r1,   r0
add.ri.int32              r2,   r0, 4
ld.int32.param            r2,   r2
add.ri.int32              r3,   r0, 8
ld.int32.param            r3,   r3
special                   r0, %gidx0
special                   r4, %lidx0
shl.ri.int32              r5,   r0,    4
shl.ri.int32              r6,   r4,    2
add.rr.int32              r7,   r5,   r6
shl.ri.int32              r5,   r7,    2
add.rr.int32              r5,   r2,   r5
ld.int32.global           r6,   r5
shl.ri.int32              r5,   r7,    2
add.rr.int32              r5,   r3,   r5
ld.int32.global           r8,   r5
add.ri.int32              r5,   r7,    1
shl.ri.int32              r9,   r5,    2
add.rr.int32              r9,   r2,   r9
ld.int32.global          r10,   r9
shl.ri.int32              r9,   r5,    2
add.rr.int32              r9,   r3,   r9
ld.int32.global          r11,   r9
add.ri.int32              r9,   r7,    2
shl.ri.int32             r12,   r9,    2
add.rr.int32             r12,   r2,  r12
ld.int32.global          r13,  r12
shl.ri.int32             r12,   r9,    2
add.rr.int32             r12,   r3,  r12
ld.int32.global          r14,  r12
add.ri.int32             r12,   r7,    3
shl.ri.int32             r15,  r12,    2
add.rr.int32             r15,   r2,  r15
ld.int32.global           r2,  r15
shl.ri.int32             r15,  r12,    2
add.rr.int32             r15,   r3,  r15
ld.int32.global           r3,  r15
shl.ri.int32             r15,   r5,    2
add.rr.int32             r15,   r1,  r15
shl.ri.int32              r5,   r9,    2
add.rr.int32              r5,   r1,   r5
shl.ri.int32              r9,  r12,    2
add.rr.int32              r9,   r1,   r9
shl.ri.int32             r12,   r7,    2
add.rr.int32             r12,   r1,  r12
add.rr.int32              r1,  r10,  r11
st.int32.global          r15,   r1
add.rr.int32              r1,  r13,  r14
st.int32.global           r5,   r1
add.rr.int32              r1,   r2,   r3
st.int32.global           r9,   r1
add.rr.int32              r1,   r6,   r8
st.int32.global          r12,   r1
stop
"""

example_asm = """
special                   r0, %param
ld.int32.param            r1,   r0
add.ri.int32              r2,   r0, 4
ld.int32.param            r2,   r2
add.ri.int32              r3,   r0, 8
ld.int32.param            r3,   r3
special                   r0, %gidx0
special                   r4, %lidx0
shl.ri.int32              r5,   r0,    4
shl.ri.int32              r6,   r4,    2
add.rr.int32              r7,   r5,   r6
shl.ri.int32              r5,   r7,    2
add.rr.int32              r5,   r2,   r5
ld.int32.global           r6,   r5
shl.ri.int32              r5,   r7,    2
add.rr.int32              r5,   r3,   r5
ld.int32.global           r8,   r5
add.ri.int32              r5,   r7,    1
shl.ri.int32              r9,   r5,    2
add.rr.int32              r9,   r2,   r9
ld.int32.global          r10,   r9
shl.ri.int32              r9,   r5,    2
add.rr.int32              r9,   r3,   r9
ld.int32.global          r11,   r9
add.ri.int32              r9,   r7,    2
shl.ri.int32             r12,   r9,    2
add.rr.int32             r12,   r2,  r12
ld.int32.global          r13,  r12
shl.ri.int32             r12,   r9,    2
add.rr.int32             r12,   r3,  r12
ld.int32.global          r14,  r12
add.ri.int32             r12,   r7,    3
shl.ri.int32             r15,  r12,    2
add.rr.int32             r15,   r2,  r15
ld.int32.global           r2,  r15
shl.ri.int32             r15,  r12,    2
add.rr.int32             r15,   r3,  r15
ld.int32.global           r3,  r15
shl.ri.int32             r15,   r5,    2
add.rr.int32             r15,   r1,  r15
shl.ri.int32              r5,   r9,    2
add.rr.int32              r5,   r1,   r5
shl.ri.int32              r9,  r12,    2
add.rr.int32              r9,   r1,   r9
shl.ri.int32             r12,   r7,    2
add.rr.int32             r12,   r1,  r12
add.rr.int32              r1,  r10,  r11
st.int32.global          r15,   r1
add.rr.int32              r1,  r13,  r14
st.int32.global           r5,   r1
add.rr.int32              r1,   r2,   r3
st.int32.global           r9,   r1
add.rr.int32              r1,   r6,   r8
st.int32.global          r12,   r1
stop
"""

if __name__ == "__main__":
    print("Assembling example ASM code...")
    hex_program = asm2hex(example_asm)
    print("Hex program:")
    for idx, line in enumerate(hex_program):
        print((f"'h{line},") if idx < len(hex_program) - 1 else f"'h{line} ", end=" ")
        print(f"// {example_asm.split('\n')[idx + 1]}")
    print("Done.")