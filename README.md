# Demonstração: Agentes de IA com Claude, GPT e Iara

Códigos que acompanham o deck **"Agentes de IA — do assistente que responde ao colaborador digital que resolve"**.
As demos fazem **chamadas reais** às APIs do **Claude (Anthropic)** e do **GPT (OpenAI)**; a conexão com a
**Iara** está preparada para ser implementada no ambiente do banco. Caso usado: **contestação de compra no
cartão**, com dados 100% fictícios.

## Preparação (uma vez)

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="..."     # Claude
export OPENAI_API_KEY="..."        # GPT
python 00_teste_conexao.py         # confere Claude, GPT e Iara
```

Windows PowerShell: `$env:ANTHROPIC_API_KEY="..."`. Veja `.env.exemplo` para todas as variáveis.

> Use apenas chaves e ambientes aprovados pela governança do banco, e somente dados fictícios.

## Estrutura

```
utils/                       conexões com os modelos (uma por fornecedor) + console
  base.py                    contrato comum: Provedor.conversar(instrucoes, historico, ferramentas) -> Resposta
  conexao_anthropic.py       Claude
  conexao_openai.py          GPT (aceita gateway via OPENAI_BASE_URL)
  conexao_iara.py            Iara — EM BRANCO, a implementar no ambiente do banco
  conexao_simulada.py        ensaio offline (regras locais, não é um LLM)
  console.py                 cores, efeito de digitação e opções de linha de comando

agente/                      as peças de um agente, uma por arquivo (espelham o slide "Anatomia")
  ciclo.py                   Agente: perceber → planejar → agir → observar
  instrucoes.py              objetivo e instruções, montadas conforme as peças presentes
  memoria.py                 memória da conversa
  ferramentas.py             ferramentas de cartão (consultas e ações)
  conhecimento.py            busca de conhecimento (BM25) na pasta base_conhecimento/
  guardrails.py              entrada, escopo, pré-condições, alçada, modo sombra, saída e auditoria
  dados.py                   dados fictícios dos "sistemas" do banco

base_conhecimento/           políticas e normas fictícias em Markdown (o que o agente consulta)
00 … 06                      as demonstrações
```

Montar um agente é encaixar peças:

```python
from utils import criar_provedor
from agente import Agente, Memoria, BaseConhecimento, Guardrails, FERRAMENTAS_CARTAO

llm = criar_provedor("claude")                       # ou "gpt", "iara", "simulado"
agente = Agente(llm,
                memoria=Memoria(),
                ferramentas=FERRAMENTAS_CARTAO,
                conhecimento=BaseConhecimento(),
                guardrails=Guardrails(cliente_sessao="C-1001", alcada=2000))
agente.conversar("Não reconheço uma compra de R$ 1.249,90")
```

## Implementando a Iara

Preencha `utils/conexao_iara.py`: a classe `ProvedorIara` precisa só de `__init__` (criar o cliente) e
`conversar` (converter instruções, histórico e ferramentas para o formato da Iara e devolver uma `Resposta`).
Use `conexao_anthropic.py` e `conexao_openai.py` como modelo. Nada mais no projeto precisa mudar:
depois disso, todas as demos rodam com `--provedor iara`.

## Escolhendo o modelo

| Opção | Efeito |
|---|---|
| `--provedor claude` | Claude, modelo em `MODELO_CLAUDE` (padrão `claude-sonnet-5-5`) |
| `--provedor gpt` | GPT, modelo em `MODELO_GPT` (padrão `gpt-5.6`) |
| `--provedor iara` | Iara, depois de implementada |
| `--provedor ambos` | Só na demo 03: roda o mesmo agente no Claude e no GPT e compara |
| `--provedor simulado` | Ensaio offline, sem chave e sem custo |
| `--modelo NOME` | Sobrescreve o modelo daquela execução |

Confira os nomes de modelo disponíveis na sua conta antes do evento.

## Roteiro sugerido (≈ 18 min)

| Capítulo do deck | Comando | O que mostrar |
|---|---|---|
| 1 • Chatbot × Agente | `python 01_chatbot_vs_agente.py --provedor claude` | O mesmo modelo: sem peças orienta, com peças resolve |
| 2 • Anatomia e evolução | `python 02_evolucao_do_agente.py --provedor claude` | A mesma conversa em 5 níveis, do LLM puro ao agente completo |
| 2 • Ciclo | `python 03_ciclo_do_agente.py --provedor claude --passo` | O modelo explica e escolhe cada passo; ENTER avança |
| 3 • Demonstração | `python 03_ciclo_do_agente.py --provedor ambos` | Mesmo agente em Claude e GPT, com tokens e tempo |
| 4 • Multiagentes | `python 04_multiagentes.py --provedor gpt` | O orquestrador aciona especialistas; o Revisor barra o rascunho |
| 4 • Guardrails | `python 05_guardrails.py --provedor claude` | Automático, aprovação humana, manipulação e conta de terceiro |
| 6 • Como começar | `python 06_modo_sombra.py --provedor claude` | Concordância do agente com decisões de analistas |

Outras opções: `--rapido` (sem efeito de digitação), `--passo` (ENTER a cada etapa), `--sem-cor`,
`--nivel N` e `--detalhe` (demo 02), `--auto` (demo 05 aprova sozinha), `--sem-erro` (demo 04).

## Bom saber

- Com LLM real, o texto e às vezes a ordem dos passos mudam a cada execução. **Os guardrails não mudam**:
  escopo, alçada, pré-condições e bloqueio de manipulação são verificados no código.
- Na demo 02, com um modelo real, os níveis 3 e 4 às vezes recusam sozinhos o pedido sobre a conta de outro
  cliente. É exatamente o ponto: sem guardrails, a proteção depende do modelo; no nível 5, do código.
- Na demo 04, o rascunho v1 recebe dois erros **de propósito** para mostrar o Revisor; `--sem-erro` desliga.
- A base de conhecimento e as políticas são **fictícias**. Cada execução grava `auditoria_*.jsonl`, com CPF e
  nomes mascarados; pode apagar depois.
- Sem internet no dia? Rode com `--provedor simulado` ou use o replay do slide de demonstração.
