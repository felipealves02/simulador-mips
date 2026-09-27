import json
import sys

REG_NAMES = [
    "$zero", "$at", "$v0", "$v1", "$a0", "$a1", "$a2", "$a3",
    "$t0", "$t1", "$t2", "$t3", "$t4", "$t5", "$t6", "$t7",
    "$s0", "$s1", "$s2", "$s3", "$s4", "$s5", "$s6", "$s7",
    "$t8", "$t9", "$k0", "$k1", "$gp", "$sp", "$fp", "$ra"
]

def to_signed32(value):
    value &= 0xFFFFFFFF
    if value & 0x80000000:
        return value - 0x100000000
    return value

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

    def read_signed(self, index):
        return to_signed32(self.regs[index])

    def write(self, index, value):
        # O registrador $0 é sempre zero
        if index != 0:
            self.regs[index] = value & 0xFFFFFFFF

    def write_hi(self, value):
        self.hi = value & 0xFFFFFFFF

    def write_lo(self, value):
        self.lo = value & 0xFFFFFFFF

    def set_pc(self, value):
        self.pc = value & 0xFFFFFFFF

    def increment_pc(self):
        self.pc = (self.pc + 4) & 0xFFFFFFFF

    def get_state(self):
        state = {}

        # Registradores gerais na ordem $0 até $31
        for index, value in enumerate(self.regs):
            if value != 0:
                state[f"${index}"] = to_signed32(value)

        # Registradores especiais
        if self.pc != 0:
            state["pc"] = to_signed32(self.pc)

        if self.hi != 0:
            state["hi"] = to_signed32(self.hi)

        if self.lo != 0:
            state["lo"] = to_signed32(self.lo)

        return state

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
                # Nomes mnemônicos como $gp, $sp, $ra...
                elif name in REG_NAMES:
                    index = REG_NAMES.index(name)
                    self.write(index, value)

# Mapeamento Tipo R (opcode == 0): funct -> (nome, formato)
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
OPCODES = {
    2:  ("j", "jump"),
    3:  ("jal", "jump"),

    4:  ("beq", "branch"),
    5:  ("bne", "branch"),
    6:  ("blez", "rs_offset"),
    7:  ("bgtz", "rs_offset"),

    8:  ("addi", "rt_rs_signed_imm"),
    9:  ("addiu", "rt_rs_signed_imm"),
    10: ("slti", "rt_rs_signed_imm"),
    11: ("sltiu", "rt_rs_signed_imm"),

    12: ("andi", "rt_rs_unsigned_imm"),
    13: ("ori", "rt_rs_unsigned_imm"),
    14: ("xori", "rt_rs_unsigned_imm"),

    15: ("lui", "lui"),

    32: ("lb", "load_store"),
    33: ("lh", "load_store"),
    35: ("lw", "load_store"),
    36: ("lbu", "load_store"),
    37: ("lhu", "load_store"),
    48: ("ll", "load_store"),

    40: ("sb", "load_store"),
    41: ("sh", "load_store"),
    43: ("sw", "load_store"),
    56: ("sc", "load_store")
}

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

    signed_imm = imm - 0x10000 if imm >= 0x8000 else imm

    fields = {
        "opcode": opcode, "rs": rs, "rt": rt, "rd": rd,
        "shamt": shamt, "funct": funct, "imm": imm,
        "signed_imm": signed_imm, "addr": addr
    }

    if opcode == 1:
        if rt not in REGIMM:
            fields["text"] = f"desconhecida (opcode {opcode}, rt {rt})"
            return fields
        name, fmt = REGIMM[rt]
        if fmt == "rs_offset":
            fields["text"] = f"{name} ${rs}, {signed_imm}"
            return fields

    if opcode == 0:
        if funct not in R_FUNCT:
            fields["text"] = f"desconhecida (funct {funct})"
            return fields
        name, fmt = R_FUNCT[funct]
        if fmt == "rd_rs_rt":
            fields["text"] = f"{name} ${rd}, ${rs}, ${rt}"
        elif fmt == "shift":
            fields["text"] = f"{name} ${rd}, ${rt}, {shamt}"
        elif fmt == "rd_rt_rs":
            fields["text"] = f"{name} ${rd}, ${rt}, ${rs}"
        elif fmt == "jr":
            fields["text"] = f"{name} ${rs}"
        elif fmt == "rd_only":
            fields["text"] = f"{name} ${rd}"
        elif fmt == "rs_rt":
            fields["text"] = f"{name} ${rs}, ${rt}"
        elif fmt == "syscall":
            fields["text"] = "syscall"
        else:
            fields["text"] = "desconhecida"
    else:
        if opcode not in OPCODES:
            fields["text"] = f"desconhecida (opcode {opcode})"
            return fields
        name, fmt = OPCODES[opcode]
        if fmt == "rt_rs_signed_imm":
            fields["text"] = f"{name} ${rt}, ${rs}, {signed_imm}"
        elif fmt == "rt_rs_unsigned_imm":
            fields["text"] = f"{name} ${rt}, ${rs}, {imm}"
        elif fmt == "branch":
            fields["text"] = f"{name} ${rs}, ${rt}, {signed_imm}"
        elif fmt == "rs_offset":
            fields["text"] = f"{name} ${rs}, {signed_imm}"
        elif fmt == "load_store":
            fields["text"] = f"{name} ${rt}, {signed_imm}(${rs})"
        elif fmt == "lui":
            fields["text"] = f"{name} ${rt}, {imm}"
        elif fmt == "jump":
            fields["text"] = f"{name} {addr}"
        else:
            fields["text"] = "desconhecida"

    return fields

