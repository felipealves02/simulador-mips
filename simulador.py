import json
import sys

# Mapeamento Tipo R (opcode == 0): funct -> (nome, formato)
# Formatos: "rd_rs_rt", "shift", "jr", "mf", "mult_div", "syscall"
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
# Formatos: "rt_rs_imm", "branch", "load_store", "lui", "jump"
OPCODES = {
    # Tipo J
    2:  ("j", "jump"),
    3:  ("jal", "jump"),

    # Desvios
    4:  ("beq", "branch"),
    5:  ("bne", "branch"),
    6:  ("blez", "rs_offset"),
    7:  ("bgtz", "rs_offset"),
    1:  ("bltz", "rs_offset"),

    # Aritméticas / comparação
    8:  ("addi", "rt_rs_imm"),
    9:  ("addiu", "rt_rs_imm"),
    10: ("slti", "rt_rs_imm"),
    11: ("sltiu", "rt_rs_imm"),

    # Lógicas imediatas
    12: ("andi", "rt_rs_imm"),
    13: ("ori", "rt_rs_imm"),
    14: ("xori", "rt_rs_imm"),

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

    # Converte imediato para complemento de 2 com sinal caso necessário
    signed_imm = imm - 0x10000 if imm >= 0x8000 else imm

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
        if fmt == "rt_rs_imm":
            return f"{name} ${rt}, ${rs}, {signed_imm}"
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