# Copyright 2025 Tobias Senti
from util import ParsedInstruction, Modifier, Operand

class Parser():
    def parse_file(self, filepath: str) -> list[ParsedInstruction]:
        with open(filepath, 'r') as file:
            lines = file.readlines()
            return self.parse_lines(lines)

    def parse_lines(self, lines: list[str]) -> list[ParsedInstruction]:
        last_label = None
        instructions = []
        for line in lines:
            line = line.strip()
            print(f"Parsing line: {line}")
            line = line.split('#')[0].strip() # Remove comments
            
            # Skip empty lines
            if len(line) == 0:
                continue

            parts = line.split()

            # We have a lable in this line
            if len(parts) == 1 and parts[0].endswith(':'):
                print(f"Found label: {parts[0]}")
                last_label = parts[0][:-1]
                continue

            # Split of instruction, modifiers and operands
            opcode_parts = parts[0].split('.')
            instruction = opcode_parts[0]
            modifiers = opcode_parts[1:] if len(opcode_parts) > 1 else []
            operands = [part.replace(',', '') for part in parts[1:]]

            # Parse modifiers and operands
            mod_objs = [Modifier(mod) for mod in modifiers]
            op_objs = [Operand(op) for op in operands]

            # Create ParsedInstruction
            parsed_inst = ParsedInstruction(instruction, mod_objs, op_objs, line, last_label)
            last_label = None
            instructions.append(parsed_inst)

        # Return parsed instructions and label map
        return instructions
