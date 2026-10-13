# Demonstração: Agentes de IA com Claude, GPT e Iara

Códigos que acompanham o deck **"Agentes de IA — do assistente que responde ao colaborador digital que resolve"**.
As demos fazem **chamadas reais** às APIs do **Claude (Anthropic)** e do **GPT (OpenAI)**; a conexão com a
**Iara** está preparada para ser implementada no ambiente do banco. Caso usado: **contestação de compra no
cartão**, com dados 100% fictícios.

## Preparação (uma vez)

```bash
pip install -r requirements.txt
cp .env.exemplo .env               # PowerShell: Copy-Item .env.exemplo .env
# edite o .env e preencha ANTHROPIC_API_KEY (Claude) e/ou OPENAI_API_KEY (GPT)
python 00_teste_conexao.py         # confere Claude, GPT e Iara
```

O `.env` é carregado automaticamente por todas as demos (via `utils/__init__.py`) e está no `.gitignore`.
Variáveis definidas no terminal (`export ...` / `$env:...`) têm prioridade sobre o `.env`. Veja `.env.exemplo` para todas as variáveis.

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
  interativo.py              o "palco" das demos no terminal + abrir_web (o atalho --web)
  roteiro.py                 mensagens e casos prontos, os mesmos no terminal e no navegador
  web.py                     peças da interface web: ciclo ao vivo no chat e o código "por dentro" de cada peça

agente/                      as peças de um agente, uma por arquivo (espelham o slide "Anatomia")
  ciclo.py                   Agente: perceber → planejar → agir → observar
  instrucoes.py              objetivo e instruções, montadas conforme as peças presentes
  memoria.py                 memória da conversa
  ferramentas.py             ferramentas de cartão (consultas e ações)
  conhecimento.py            busca de conhecimento (BM25) na pasta base_conhecimento/
  guardrails.py              entrada, escopo, pré-condições, alçada, modo sombra, saída e auditoria
  dados.py                   dados fictícios dos "sistemas" do banco
  multiagentes.py            orquestrador + especialistas (demo 04)
  modo_sombra.py             propor sem executar e comparar com o analista (demo 06)
  avaliacao.py               o que uma resposta demonstrou: lembrou, resolveu, citou fonte, protegeu

base_conhecimento/           políticas e normas fictícias em Markdown (o que o agente consulta)
00 … 06                      as demonstrações no terminal
streamlit_app.py             o app web: todas as demonstrações no navegador
app_pages/                   uma página por demonstração (+ início)
.streamlit/config.toml       app só nesta máquina (localhost), sem telemetria, cor de destaque
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

## No navegador (app web)

> **Vai apresentar?** Siga o [ROTEIRO_APRESENTACAO.md](ROTEIRO_APRESENTACAO.md): checklist, cliques, falas e perguntas prováveis para cada demo.

```bash
python streamlit_app.py --provedor claude              # abre o app com todas as demos
python 05_guardrails.py --provedor claude --web        # qualquer demo com --web abre direto na página dela
```

O modelo é escolhido na barra lateral e vale para todas as páginas. Cada página tem, à direita, o painel
**Por dentro**: o trecho de código que faz aquela peça funcionar (ex.: o que dá memória ao agente), com
uma explicação em linguagem de negócio. O código é lido do próprio projeto em execução (não é cópia), então
o que aparece na tela é exatamente o que está rodando.

| Página | Interação |
|---|---|
| 00 • Teste de conexão | Testa os modelos marcados e mostra tempo e tokens |
| 01 • Chatbot × agente | Chatbot e agente respondem lado a lado; placar acumulado no topo |
| 02 • Evolução | Peças em checkboxes (ou níveis 1–5) + chat; ao mudar peças, "Repetir mensagens" refaz a conversa |
| 03 • Ciclo | Linha do tempo perceber → planejar → agir → observar; "Comparar Claude × GPT" lado a lado |
| 04 • Multiagentes | Escolha o caso e como nasce o rascunho; "você escreve o v1" desafia o Revisor |
| 05 • Guardrails | Casos e ataques prontos; acima da alçada aparecem os botões **Aprovar / Negar** para o analista |
| 06 • Modo sombra | Tabela editável de casos, ajustes nas instruções e nova rodada; concordância × meta |

