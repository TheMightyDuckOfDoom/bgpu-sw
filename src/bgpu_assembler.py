#!/usr/bin/env python3

from bgpu_instructions import *

def parse_instruction(line: str) -> Instruction:
    print(f"Parsing line: {line.strip()}")
    parts = line.split('#')[0].strip().split()
    print(f"Parts: {parts}")

    if parts[0][-1] == ':':
        # It's a label, skip
        print(f"Found label: {parts[0]}")
        return None

    opcode_str = parts[0].split(".")[0]
    opcode_modifiers = parts[0].split(".")[1:] if "." in parts[0] else []

    # opcode dst, op2, op1

    dst = parts[1].replace(",", "") if len(parts) > 1 else ""
    op2 = parts[2].replace(",", "") if len(parts) > 2 else ""
    op1 = parts[3].replace(",", "") if len(parts) > 3 else ""

    width = None
    print(f"Opcode modifiers: {opcode_modifiers}")
    for modifier in opcode_modifiers:
        if modifier in ["int32", "int16", "uint16", "int8", "uint8", "float32", "long"]:
            assert width is None, "Multiple width modifiers specified"
            width = modifier

    is_ri = False
    if "ri" in opcode_modifiers:
        is_ri = True
        if "rr" in opcode_modifiers:
            raise ValueError("Cannot specify both 'ri' and 'rr' modifiers")

    if opcode_str == "ldparam":
        is_ri = True

    for opcode in OpCode:
        if opcode_str == opcode.value[0]:
            return Instruction(opcode, dst, op1, op2, width, is_ri, opcode_modifiers)

    raise ValueError(f"Unknown opcode: {opcode_str}") 

def asm2hex(asm_code: str) -> list[str]:
    program = []
    for line in asm_code.splitlines():
        line = line.strip()
        if line == "":
            continue
        inst = parse_instruction(line)
        print(f"Parsed instruction: {inst}")
        if inst is not None:
            if isinstance(inst, list):
                for i in inst:
                    program.append((i, line))
            else:
                program.append((inst, line))

    for inst, line in program:
        print(f"Instruction: {inst.encode()} {inst.text}, EU: {inst.eu}, Subtype: {inst.subtype}, Dst: {inst.dst}", end="")
        if inst.op2 != "":
            print(f", Op2: {inst.op2}", end="")
        if inst.op1 != "":
            print(f", Op1: {inst.op1}", end="")
        print(" <- " + line)

    return [inst.encode() + " // " + line for inst, line in program]

example_asm = """
r_4_2_2_4_8:
        ldparam   r0, 0 # define global
        ldparam   r1, 1 # define global
        ldparam   r2, 2 # define global
        mov.ri.float32  r3, 0 # define register
        mov.ri.float32    r4, 0f00000000 # constant
        mov.ri.int32      r5, 1 # constant
        mov.ri.long       r6, 1 # constant
        mov.ri.int32      r7, 2 # constant
        mov.ri.long       r8, 2 # constant
        mov.ri.int32      r9, 3 # constant
        mov.ri.long      r10, 3 # constant
        mov.ri.int32     r11, 4 # constant
        special                  r12, %g
        special                  r13, %l
        mov.ri.long      r14, 4 # constant
        mov.ri.int32     r15, 8 # constant
        mov.rr                    r3,   r4 # store register into register
        add.rr.int32             r16,   r3,   r5 # index
        mov.rr                    r3,   r4 # store register into register
        add.rr.int32             r17,   r3,   r7 # index
        mov.rr                    r3,   r4 # store register into register
        add.rr.int32             r18,   r3,   r9 # index
        mov.rr                    r3,   r4 # store register into register
        shl.rr.long              r19,  r12,  r14
        shr.rr.int32             r20,  r13,   r5
        shl.rr.long              r21,  r20,   r8
        and.rr.int32             r22,  r13,   r5
        shl.rr.int32             r23,  r22,   r9
        add.rr.long              r24,  r19,  r23
        mov.ri.int32             r25,    0 # init range
loop_r25:
        add.rr.long              r26,  r24,  r25
        add.rr.int32             r27,   r1,  r26 # index
        ld.float32.global                r28,  r27
        shl.rr.int32             r29,  r25,   r9
        add.rr.long              r30,  r21,  r29
        add.rr.int32             r31,   r2,  r30 # index
        ld.float32.global                r32,  r31
        add.rr.long              r33,  r30,   r6
        add.rr.int32             r34,   r2,  r33 # index
        ld.float32.global                r35,  r34
        add.rr.long              r36,  r30,   r8
        add.rr.int32             r37,   r2,  r36 # index
        ld.float32.global                r38,  r37
        add.rr.long              r39,  r30,  r10
        add.rr.int32             r40,   r2,  r39 # index
        ld.float32.global                r41,  r40
        mul.rr.float32           r42,  r28,  r35
        add.rr.float32           r43,   r3,  r42
        mov.rr                    r3,  r43 # store register into register
        mul.rr.float32           r44,  r28,  r38
        add.rr.float32           r45,   r3,  r44
        mov.rr                    r3,  r45 # store register into register
        mul.rr.float32           r46,  r28,  r41
        add.rr.float32           r47,   r3,  r46
        mov.rr                    r3,  r47 # store register into register
        mul.rr.float32           r48,  r28,  r32
        add.rr.float32           r49,   r3,  r48
        mov.rr                    r3,  r49 # store register into register
checkloop_r25:
        add.ri.int32             r25,  r25,    1 # increment
        sub.rr.int32             r50,  r25,  r15 # compare bound
        br.nz.loop_r25           r50 # loop back if not done
endloop_r25:
        add.rr.long              r50,  r24,  r21
        add.rr.int32             r51,   r0,  r50 # index
        st.float32.global                r51,   r3
        add.rr.long              r52,  r50,   r6
        add.rr.int32             r53,   r0,  r52 # index
        st.float32.global                r53,   r3
        add.rr.long              r54,  r50,   r8
        add.rr.int32             r55,   r0,  r54 # index
        st.float32.global                r55,   r3
        add.rr.long              r56,  r50,  r10
        add.rr.int32             r57,   r0,  r56 # index
        st.float32.global                r57,   r3
        stop
"""

if __name__ == "__main__":
    print("Assembling example ASM code...")
    hex_program = asm2hex(example_asm)
    for addr, hex_inst in enumerate(hex_program):
        print(f"{addr:04x}: {hex_inst}")
    print("Done.")