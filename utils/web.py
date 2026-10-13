"""
utils/web.py — peças comuns do app web (Streamlit): conexão com o modelo, o ciclo do agente ao vivo no chat
e os blocos de código "por dentro" de cada demo.

Os blocos de código são lidos do PRÓPRIO código-fonte em execução (inspect), não copiados: o que aparece
na tela é exatamente o que está rodando.
"""

from __future__ import annotations

import inspect
import textwrap
from pathlib import Path

import streamlit as st

from . import criar_provedor
from .console import brl

RAIZ = Path(__file__).resolve().parent.parent
PROVEDORES = ["claude", "gpt", "simulado", "iara"]
ETAPAS = {   # etiqueta do ciclo → (nome na tela, ícone)
    "PERCEBER": ("Perceber", ":material/visibility:"),
    "PLANEJAR": ("Planejar", ":material/route:"),
    "AGIR": ("Agir", ":material/build:"),
    "OBSERVAR": ("Observar", ":material/manage_search:"),
    "GUARDRAIL": ("Guardrail", ":material/shield:"),
    "ALÇADA": ("Alçada", ":material/front_hand:"),
    "SOMBRA": ("Modo sombra", ":material/visibility_off:"),
    "LIMITE": ("Limite de voltas", ":material/block:"),
}
ALERTAS = {"GUARDRAIL", "ALÇADA", "SOMBRA", "LIMITE"}

DEMOS = [
    {"arquivo": "app_pages/d00_conexao.py", "titulo": "00 • Teste de conexão", "icone": ":material/cable:",
     "url": "conexao", "resumo": "Confere Claude, GPT e Iara antes da apresentação: o mesmo contrato para todos."},
    {"arquivo": "app_pages/d01_chatbot_vs_agente.py", "titulo": "01 • Chatbot × agente",
     "icone": ":material/compare_arrows:", "url": "chatbot-vs-agente",
     "resumo": "A mesma pergunta, o mesmo modelo: o chatbot orienta, o agente resolve."},
    {"arquivo": "app_pages/d02_evolucao.py", "titulo": "02 • Evolução do agente", "icone": ":material/extension:",
     "url": "evolucao", "resumo": "Ligue e desligue memória, ferramentas, conhecimento e guardrails e converse."},
    {"arquivo": "app_pages/d03_ciclo.py", "titulo": "03 • Ciclo do agente", "icone": ":material/autorenew:",
     "url": "ciclo", "resumo": "Perceber → planejar → agir → observar, ao vivo; compare Claude e GPT."},
    {"arquivo": "app_pages/d04_multiagentes.py", "titulo": "04 • Multiagentes", "icone": ":material/groups:",
     "url": "multiagentes", "resumo": "Um orquestrador aciona especialistas; o Revisor barra o rascunho errado."},
    {"arquivo": "app_pages/d05_guardrails.py", "titulo": "05 • Guardrails", "icone": ":material/shield:",
     "url": "guardrails", "resumo": "Tente quebrar o agente; aprove ou negue acima da alçada."},
    {"arquivo": "app_pages/d06_modo_sombra.py", "titulo": "06 • Modo sombra", "icone": ":material/visibility_off:",
     "url": "modo-sombra", "resumo": "Meça o agente contra analistas, ajuste e meça de novo antes da autonomia."},
]


def md(texto) -> str:
    """Evita que 'R$ 1,00 ... R$ 2,00' vire fórmula no Markdown do Streamlit."""
    return str(texto or "").replace("$", "\\$")


# ------------------------------------------------------------------ conexão com o modelo
@st.cache_resource(show_spinner=False, max_entries=8)
def _conectar(nome: str, modelo: str):
    return criar_provedor(nome, modelo or None)