def execute_instruction(fields, bank):
    """
    Executa a instrução decodificada no banco de registradores.
    Retorna a string de stdout ("overflow" se houver overflow aritmético, caso contrário "").
    """
    opcode = fields["opcode"]
    stdout_msg = ""

    # Incremento do PC por instrução (4 bytes)
    bank.increment_pc()

    if opcode == 0:
        funct = fields["funct"]
        rs_signed = bank.read_signed(fields["rs"])
        rt_signed = bank.read_signed(fields["rt"])
        rd = fields["rd"]

        # Lógicas já implementadas pelo grupo
        if funct == 36:    # and
            bank.write(rd, bank.read(fields["rs"]) & bank.read(fields["rt"]))
        elif funct == 37:  # or
            bank.write(rd, bank.read(fields["rs"]) | bank.read(fields["rt"]))
        elif funct == 38:  # xor
            bank.write(rd, bank.read(fields["rs"]) ^ bank.read(fields["rt"]))
        elif funct == 39:  # nor
            bank.write(rd, ~(bank.read(fields["rs"]) | bank.read(fields["rt"])) & 0xFFFFFFFF)

        # Aritméticas e Comparação (Integrante 2)
        elif funct == 32:  # add (com detecção de overflow)
            res = rs_signed + rt_signed
            if res > 2147483647 or res < -2147483648:
                stdout_msg = "overflow"
            else:
                bank.write(rd, res)

        elif funct == 33:  # addu (sem overflow)
            bank.write(rd, rs_signed + rt_signed)

        elif funct == 34:  # sub (com detecção de overflow)
            res = rs_signed - rt_signed
            if res > 2147483647 or res < -2147483648:
                stdout_msg = "overflow"
            else:
                bank.write(rd, res)

        elif funct == 35:  # subu (sem overflow)
            bank.write(rd, rs_signed - rt_signed)

        elif funct == 42:  # slt (comparação com sinal)
            bank.write(rd, 1 if rs_signed < rt_signed else 0)

        # HI/LO — multiplicação, divisão e leitura dos registradores especiais
        elif funct == 24:  # mult (com sinal)
            product = rs_signed * rt_signed
            product &= 0xFFFFFFFFFFFFFFFF
            bank.write_hi((product >> 32) & 0xFFFFFFFF)
            bank.write_lo(product & 0xFFFFFFFF)

        elif funct == 25:  # multu (sem sinal)
            product = bank.read(fields["rs"]) * bank.read(fields["rt"])
            product &= 0xFFFFFFFFFFFFFFFF
            bank.write_hi((product >> 32) & 0xFFFFFFFF)
            bank.write_lo(product & 0xFFFFFFFF)

        elif funct == 26:  # div (com sinal)
            if rt_signed != 0:
                quotient = abs(rs_signed) // abs(rt_signed)
                if (rs_signed < 0) != (rt_signed < 0):
                    quotient = -quotient
                remainder = rs_signed - (quotient * rt_signed)
                bank.write_lo(quotient)
                bank.write_hi(remainder)

        elif funct == 27:  # divu (sem sinal)
            rt_unsigned = bank.read(fields["rt"])
            if rt_unsigned != 0:
                quotient = bank.read(fields["rs"]) // rt_unsigned
                remainder = bank.read(fields["rs"]) % rt_unsigned
                bank.write_lo(quotient)
                bank.write_hi(remainder)

        elif funct == 16:  # mfhi
            bank.write(rd, bank.hi)

        elif funct == 18:  # mflo
            bank.write(rd, bank.lo)

    else:
        # Instruções Tipo I Aritméticas e Comparação (Integrante 2)
        rs_signed = bank.read_signed(fields["rs"])
        rt = fields["rt"]
        signed_imm = fields["signed_imm"]

        if opcode == 8:    # addi (com detecção de overflow)
            res = rs_signed + signed_imm
            if res > 2147483647 or res < -2147483648:
                stdout_msg = "overflow"
            else:
                bank.write(rt, res)

        elif opcode == 9:  # addiu (sem overflow)
            bank.write(rt, rs_signed + signed_imm)

        elif opcode == 10: # slti (comparação imediata com sinal)
            bank.write(rt, 1 if rs_signed < signed_imm else 0)

    return stdout_msg

def process_file(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Carrega a configuração inicial dos registradores
    config = data.get("config", {})
    regs_config = config.get("regs", {})

    # Cria o banco de registradores uma única vez
    bank = RegisterBank(regs_config)

    results = []

    for hex_inst in data.get("text", []):
        fields = decode_instruction(hex_inst)
        
        # Executa a instrução, atualiza registradores e captura overflow
        stdout_msg = execute_instruction(fields, bank)

        results.append({
            "hex": hex_inst,
            "text": fields["text"],
            "regs": bank.get_state(),
            "mem": {},
            "stdout": stdout_msg
        })

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    infile = sys.argv[1] if len(sys.argv) > 1 else "entrada.json"
    outfile = sys.argv[2] if len(sys.argv) > 2 else "saida.json"
    process_file(infile, outfile)