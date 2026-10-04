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

class Memory:
    # Memória endereçável por byte

    SEGMENT_SIZE = 1024

    SEGMENT_BASES = {
        "text": 0x00400000,
        "data": 0x10010000,
        "sp": 0x7FFFEFFC
    }

    def __init__(self, mem_config=None, data=None):
        self.bytes = {}
        self.word_addresses = set()

        if mem_config:
            self.load_config(mem_config)

        if data:
            self.load_data(data)

    def read_byte(self, address):
        address &= 0xFFFFFFFF
        return self.bytes.get(address, 0)

    def write_byte(self, address, value):
        address &= 0xFFFFFFFF
        self.bytes[address] = value & 0xFF

    def load_config(self, mem_config):
        for address, value in mem_config.items():
            self.write_word(int(address), int(value))

    def load_data(self, data):
        for address, value in data.items():
            self.write_word(int(address), int(value))

    def read_word(self, address):
        # MIPS Big Endian
        b0 = self.read_byte(address)
        b1 = self.read_byte(address + 1)
        b2 = self.read_byte(address + 2)
        b3 = self.read_byte(address + 3)

        return (
            (b0 << 24)
            | (b1 << 16)
            | (b2 << 8)
            | b3
        )

    def write_word(self, address, value):
        address &= 0xFFFFFFFF
        value &= 0xFFFFFFFF

        self.word_addresses.add(address)

        # MIPS Big Endian
        self.write_byte(address,     (value >> 24) & 0xFF)
        self.write_byte(address + 1, (value >> 16) & 0xFF)
        self.write_byte(address + 2, (value >> 8) & 0xFF)
        self.write_byte(address + 3, value & 0xFF)

    def get_state(self):
        state = {}

        for address in sorted(self.word_addresses):
            value = self.read_word(address)

            if value != 0:
                state[str(address)] = to_signed32(value)

        return state

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

def execute_instruction(fields, bank, memory):
    """
    Executa a instrução decodificada no banco de registradores e na memória.
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

        # Lógicas
        if funct == 36:    # and
            bank.write(rd, bank.read(fields["rs"]) & bank.read(fields["rt"]))
        elif funct == 37:  # or
            bank.write(rd, bank.read(fields["rs"]) | bank.read(fields["rt"]))
        elif funct == 38:  # xor
            bank.write(rd, bank.read(fields["rs"]) ^ bank.read(fields["rt"]))
        elif funct == 39:  # nor
            bank.write(rd, ~(bank.read(fields["rs"]) | bank.read(fields["rt"])) & 0xFFFFFFFF)

        # Shifts fixos
        elif funct == 0:   # sll
            bank.write(rd, bank.read(fields["rt"]) << fields["shamt"])
        elif funct == 2:   # srl
            bank.write(rd, bank.read(fields["rt"]) >> fields["shamt"])
        elif funct == 3:   # sra
            bank.write(rd, rt_signed >> fields["shamt"])

        # Shifts variáveis
        elif funct == 4:   # sllv
            bank.write(rd, bank.read(fields["rt"]) << (bank.read(fields["rs"]) & 0x1F))
        elif funct == 6:   # srlv
            bank.write(rd, bank.read(fields["rt"]) >> (bank.read(fields["rs"]) & 0x1F))
        elif funct == 7:   # srav
            bank.write(rd, rt_signed >> (bank.read(fields["rs"]) & 0x1F))

        # Aritméticas e Comparação
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

        # HI/LO
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

        # Desvio
        elif funct == 8:   # jr
            bank.set_pc(bank.read(fields["rs"]))

    else:
        rs_signed = bank.read_signed(fields["rs"])
        rs_unsigned = bank.read(fields["rs"])
        rt = fields["rt"]
        signed_imm = fields["signed_imm"]

        # Aritméticas I
        if opcode == 8:    # addi
            res = rs_signed + signed_imm
            if res > 2147483647 or res < -2147483648:
                stdout_msg = "overflow"
            else:
                bank.write(rt, res)

        elif opcode == 9:  # addiu
            bank.write(rt, rs_signed + signed_imm)

        elif opcode == 10: # slti
            bank.write(rt, 1 if rs_signed < signed_imm else 0)

        elif opcode == 12: # andi
            bank.write(rt, bank.read(fields["rs"]) & fields["imm"])

        elif opcode == 13: # ori
            bank.write(rt, bank.read(fields["rs"]) | fields["imm"])

        elif opcode == 14: # xori
            bank.write(rt, bank.read(fields["rs"]) ^ fields["imm"])

        elif opcode == 15: # lui
            bank.write(rt, fields["imm"] << 16)

        # Desvios incondicionais 
        elif opcode == 2:  # j
            bank.set_pc((bank.pc & 0xF0000000) | (fields["addr"] << 2))

        elif opcode == 3:  # jal
            bank.write(31, bank.pc)
            bank.set_pc((bank.pc & 0xF0000000) | (fields["addr"] << 2))

        # ==========================================
        # LOAD E STORE (lw, sw, lb, lbu, sb)
        # ==========================================
        elif opcode == 35: # lw (Load Word)
            effective_addr = (rs_unsigned + signed_imm) & 0xFFFFFFFF
            word_val = memory.read_word(effective_addr)
            bank.write(rt, word_val)

        elif opcode == 43: # sw (Store Word)
            effective_addr = (rs_unsigned + signed_imm) & 0xFFFFFFFF
            memory.write_word(effective_addr, bank.read(rt))

        elif opcode == 32: # lb (Load Byte com extensão de sinal)
            effective_addr = (rs_unsigned + signed_imm) & 0xFFFFFFFF
            byte_val = memory.read_byte(effective_addr)
            # Extensão de sinal para 8 bits (-128 a 127)
            if byte_val >= 0x80:
                byte_val -= 0x100
            bank.write(rt, byte_val)

        elif opcode == 36: # lbu (Load Byte Unsigned com extensão de zero)
            effective_addr = (rs_unsigned + signed_imm) & 0xFFFFFFFF
            byte_val = memory.read_byte(effective_addr) & 0xFF
            bank.write(rt, byte_val)

        elif opcode == 40: # sb (Store Byte)
            effective_addr = (rs_unsigned + signed_imm) & 0xFFFFFFFF
            byte_val = bank.read(rt) & 0xFF
            memory.write_byte(effective_addr, byte_val)
            # Mantém alinhamento da palavra para rastreamento no get_state
            aligned_word = effective_addr - (effective_addr % 4)
            memory.word_addresses.add(aligned_word)

    return stdout_msg

def process_file(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Carrega a configuração inicial dos registradores e da memória
    config = data.get("config", {})
    regs_config = config.get("regs", {})
    mem_config = config.get("mem", {})
    data_segment = data.get("data", {})

    # Cria o banco de registradores e a memória
    bank = RegisterBank(regs_config)
    memory = Memory(mem_config, data_segment)

    results = []

    for hex_inst in data.get("text", []):
        fields = decode_instruction(hex_inst)
        
        # Executa a instrução passando bank e memory
        stdout_msg = execute_instruction(fields, bank, memory)

        results.append({
            "hex": hex_inst,
            "text": fields["text"],
            "regs": bank.get_state(),
            "mem": memory.get_state(),
            "stdout": stdout_msg
        })

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    infile = sys.argv[1] if len(sys.argv) > 1 else "entrada.json"
    outfile = sys.argv[2] if len(sys.argv) > 2 else "saida.json"
    process_file(infile, outfile)