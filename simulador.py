import json
import sys

REG_NAMES = [
    "$zero", "$at", "$v0", "$v1", "$a0", "$a1", "$a2", "$a3",
    "$t0", "$t1", "$t2", "$t3", "$t4", "$t5", "$t6", "$t7",
    "$s0", "$s1", "$s2", "$s3", "$s4", "$s5", "$s6", "$s7",
    "$t8", "$t9", "$k0", "$k1", "$gp", "$sp", "$fp", "$ra"
]

class RegisterBank:
    # Banco de 32 registradores + pc, hi e lo

    def __init__(self, regs_config=None):
        self.regs = [0] * 32
        self.pc = 0x00400000
        self.hi = 0
        self.lo = 0

        # Valores padrão do MARS
        self.regs[28] = 0x10008000  # $gp
        self.regs[29] = 0x7FFFEFFC  # $sp

        # Sobrescreve os valores padrão com os definidos no config
        if regs_config:
            self.load_config(regs_config)

    def read(self, index):
        return self.regs[index]

    def write(self, index, value):
        # O registrador $0 é sempre zero
        if index != 0:
            self.regs[index] = value & 0xFFFFFFFF

    def increment_pc(self):
        self.pc = (self.pc + 4) & 0xFFFFFFFF

    def load_config(self, regs_config):
        for name, value in regs_config.items():

            if name == "pc":
                self.pc = value & 0xFFFFFFFF

            elif name == "hi":
                self.hi = value & 0xFFFFFFFF

            elif name == "lo":
                self.lo = value & 0xFFFFFFFF

            elif name.startswith("$"):

                # Formato numérico: $0, $1, ..., $31
                if name[1:].isdigit():
                    index = int(name[1:])

                    if 0 <= index < 32:
                        self.write(index, value)

                # Também aceita nomes como $gp, $sp, $ra...
                elif name in REG_NAMES:
                    index = REG_NAMES.index(name)
                    self.write(index, value)

# Mapeamento Tipo R (opcode == 0): funct -> (nome, formato)
# Formatos: "rd_rs_rt", "shift", "rd_rt_rs", "jr",
# "rd_only", "rs_rt", "syscall"
R_FUNCT = {
    32: ("add", "rd_rs_rt"),
    33: ("addu", "rd_rs_rt"),
    34: ("sub", "rd_rs_rt"),
    35: ("subu", "rd_rs_rt"),
    36: ("and", "rd_rs_rt"),
    37: ("or", "rd_rs_rt"),
    38: ("xor", "rd_rs_rt"),
    39: ("nor", "rd_rs_rt"),
    42: ("slt", "rd_rs_rt"),
    43: ("sltu", "rd_rs_rt"),

    0:  ("sll", "shift"),
    2:  ("srl", "shift"),
    3:  ("sra", "shift"),
    4:  ("sllv", "rd_rt_rs"),
    6:  ("srlv", "rd_rt_rs"),
    7:  ("srav", "rd_rt_rs"),

    8:  ("jr", "jr"),
    12: ("syscall", "syscall"),

    16: ("mfhi", "rd_only"),
    18: ("mflo", "rd_only"),

    24: ("mult", "rs_rt"),
    25: ("multu", "rs_rt"),
    26: ("div", "rs_rt"),
    27: ("divu", "rs_rt")
}