def llm(nome: str | None = None, modelo: str | None = None):
    """O modelo escolhido na barra lateral (ou um específico, ex.: llm("gpt")). Para a página se faltar chave."""
    nome = nome or st.session_state.get("provedor", "simulado")
    modelo = st.session_state.get("modelo", "") if modelo is None else modelo
    try:
        return _conectar(nome, modelo)
    except SystemExit as e:                      # criar_provedor avisa por SystemExit (falta chave, SDK...)
        st.error(f"Não foi possível conectar ao provedor **{nome}**: {e}", icon=":material/link_off:")
        st.stop()


# ------------------------------------------------------------------ entrada do apresentador
def _curto(texto: str, n: int = 48) -> str:
    return texto if len(texto) <= n else texto[:n - 1] + "…"


def sugestoes(chave: str, opcoes, rotulo: str = "Mensagens prontas", formato=None) -> None:
    """Mensagens prontas como 'pills': um clique põe a mensagem na fila da página."""
    fila = st.session_state.setdefault(f"{chave}_fila", [])

    def escolher():
        if (valor := st.session_state.get(f"{chave}_sugestao")) is not None:
            fila.append(valor)
            st.session_state[f"{chave}_sugestao"] = None

    st.pills(rotulo, opcoes, key=f"{chave}_sugestao", on_change=escolher, format_func=formato or _curto)


def mensagens(chave: str, placeholder: str = "Escreva como se fosse o cliente…") -> list:
    """O que processar nesta execução: o que veio das sugestões + o que foi digitado no chat."""
    fila = st.session_state.setdefault(f"{chave}_fila", [])
    if digitado := st.chat_input(placeholder, key=f"{chave}_chat"):
        fila.append(digitado)
    novas, fila[:] = list(fila), []
    return novas


def sessao(chave: str, config: tuple, fabrica):
    """Guarda um objeto (agente, equipe...) na sessão e o recria quando a configuração muda.
    Devolve (objeto, mudou)."""
    ss = st.session_state
    mudou = ss.get(f"{chave}__config") != config
    if mudou:
        ss[chave] = fabrica()
        ss[f"{chave}__config"] = config
    return ss[chave], mudou


# ------------------------------------------------------------------ o ciclo do agente no chat
def passo(etiqueta: str, texto: str) -> None:
    nome, icone = ETAPAS.get(etiqueta, (etiqueta.title(), ":material/circle:"))
    estado = "error" if etiqueta in ALERTAS else "complete"
    with st.status(f"{icone} **{nome}**", type="step", state=estado, expanded=True):
        st.markdown(md(texto))


def rotulo_ciclo(r: dict) -> str:
    return (f"Ciclo do agente • {r['voltas']} chamadas ao modelo • {len(r['ferramentas'])} ferramentas • "
            f"{r['segundos']} s")


def executar(agente, mensagem: str, contexto: str = "", aberto: bool = False) -> dict | None:
    """Roda o agente mostrando cada etapa do ciclo ao vivo. Devolve o resultado com os passos em r["passos"]."""
    passos = []

    def eco(etiqueta, texto):
        if etiqueta != "RESPONDER":                  # a resposta aparece logo abaixo, fora do ciclo
            passos.append((etiqueta, texto))
            passo(etiqueta, texto)

    with st.status(":shimmer[O agente está trabalhando…]", type="compact", expanded=True) as status:
        agente.eco = eco
        try:
            r = agente.conversar(mensagem, contexto=contexto)
        except Exception as e:
            status.update(label="Falha na chamada ao modelo", state="error")
            st.error(f"{type(e).__name__}: {str(e)[:300]}")
            return None
        finally:
            agente.eco = None
        status.update(label=rotulo_ciclo(r), state="complete", expanded=aberto)
    r["passos"] = passos
    return r


def ciclo_gravado(r: dict, aberto: bool = False) -> None:
    """Reexibe o ciclo de uma resposta antiga (histórico do chat)."""
    if r.get("passos"):
        with st.status(rotulo_ciclo(r), type="compact", state="complete", expanded=aberto):
            for etiqueta, texto in r["passos"]:
                passo(etiqueta, texto)


def metricas(r: dict) -> None:
    ferramentas = " → ".join(r["ferramentas"]) or "nenhuma"
    st.caption(f":material/build: {ferramentas} • :material/token: {r['tokens_entrada'] + r['tokens_saida']} tokens")


