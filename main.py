import os
import re
import subprocess
import streamlit as st
from typing import List, Dict, Tuple

# Identify groups for parallelizing
class ParallelMatrixLayout:
    def __init__(self, rows: int, cols: int, base_addr: int):
        self.rows = rows
        self.cols = cols
        self.base = base_addr
        self.core_assignment = {}

    def assign_cores(self, total_cores: int = 8):
        block_size = 2  # Smaller blocks for these matrix sizes
        for i in range(self.rows):
            for j in range(self.cols):
                block_i, block_j = i // block_size, j // block_size
                self.core_assignment[(i,j)] = (block_i + block_j) % total_cores

    def get_addr(self, i: int, j: int) -> int:
        return self.base + (i * self.cols + j) * 4  # 4 bytes per element

    def get_addr_and_core(self, i: int, j: int) -> Tuple[int, int]:
        addr = self.get_addr(i, j)
        return addr, self.core_assignment.get((i,j), 0)

# pPIM Instructions class
# Opcodes and Instruction word format
class pPIM_Instruction:
    NOP  = 0b00
    PROG = 0b01
    EXE  = 0b10
    END  = 0b11

    def __init__(self, instr_type: int, pointer: int = 0, rd: int = 0, wr: int = 0, row_addr: int = 0):
        self.type = instr_type    # 2 bits
        self.pointer = pointer    # 6 bits
        self.rd = rd              # 1 bit
        self.wr = wr              # 1 bit
        self.row_addr = row_addr  # 8 bits

    def encode(self) -> str:
        # 24-bit format: [2 op][6 ptr][1 rd][1 wr][8 addr][6 reserved]
        instr = (self.type << 22) | \
                (self.pointer << 16) | \
                (self.rd << 15) | \
                (self.wr << 14) | \
                (self.row_addr << 6)
        return f"{instr:024b}"

# Get the matrix sizes from the .ll file
def detect_matrix_sizes(llvm_ir: str) -> Tuple[ParallelMatrixLayout, ParallelMatrixLayout, ParallelMatrixLayout]:
    # Adjusted regex to match alloca patterns
    pattern = r"alloca \[(\d+) x \[(\d+) x i32\]\]"
    matches = list(re.finditer(pattern, llvm_ir))
    
    if len(matches) < 2:
        raise ValueError("Could not find sufficient matrix allocations in LLVM IR")
    
    # Extract matrix dimensions from LLVM IR
    A_rows, A_cols = map(int, matches[0].groups())
    B_rows, B_cols = map(int, matches[1].groups())

    if A_cols != B_rows:
        raise ValueError("Matrix multiplication requires A_cols == B_rows")
    
    # Base address assignments
    A_base = 0x100
    B_base = A_base + A_rows * A_cols * 4
    C_base = B_base + B_rows * B_cols * 4

    # Create memory layouts
    A = ParallelMatrixLayout(A_rows, A_cols, A_base)
    B = ParallelMatrixLayout(B_rows, B_cols, B_base)
    C = ParallelMatrixLayout(A_rows, B_cols, C_base)

    # Assign cores
    A.assign_cores()
    B.assign_cores()
    C.assign_cores()

    print(f"Detected Matrix Sizes - A: {A_rows}x{A_cols}, B: {B_rows}x{B_cols}, C: {A_rows}x{B_cols}")
    return A, B, C

# Generating Look up tables
def generate_LUT_programming() -> List[pPIM_Instruction]:
    """Generate LUT programming instructions"""
    instructions = []
    for core in range(8):  # Program 8 cores
        instructions.append(pPIM_Instruction(
            pPIM_Instruction.PROG,
            pointer=core,
            row_addr=core * 64
        ))
        instructions.append(pPIM_Instruction(pPIM_Instruction.NOP))
    return instructions