## Roteiro sugerido (≈ 20 min) — todas as demos são interativas

Em todas as demos você digita como se fosse o cliente (ou o analista) e o agente responde ao vivo.
Para não digitar no palco, **um número escolhe uma mensagem pronta**; `/ajuda` lista os comandos e `/sair`
encerra mostrando o placar. Erro de rede ou `Ctrl+C` interrompem só a mensagem atual, não a demo.

| Capítulo do deck | Comando | Como conduzir |
|---|---|---|
| 1 • Chatbot × Agente | `python 01_chatbot_vs_agente.py --provedor claude` | Cada mensagem vai ao chatbot e ao agente, lado a lado. Peça à plateia uma pergunta de cliente. `/cliente C-1002` troca o cliente logado |
| 2 • Anatomia e evolução | `python 02_evolucao_do_agente.py --provedor claude` | Comece no nível 1 com as mensagens 1 e 2. Digite `+` para encaixar a próxima peça e responda **S** para repetir a conversa no novo nível. `/comparar` mostra o placar dos 5 níveis |
| 2 • Ciclo | `python 03_ciclo_do_agente.py --provedor claude` | ENTER avança cada etapa (perceber → planejar → agir → observar). `/passo` desliga, `/trilha` mostra a auditoria |
| 3 • Demonstração | `python 03_ciclo_do_agente.py --provedor ambos` | Cada mensagem roda no Claude e no GPT, com voltas, tokens e tempo |
| 4 • Multiagentes | `python 04_multiagentes.py --provedor gpt` | Escolha um caso. `/rascunho voce` deixa **um executivo escrever o rascunho** e tentar passar algo errado pelo Revisor |
| 4 • Guardrails | `python 05_guardrails.py --provedor claude` | "Tente quebrar o agente": casos 1–6 prontos ou ataques da plateia. Um executivo aprova/nega acima da alçada. `/alcada 10000` muda a decisão de negócio ao vivo |
| 6 • Como começar | `python 06_modo_sombra.py --provedor claude` | ENTER roda os casos; digite o número de um caso divergente para ver o raciocínio; `/ajuste` acrescenta uma instrução e ENTER mede de novo. `/novo` cadastra um caso, `/meta 95` muda a meta |

Opções de linha de comando: `--rapido` (sem efeito de digitação), `--passo` (ENTER a cada etapa), `--sem-cor`,
`--nivel N` e `--detalhe` (demo 02), `--auto` (demo 05 aprova sozinha), `--sem-erro` (demo 04 começa com a IA
escrevendo o rascunho), `--web` (abre a demo no navegador), `--porta N` (porta do app web), `--debug` (mostra o erro completo se uma chamada falhar).

## Bom saber

- Com LLM real, o texto e às vezes a ordem dos passos mudam a cada execução. **Os guardrails não mudam**:
  escopo, alçada, pré-condições e bloqueio de manipulação são verificados no código.
- Na demo 02, com um modelo real, os níveis 3 e 4 às vezes recusam sozinhos o pedido sobre a conta de outro
  cliente. É exatamente o ponto: sem guardrails, a proteção depende do modelo; no nível 5, do código.
- Na demo 04, por padrão o rascunho v1 recebe dois erros **de propósito** para mostrar o Revisor; `/rascunho ia`
  ou `--sem-erro` desliga, `/rascunho voce` deixa o apresentador escrever o v1.
- O modo `--provedor simulado` segue regras fixas: serve para ensaiar o roteiro com as mensagens prontas, mas
  responde mal a perguntas livres. Para mensagens da plateia, use Claude ou GPT.
- A base de conhecimento e as políticas são **fictícias**. Cada execução grava `auditoria_*.jsonl`, com CPF e
  nomes mascarados; pode apagar depois.
- Sem internet no dia? Rode com `--provedor simulado` ou use o replay do slide de demonstração.