def resposta(r: dict, aberto: bool = False) -> None:
    """Uma resposta do agente vinda do histórico: ciclo (recolhido), texto e métricas."""
    ciclo_gravado(r, aberto)
    st.markdown(md(r["resposta"]))
    metricas(r)


def indicadores(a: dict, r: dict, memoria_turnos: int | None, alcada: float = 2000.0) -> None:
    """O que a resposta demonstrou (veja agente/avaliacao.py), como selos coloridos."""
    from agente.avaliacao import estornos_sem_aprovacao
    selos = []
    if memoria_turnos is None:
        selos.append(":gray-badge[:material/memory: sem memória: a mensagem chegou isolada]")
    else:
        selos.append(f":gray-badge[:material/memory: memória: {memoria_turnos} "
                     f"{'mensagem' if memoria_turnos == 1 else 'mensagens'}]")
    if a["lembra"]:
        selos.append(":green-badge[:material/check: lembrou da cliente]")
    if a["resolve"]:
        selos.append(":green-badge[:material/check: agiu nos sistemas]")
    if a["fonte"]:
        selos.append(":green-badge[:material/check: citou a norma]")
    elif a["sem_fonte"]:
        selos.append(":red-badge[:material/close: prazo sem fonte]")
    if a["invadiu"]:
        selos.append(f":red-badge[:material/close: mexeu na conta de {', '.join(sorted(a['invadiu']))}]")
    elif a["protege"]:
        selos.append(":green-badge[:material/check: protegeu a outra conta]")
    for valor in estornos_sem_aprovacao(r, alcada):
        selos.append(f":red-badge[:material/warning: estorno de {md(brl(valor))} sem aprovação]")
    st.markdown(" ".join(selos))


# ------------------------------------------------------------------ código "por dentro"
def _relativo(caminho) -> str:
    try:
        return Path(caminho).resolve().relative_to(RAIZ).as_posix()
    except ValueError:
        return Path(caminho).name


def fonte(obj) -> tuple[str, str]:
    """Código-fonte completo de uma função, método ou classe: (arquivo, código)."""
    return _relativo(inspect.getsourcefile(obj)), textwrap.dedent(inspect.getsource(obj))


def trecho(obj, *marcas: str, contexto: int = 0) -> tuple[str, str]:
    """Só as linhas de `obj` que contêm alguma das marcas (mais a assinatura), com '...' no que foi omitido."""
    linhas = textwrap.dedent(inspect.getsource(obj)).splitlines()
    fim_assinatura = next(i for i, linha in enumerate(linhas) if linha.split("#")[0].rstrip().endswith(":"))
    manter = set(range(fim_assinatura + 1))                # a assinatura inteira, mesmo em várias linhas
    for i, linha in enumerate(linhas):
        if any(m in linha for m in marcas):
            manter.update(range(max(0, i - contexto), min(len(linhas), i + contexto + 1)))
    saida, anterior = [], -1
    for i in sorted(manter):
        if i != anterior + 1:
            recuo = len(linhas[i]) - len(linhas[i].lstrip())
            saida.append(" " * recuo + "...")
        saida.append(linhas[i])
        anterior = i
    return _relativo(inspect.getsourcefile(obj)), "\n".join(saida)


def bloco_arquivo(caminho: str, inicio: str, fim: str, antes: int = 0) -> tuple[str, str]:
    """Linhas de um arquivo, da primeira que contém `inicio` até a primeira seguinte que contém `fim`."""
    linhas = (RAIZ / caminho).read_text(encoding="utf-8").splitlines()
    i = next(n for n, linha in enumerate(linhas) if inicio in linha) - antes
    j = next(n for n in range(i + antes + 1, len(linhas)) if fim in linhas[n])
    return caminho, textwrap.dedent("\n".join(linhas[i:j + 1]))


