# Simulador MIPS - Entrega 1: Identificador de Instruções

Projeto de desenvolvimento incremental de um simulador para a arquitetura MIPS.

## Integrantes do Grupo

- Felipe Alves
- Lucas Cavalcanti
- Nickollas Vital
- Thallysson Silva

## Descrição da Entrega 1

Nesta primeira entrega foi implementado o identificador de instruções MIPS.

O programa recebe um arquivo JSON contendo instruções em código de máquina hexadecimal de 32 bits e realiza a decodificação para sua representação em Assembly MIPS.

O objetivo desta etapa é identificar corretamente as instruções apresentadas na disciplina, mantendo a mesma ordem em que aparecem no arquivo de entrada.

Nesta primeira entrega, não é realizada a execução das instruções. A atualização dos registradores, acesso à memória e demais operações do simulador serão implementados nas próximas etapas do projeto.

## Estrutura do Projeto

- `simulador.py` - código principal responsável pela identificação e decodificação das instruções MIPS.
- `entrada.json` - arquivo contendo as instruções em hexadecimal.
- `saida.json` - arquivo gerado com o resultado da decodificação.
- `README.md` - documentação do projeto.

## Formato de Entrada

O arquivo `entrada.json` contém as instruções MIPS de 32 bits representadas em hexadecimal.

Exemplo:

```json
{
  "text": [
    "0x02114020",
    "0x012a5821",
    "0x018d7022"
  ]
}
```

Cada valor hexadecimal é lido e separado nos campos correspondentes ao formato da instrução, como:

- `opcode`
- `rs`
- `rt`
- `rd`
- `shamt`
- `funct`
- imediato
- endereço

A identificação desses campos permite determinar a instrução Assembly correspondente.

## Formato de Saída

O programa gera um arquivo `saida.json` contendo o resultado da decodificação de cada instrução.

Exemplo:

```json
[
  {
    "hex": "0x02114020",
    "text": "add $8, $16, $17",
    "regs": {},
    "mem": {},
    "stdout": ""
  },
  {
    "hex": "0x012a5821",
    "text": "addu $11, $9, $10",
    "regs": {},
    "mem": {},
    "stdout": ""
  }
]
```

Nesta primeira entrega, os campos:

- `regs`
- `mem`
- `stdout`

permanecem vazios, pois a execução das instruções ainda não faz parte desta etapa.

## Tipos de Instruções

O identificador trabalha com instruções dos formatos:

- Tipo R
- Tipo I
- Tipo J

A identificação considera os campos correspondentes de cada formato e, quando necessário, campos adicionais como `funct` e `rt`.

## Como Executar

### Pré-requisitos

- Python 3 instalado

### Execução

No terminal, acesse a pasta do projeto e execute:

```bash
python simulador.py entrada.json saida.json
```

O programa irá:

1. Ler as instruções presentes no arquivo `entrada.json`.
2. Identificar cada instrução MIPS.
3. Converter o código de máquina para sua representação Assembly.
4. Gerar o resultado no arquivo `saida.json`.

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
- Os valores de imediato com sinal são tratados utilizando complemento de dois.
- Instruções lógicas imediatas utilizam o campo imediato sem sinal.
- Instruções que necessitam de campos adicionais para identificação possuem tratamento específico.
- Caso uma instrução não seja reconhecida, o programa informa que ela é desconhecida.

## Entregas Futuras

Nas próximas etapas do projeto serão adicionadas funcionalidades relacionadas à execução das instruções, incluindo atualização dos registradores, registradores especiais e operações envolvendo memória e desvios.