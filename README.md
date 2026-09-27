# Simulador MIPS - Entrega 2: Instruções Lógicas e Aritméticas

Projeto de desenvolvimento incremental de um simulador para a arquitetura MIPS.

## Integrantes do Grupo

- Felipe Alves
- Lucas Cavalcanti
- Nickollas Vital
- Thallysson Silva

## Descrição da Entrega 2

Nesta segunda entrega, o simulador mantém a identificação e decodificação das instruções implementadas na primeira etapa e passa também a executar instruções lógicas e aritméticas dos tipos R e I.

O programa recebe um arquivo JSON contendo instruções MIPS em código de máquina hexadecimal de 32 bits, realiza a decodificação para Assembly e executa as instruções suportadas utilizando um banco de 32 registradores, além dos registradores especiais PC, HI e LO.

A execução é sequencial, de forma que o resultado de uma instrução pode influenciar as instruções seguintes.

Após cada instrução, o programa registra o estado atualizado do banco de registradores, exibindo apenas os registradores com valor diferente de zero.

## Estrutura do Projeto

- `simulador.py` - código principal responsável pela decodificação e execução das instruções MIPS.
- `entrada.json` - arquivo de entrada contendo a configuração inicial e as instruções em hexadecimal.
- `saida.json` - arquivo gerado com o resultado da execução.
- `README.md` - documentação do projeto.

## Formato de Entrada

O arquivo `entrada.json` possui os campos:

- `config` - configuração inicial do simulador.
- `data` - reservado para dados em memória.
- `text` - instruções MIPS de 32 bits representadas em hexadecimal.

Exemplo:

```json
{
  "config": {
    "regs": {
      "$4": 10,
      "$5": 20
    }
  },
  "data": {},
  "text": [
    "0x00853020",
    "0x20c70005"
  ]
}
```

Os valores definidos em `config.regs` são carregados antes do início da execução.

Os registradores são inicializados de acordo com o MARS, com destaque para:

- `$gp = 0x10008000`
- `$sp = 0x7fffeffc`
- `pc = 0x00400000`

O registrador `$0` permanece sempre com valor zero.

## Decodificação das Instruções

Cada instrução hexadecimal é separada nos campos correspondentes ao formato MIPS, como:

- `opcode`
- `rs`
- `rt`
- `rd`
- `shamt`
- `funct`
- imediato
- endereço

A identificação considera instruções dos formatos:

- Tipo R
- Tipo I
- Tipo J

As funcionalidades de identificação e decodificação implementadas na primeira entrega foram mantidas nesta etapa.

## Instruções Executadas na Entrega 2

### Aritméticas e comparação

- `add`
- `sub`
- `addu`
- `subu`
- `slt`
- `addi`
- `addiu`
- `slti`

### Lógicas

- `and`
- `or`
- `xor`
- `nor`
- `andi`
- `ori`
- `xori`

### Deslocamentos

- `sll`
- `srl`
- `sra`
- `sllv`
- `srlv`
- `srav`

### Operações com HI e LO

- `mult`
- `multu`
- `div`
- `divu`
- `mfhi`
- `mflo`

## Banco de Registradores

O simulador possui:

- 32 registradores de propósito geral;
- registrador `PC`;
- registrador `HI`;
- registrador `LO`.

Os registradores possuem 32 bits.

Os valores definidos no campo `config` são carregados antes da execução das instruções.

O banco de registradores mantém seu estado durante toda a execução, permitindo que o resultado de uma instrução seja utilizado pelas instruções seguintes.

O registrador `$0` permanece sempre com valor zero.

Os registradores `$gp`, `$sp` e `pc` são inicializados com os valores padrão do MARS.

## Operações com HI e LO

As instruções de multiplicação e divisão utilizam os registradores especiais `HI` e `LO`.

Nas operações de multiplicação, o resultado de 64 bits é dividido entre os dois registradores.

As instruções `mfhi` e `mflo` permitem transferir os valores armazenados em `HI` e `LO` para registradores de propósito geral.

## Valores com Sinal e Sem Sinal

O simulador trabalha com valores de 32 bits.

Para operações que utilizam valores com sinal, a interpretação é realizada em complemento de dois.

As instruções sem sinal utilizam a representação de 32 bits sem interpretação de sinal.

Os imediatos das instruções lógicas `andi`, `ori` e `xori` são tratados como valores sem sinal.

## Overflow

As instruções:

- `add`
- `sub`
- `addi`

possuem tratamento de overflow aritmético.

Quando ocorre overflow, o campo `stdout` recebe:

```text
overflow
```

Caso contrário, o campo permanece vazio.

## Formato de Saída

O programa gera um arquivo `saida.json` contendo o resultado de cada instrução processada.

Exemplo:

```json
[
  {
    "hex": "0x00853020",
    "text": "add $6, $4, $5",
    "regs": {
      "$4": 10,
      "$5": 20,
      "$6": 30,
      "$28": 268468224,
      "$29": 2147479548,
      "pc": 4194308
    },
    "mem": {},
    "stdout": ""
  }
]
```

Os campos representam:

- `hex` - instrução original em hexadecimal.
- `text` - instrução decodificada em Assembly MIPS.
- `regs` - estado do banco de registradores após a execução.
- `mem` - estado da memória.
- `stdout` - informa a ocorrência de overflow.

Somente registradores com valor diferente de zero são apresentados em `regs`.

A ordem dos registradores é mantida de `$0` até `$31`, seguida pelos registradores especiais `pc`, `hi` e `lo`.

Nesta entrega, o campo `mem` permanece vazio, pois as operações de memória fazem parte da próxima etapa.

## Atualização do PC

O registrador `PC` é atualizado durante a execução das instruções.

Nas instruções lógicas e aritméticas desta etapa, o PC avança para a próxima instrução após cada execução.

As instruções de controle de fluxo serão tratadas na Entrega 3.

## Como Executar

### Pré-requisitos

- Python 3 instalado.

### Execução

No terminal, acesse a pasta do projeto e execute:

```bash
python simulador.py entrada.json saida.json
```

O programa irá:

1. Ler o arquivo `entrada.json`.
2. Carregar a configuração inicial dos registradores.
3. Inicializar o banco de registradores.
4. Ler cada instrução hexadecimal.
5. Decodificar a instrução para Assembly MIPS.
6. Executar as instruções suportadas pela Entrega 2.
7. Atualizar o estado do banco de registradores.
8. Gerar o arquivo `saida.json`.

Também é possível executar apenas:

```bash
python simulador.py
```

Nesse caso, o programa utiliza por padrão:

```text
entrada.json
```

como arquivo de entrada e:

```text
saida.json
```

como arquivo de saída.

## Observações

- As instruções são processadas na mesma ordem em que aparecem no arquivo de entrada.
- O resultado de uma instrução pode afetar as instruções seguintes.
- O registrador `$0` não pode ser alterado.
- Os valores dos registradores são mantidos em 32 bits.
- Os valores com sinal utilizam representação em complemento de dois.
- As instruções lógicas imediatas utilizam imediato sem sinal.
- O PC é atualizado durante a execução.
- Os registradores `HI` e `LO` são utilizados nas operações de multiplicação e divisão.
- Somente registradores com valor diferente de zero são apresentados na saída.
- As funcionalidades de identificação e decodificação da Entrega 1 continuam disponíveis.
- As instruções de memória e desvio serão executadas na Entrega 3.

## Próxima Entrega

Na próxima etapa serão adicionadas as operações de memória e controle de fluxo, incluindo instruções de load, store e desvio.