# Mapeamento Tipo I e J: opcode -> (nome, formato)
# Formatos: "rt_rs_signed_imm", "rt_rs_unsigned_imm",
# "branch", "rs_offset", "load_store", "lui", "jump"
OPCODES = {
    # Tipo J
    2:  ("j", "jump"),
    3:  ("jal", "jump"),

    # Desvios
    4:  ("beq", "branch"),
    5:  ("bne", "branch"),
    6:  ("blez", "rs_offset"),
    7:  ("bgtz", "rs_offset"),

    # Aritméticas / comparação
    8:  ("addi", "rt_rs_signed_imm"),
    9:  ("addiu", "rt_rs_signed_imm"),
    10: ("slti", "rt_rs_signed_imm"),
    11: ("sltiu", "rt_rs_signed_imm"),

    # Lógicas imediatas
    12: ("andi", "rt_rs_unsigned_imm"),
    13: ("ori", "rt_rs_unsigned_imm"),
    14: ("xori", "rt_rs_unsigned_imm"),

    # Load upper immediate
    15: ("lui", "lui"),

    # Load
    32: ("lb", "load_store"),
    33: ("lh", "load_store"),
    35: ("lw", "load_store"),
    36: ("lbu", "load_store"),
    37: ("lhu", "load_store"),
    48: ("ll", "load_store"),

    # Store
    40: ("sb", "load_store"),
    41: ("sh", "load_store"),
    43: ("sw", "load_store"),
    56: ("sc", "load_store")
}

# Instruções especiais com opcode 1
# A identificação depende também do campo rt
REGIMM = {
    0: ("bltz", "rs_offset")
}

def decode_instruction(hex_str):
    val = int(hex_str, 16)
    opcode = (val >> 26) & 0x3F
    rs = (val >> 21) & 0x1F
    rt = (val >> 16) & 0x1F
    rd = (val >> 11) & 0x1F
    shamt = (val >> 6) & 0x1F
    funct = val & 0x3F
    imm = val & 0xFFFF
    addr = val & 0x03FFFFFF

    # Converte o imediato de 16 bits para valor com sinal quando necessário
    signed_imm = imm - 0x10000 if imm >= 0x8000 else imm

    # Opcode 1 utiliza também o campo rt para identificar a instrução
    if opcode == 1:
        if rt not in REGIMM:
            return f"desconhecida (opcode {opcode}, rt {rt})"

        name, fmt = REGIMM[rt]

        if fmt == "rs_offset":
            return f"{name} ${rs}, {signed_imm}"

    if opcode == 0:
        if funct not in R_FUNCT:
            return f"desconhecida (funct {funct})"
        name, fmt = R_FUNCT[funct]
        if fmt == "rd_rs_rt":
            return f"{name} ${rd}, ${rs}, ${rt}"
        if fmt == "shift":
            return f"{name} ${rd}, ${rt}, {shamt}"
        if fmt == "rd_rt_rs":
            return f"{name} ${rd}, ${rt}, ${rs}"
        if fmt == "jr":
            return f"{name} ${rs}"
        if fmt == "rd_only":
            return f"{name} ${rd}"
        if fmt == "rs_rt":
            return f"{name} ${rs}, ${rt}"
        if fmt == "syscall":
            return "syscall"
    else:
        if opcode not in OPCODES:
            return f"desconhecida (opcode {opcode})"
        name, fmt = OPCODES[opcode]
        if fmt == "rt_rs_signed_imm":
            return f"{name} ${rt}, ${rs}, {signed_imm}"
        if fmt == "rt_rs_unsigned_imm":
            return f"{name} ${rt}, ${rs}, {imm}"
        if fmt == "branch":
            return f"{name} ${rs}, ${rt}, {signed_imm}"
        if fmt == "rs_offset":
            return f"{name} ${rs}, {signed_imm}"
        if fmt == "load_store":
            return f"{name} ${rt}, {signed_imm}(${rs})"
        if fmt == "lui":
            return f"{name} ${rt}, {imm}"
        if fmt == "jump":
            return f"{name} {addr}"

    return "desconhecida"

def process_file(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    results = []
    for hex_inst in data.get("text", []):
        decoded = decode_instruction(hex_inst)
        results.append({
            "hex": hex_inst,
            "text": decoded,
            "regs": {},
            "mem": {},
            "stdout": ""
        })

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    infile = sys.argv[1] if len(sys.argv) > 1 else "entrada.json"
    outfile = sys.argv[2] if len(sys.argv) > 2 else "saida.json"
    process_file(infile, outfile)