def codigo(titulo: str, explicacao: str, *blocos: tuple[str, str], aberto: bool = False, icone=None) -> None:
    """Um 'por dentro' da demo: título, explicação em linguagem de negócio e o código que faz funcionar."""
    with st.expander(titulo, expanded=aberto, icon=icone or ":material/code:"):
        st.markdown(explicacao)
        for arquivo, texto in blocos:
            st.caption(f":material/description: `{arquivo}`")
            st.code(texto, language="python")


# ------------------------------------------------------------------ cada peça, por dentro
def peca(nome: str, aberto: bool = False) -> None:
    """Explicação + o código que faz a peça funcionar. nome: llm | memoria | ferramentas | conhecimento | guardrails"""
    from agente import Agente, BaseConhecimento, Guardrails, Memoria
    from agente.ferramentas import Ferramenta

    if nome == "llm":
        codigo("LLM: o modelo decide o próximo passo",
               "A cada volta, o agente envia ao modelo **instruções + histórico + catálogo de ferramentas**. "
               "O modelo responde com texto ou com um pedido para usar uma ferramenta. Sem as outras peças, "
               "o modelo só conversa.",
               trecho(Agente.conversar, "self.provedor.conversar", "list(self.ferramentas"), aberto=aberto,
               icone=":material/smart_toy:")
    elif nome == "memoria":
        codigo("Memória: reenviar o histórico a cada mensagem",
               "O modelo **não lembra de nada sozinho**: cada chamada é independente. Ter memória é guardar a "
               "conversa e reenviá-la junto com a nova mensagem. Para não crescer sem limite (custo), guardamos "
               "só os últimos N turnos.",
               fonte(Memoria),
               trecho(Agente.conversar, "anteriores"),
               trecho(Agente._fim, "self.memoria"), aberto=aberto, icone=":material/memory:")
    elif nome == "ferramentas":
        codigo("Ferramentas: as mãos do agente",
               "Cada ferramenta tem **nome e descrição** (o modelo lê para decidir quando usar), **parâmetros** "
               "(o modelo preenche) e uma **função** que roda de verdade — aqui, sobre dados fictícios; no banco, "
               "a API de um sistema. Quem executa é o código, nunca o modelo.",
               fonte(Ferramenta),
               bloco_arquivo("agente/ferramentas.py", "def abrir_estorno_provisorio", "}"),
               bloco_arquivo("agente/ferramentas.py", '"abrir_estorno_provisorio",', "icone=", antes=1),
               trecho(Agente.conversar, "if not r.chamadas", "for ch in r.chamadas", "self._agir",
                      "novos.append({\"tipo\": \"resultado\"", "conteudo"),
               trecho(Agente._agir, "f.funcao(**ch.args)", "try:", "except Exception", "erro"),
               aberto=aberto, icone=":material/build:")
    elif nome == "conhecimento":
        codigo("Busca de conhecimento: consultar as normas na hora",
               "O agente não decora as regras do banco: a cada pergunta, **busca os trechos relevantes** nos "
               "documentos oficiais e responde com base neles, citando a fonte (RAG). A busca vira mais uma "
               "ferramenta, e as instruções mandam consultá-la antes de responder.",
               fonte(BaseConhecimento.como_ferramenta),
               fonte(BaseConhecimento.buscar),
               bloco_arquivo("agente/instrucoes.py", "COM_CONHECIMENTO", '"""'),
               aberto=aberto, icone=":material/menu_book:")
    elif nome == "guardrails":
        codigo("Guardrails: limites no código, fora do modelo",
               "O modelo pode errar ou ser manipulado; por isso as regras críticas são **verificadas em código, "
               "antes de qualquer ação**, e valem para qualquer modelo: escopo do cliente logado, pré-condições, "
               "alçada com aprovação humana, bloqueio de manipulação e auditoria.",
               trecho(Agente._agir, "self.guardrails", "verificar_acao", "if not v.permitido", "return v.resultado"),
               fonte(Guardrails.verificar_entrada),
               fonte(Guardrails.verificar_acao),
               aberto=aberto, icone=":material/shield:")
