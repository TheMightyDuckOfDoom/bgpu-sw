#!/usr/bin/env python3

import json

# Compares a reg_trace.log to results_cc*_cu*.log file

def parse_reg_trace(reg_trace_file_name):
    with open(reg_trace_file_name, 'r') as f:
        reg_trace = json.load(f)
    return reg_trace

def parse_results_file(results_file_name):
    results_lines = []
    with open(results_file_name, 'r') as f:
        results_lines = f.readlines()

    results = {}
    for timestamp, line in enumerate(results_lines):
        line = line.strip().replace(',', '').replace(')', '').split()
        print(line)
        if '0' in line[6]:
            raise Exception("Active mask not implemented")

        warp = line[4]
        dst = line[8].replace('r', '')

        print(f"Warp: {warp}, Dst: {dst}")

        if warp not in results:
            results[warp] = {}

        for thread in range(len(line[6])):
            data = int(line[11 + thread * 2], 16)
            thread = str(thread)
            print(f"Thread {thread} Dst=r{dst} set to {data:#010x}")
            if thread not in results[warp]:
                results[warp][thread] = {}
            if dst not in results[warp][thread]:
                results[warp][thread][dst] = []
            results[warp][thread][dst].append((timestamp + 1, data))
    
    return results

def compare_reg_traces(emu_trace, sim_trace):
    print("Comparing emulator trace with simulation trace...")
    print(f"Emulator trace: {emu_trace}")
    print(f"Simulation trace: {sim_trace}")

    for tblock in emu_trace:
        if tblock not in sim_trace:
            raise Exception(f"TBlock {tblock} not found in simulation trace")

        for thread in emu_trace[tblock]:
            if thread not in sim_trace[tblock]:
                raise Exception(f"Thread {thread} in TBlock {tblock} not found in simulation trace")

            value_mismatch = False
            earliest_mismatch_emu = None # Timestamp of the first mismatch in emulator trace
            earliest_mismatch_sim = None # Timestamp of the first mismatch in simulation trace
            for reg in emu_trace[tblock][thread]:
                if reg not in sim_trace[tblock][thread]:
                    raise Exception(f"Register {reg} in Thread {thread} of TBlock {tblock} not found in simulation trace")

                emu_values = emu_trace[tblock][thread][reg]
                sim_values = sim_trace[tblock][thread][reg]

                if len(emu_values) != len(sim_values):
                    print(f"Value count mismatch for TBlock {tblock}, Thread {thread}, Register {reg}")
                    print(f"Emulator values: {emu_values}")
                    print(f"Simulation values: {sim_values}")
                    value_mismatch = True

                for idx in range(min(len(emu_values), len(sim_values))):
                    emu_timestamp, emu_value = emu_values[idx]
                    sim_timestamp, sim_value = sim_values[idx]
                    if emu_value != sim_value:
                        print(f"Value mismatch at TBlock {tblock}, Thread {thread}, Register {reg} at emu timestamp {emu_timestamp}, sim timestamp {sim_timestamp}")
                        print(f"Emulator value: {emu_value:#010x}, Simulation value: {sim_value:#010x}")
                        value_mismatch = True
                        if earliest_mismatch_emu is None or emu_timestamp < earliest_mismatch_emu:
                            earliest_mismatch_emu = emu_timestamp
                        if earliest_mismatch_sim is None or sim_timestamp < earliest_mismatch_sim:
                            earliest_mismatch_sim = sim_timestamp
                        value_mismatch = True

            if value_mismatch:
                raise Exception(f"Values mismatch in TBlock {tblock}, Thread {thread}, earliest mismatch at Emulator timestamp {earliest_mismatch_emu}, Simulation timestamp {earliest_mismatch_sim}")
            
    print("All traces match successfully!")

emu_reg_trace = parse_reg_trace("reg_trace.log")
sim_reg_trace = parse_results_file("results.log")

compare_reg_traces(emu_reg_trace, sim_reg_trace)
