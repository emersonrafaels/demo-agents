# Demonstração: Agentes de IA com Claude e GPT

Códigos que acompanham o deck **"Agentes de IA — do assistente que responde ao colaborador digital que resolve"**.
Todas as demos fazem **chamadas reais** às APIs do **Claude (Anthropic)** e do **GPT (OpenAI)**.
Caso usado: **contestação de compra no cartão**, com dados 100% fictícios.

## Preparação (uma vez)

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="..."     # Claude
export OPENAI_API_KEY="..."        # GPT
python 00_teste_conexao.py         # confere as duas conexões
```

Windows PowerShell: `$env:ANTHROPIC_API_KEY="..."`. Veja `.env.exemplo` para todas as variáveis
(modelos, gateway interno via `OPENAI_BASE_URL`, provedor padrão).

> Use apenas chaves e ambientes aprovados pela governança do banco, e somente dados fictícios.

## Escolhendo o modelo

| Opção | Efeito |
|---|---|
| `--provedor claude` | Claude, modelo em `MODELO_CLAUDE` (padrão `claude-sonnet-5-5`) |
| `--provedor gpt` | GPT, modelo em `MODELO_GPT` (padrão `gpt-5.6`) |
| `--provedor ambos` | Só na demo 02: roda o mesmo agente nos dois e compara |
| `--provedor simulado` | Ensaio offline, sem chave e sem custo (regras locais, não é um LLM) |
| `--modelo NOME` | Sobrescreve o modelo daquela execução |

Sem `--provedor`, usa a variável `PROVEDOR` ou a chave que estiver configurada.
Confira os nomes de modelo disponíveis na sua conta antes do evento.

## Roteiro sugerido (≈ 15 min)

| Capítulo do deck | Comando | O que mostrar |
|---|---|---|
| 1 • Chatbot × Agente | `python 01_chatbot_vs_agente.py --provedor claude` | O mesmo modelo: sem ferramentas orienta, com ferramentas resolve |
| 2 • Anatomia e ciclo | `python 02_ciclo_do_agente.py --provedor claude --passo` | O modelo explica e escolhe cada passo; ENTER avança |
| 3 • Demonstração | `python 02_ciclo_do_agente.py --provedor ambos` | Mesmo agente em Claude e GPT, com tokens e tempo |
| 4 • Multiagentes | `python 03_multiagentes.py --provedor gpt` | O orquestrador aciona especialistas; o Revisor barra o rascunho |
| 4 • Guardrails | `python 04_guardrails.py --provedor claude` | Automático, aprovação humana no terminal e bloqueio |
| 6 • Como começar | `python 05_modo_sombra.py --provedor claude` | Concordância do agente com decisões de analistas |

Outras opções: `--rapido` (sem efeito de digitação), `--passo` (ENTER a cada etapa), `--sem-cor`,
`--auto` (demo 04 aprova sozinha), `--sem-erro` (demo 03 sem o erro proposital no rascunho v1).

## Estrutura: cada arquivo é uma peça da anatomia do agente

```
llm.py           o cérebro: adaptadores Claude e GPT atrás de uma interface única (+ simulado)
ferramentas.py   as mãos: dados fictícios, funções e o catálogo (JSON Schema) entregue ao modelo
agente.py        o ciclo: perceber → planejar → agir → observar, com memória e instruções
guardrails.py    os limites: prompt injection, alçada, pré-condições, mascaramento e auditoria
console.py       cores, efeito de digitação e opções de linha de comando
00 … 05          as demonstrações
```

## Bom saber

- Com LLM real, o texto e às vezes a ordem dos passos mudam a cada execução. **Os guardrails não mudam**:
  alçada, pré-condições e bloqueio de manipulação são verificados no código.
- Na demo 03, o rascunho v1 recebe dois erros **de propósito** para mostrar o Revisor; use `--sem-erro` para desligar.
- Cada execução grava `auditoria_*.jsonl` na pasta, com CPF e nomes mascarados. Pode apagar depois.
- Se a internet falhar no dia, rode com `--provedor simulado` ou use o replay do slide de demonstração.