# Generating instruction words for matrix mul
def process_matmul(llvm_ir: str) -> List[pPIM_Instruction]:
    A, B, C = detect_matrix_sizes(llvm_ir)
    instructions = generate_LUT_programming()
    
    for i in range(A.rows):
        for j in range(B.cols):
            # Initialize accumulator (no NOP needed after)
            c_addr, c_core = C.get_addr_and_core(i, j)
            instructions.append(pPIM_Instruction(
                pPIM_Instruction.EXE,
                pointer=c_core,
                wr=1,
                row_addr=c_addr
            ))
            
            for k in range(A.cols):
                a_addr, a_core = A.get_addr_and_core(i, k)
                b_addr, b_core = B.get_addr_and_core(k, j)
                
                # Load A[i][k] + mandatory NOP
                instructions.append(pPIM_Instruction(
                    pPIM_Instruction.EXE,
                    pointer=a_core,
                    rd=1,
                    row_addr=a_addr
                ))
                instructions.append(pPIM_Instruction(pPIM_Instruction.NOP))
                
                # Load B[k][j] + mandatory NOP 
                instructions.append(pPIM_Instruction(
                    pPIM_Instruction.EXE,
                    pointer=b_core,
                    rd=1,
                    row_addr=b_addr
                ))
                instructions.append(pPIM_Instruction(pPIM_Instruction.NOP))
                
                # MAC operation (no NOP needed)
                instructions.append(pPIM_Instruction(
                    pPIM_Instruction.EXE,
                    pointer=c_core
                ))
    
    instructions.append(pPIM_Instruction(pPIM_Instruction.END))
    return instructions

# Clean the cpp file
def clean_cpp(path):
    with open(path, 'r') as f:
        code = f.read()
    

    code = re.sub(r'#\s*include\s*["<][^">]+[">]', '', code) # remove include statements
    code = re.sub(r'using\s+namespace\s+std\s*;', '', code) # remove using namespace std;
    code = re.sub(r'\b(std::)?(cout|cin)\b', '//', code) # remove i/p and o/p statements

    path = path.split('.')[0] + '_cleaned.' + path.split('.')[1]
    with open(path, 'w') as f:
        f.write(code)
    return path

# Converting cpp to .ll and optimizing it 
def compile_optimize(path):
    llvm_path = path.replace(".cpp",'.ll')
    optimized_llvm_path = path.split('.')[0] + '_optimized' + '.ll'
    
    subprocess.run(["clang++", "-S", "-emit-llvm", path, "-o", llvm_path], check=True)
    print(optimized_llvm_path)
    subprocess.run(["opt", "-O3", "-S", llvm_path, "-o", optimized_llvm_path], check=True)

    return optimized_llvm_path

# StreamLit frontend
st.title('pPIM ISA Generator')
file = st.file_uploader('Upload your cpp file', type=['cpp'])

# When user uploads the file save it
if file:
    os.makedirs('temp', exist_ok=True)
    file_name = os.path.join('temp',file.name)

    print(file_name)

    with open(file_name, 'wb') as f:
        f.write(file.getbuffer())

    cleaned_path = clean_cpp(file_name)
    optimized_final_path = compile_optimize(cleaned_path)

    st.text('Compiled and Optimized Successfully')
    print(optimized_final_path)

    with open(optimized_final_path, 'r') as f:
        llvm_ir = f.read()
    
    try:
        machine_code = process_matmul(llvm_ir)
        
        with open("temp/pPIM_full2.bin", 'w') as f:
            f.write("// pPIM Instruction Stream\n")
            f.write("// 24-bit format: [2 op][6 ptr][1 rd][1 wr][8 addr][6 reserved]\n")
            for i, instr in enumerate(machine_code):
                comment = ""
                if instr.type == pPIM_Instruction.PROG:
                    comment = f"// PROG core {instr.pointer}"
                elif instr.type == pPIM_Instruction.EXE:
                    if instr.rd:
                        comment = f"// EXE read core {instr.pointer}"
                    elif instr.wr:
                        comment = f"// EXE write core {instr.pointer}"
                    else:
                        comment = f"// EXE compute core {instr.pointer}"
                elif instr.type == pPIM_Instruction.END:
                    comment = "// END"
                else:
                    comment = "// NOP"
                
                f.write(f"{instr.encode()}  {comment}\n")
            
        st.text('Generated pPIM Istructions')
        with open("temp/pPIM_full2.bin", 'rb') as f:
            st.download_button(label='Download ISA', data=f.read())
        
        print(f"Successfully generated {len(machine_code)} instructions")
    except Exception as e:
        print(f"Error: {str(e)}")