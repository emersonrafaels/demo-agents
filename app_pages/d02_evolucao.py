"""DEMO 02 (web) — A evolução do agente: escolha as peças e converse com o agente."""

import streamlit as st

from agente import FERRAMENTAS_CARTAO, Agente, Auditoria, BaseConhecimento, Guardrails, Memoria, avaliacao
from agente.dados import CLIENTES
from utils import web
from utils.roteiro import CLIENTE_PADRAO as CLIENTE
from utils.roteiro import EVOLUCAO

PECAS = {   # chave: (rótulo, ícone, linha de código, o que acrescenta)
    "memoria": ("Memória", ":material/memory:", "memoria=Memoria()", "lembra da conversa"),
    "ferramentas": ("Ferramentas", ":material/build:", "ferramentas=FERRAMENTAS_CARTAO", "consulta sistemas e age"),
    "conhecimento": ("Busca de conhecimento", ":material/menu_book:", "conhecimento=BaseConhecimento()",
                     "consulta as normas e cita a fonte"),
    "guardrails": ("Guardrails", ":material/shield:", "guardrails=Guardrails(...)",
                   "limites no código, aprovação humana e auditoria"),
}
NIVEIS = {1: [], 2: ["memoria"], 3: ["memoria", "ferramentas"], 4: ["memoria", "ferramentas", "conhecimento"],
          5: ["memoria", "ferramentas", "conhecimento", "guardrails"]}


def montar(llm, pecas, alcada, aprovador):
    """Cada peça marcada vira um argumento do Agente; o modelo é sempre o mesmo."""
    extras = {}
    if "memoria" in pecas:
        extras["memoria"] = Memoria(max_turnos=20)
    if "ferramentas" in pecas:
        extras["ferramentas"] = FERRAMENTAS_CARTAO
    if "conhecimento" in pecas:
        extras["conhecimento"] = BaseConhecimento()
    if "guardrails" in pecas:
        extras["guardrails"] = Guardrails(cliente_sessao=CLIENTE, alcada=alcada, aprovador=aprovador,
                                          auditoria=Auditoria("auditoria_demo02.jsonl"))
    return Agente(llm, nome="evolucao", verboso=False, **extras)


ss = st.session_state
for chave, valor in {"d02_historico": [], "d02_mensagens": [], "d02_anteriores": [], "d02_conversa": 0,
                     **{f"d02_{p}": False for p in PECAS}}.items():
    ss.setdefault(chave, valor)


def aplicar_nivel(n):
    for p in PECAS:
        ss[f"d02_{p}"] = p in NIVEIS[n]


def repetir():
    ss.d02_fila.extend(ss.d02_anteriores)
    ss.d02_anteriores = []


novas = web.mensagens("d02", "Escreva como se fosse a cliente Mariana…")

st.title("A evolução do agente, peça por peça")
st.caption("O modelo é sempre o mesmo. Encaixe as peças à esquerda do chat e veja a mesma conversa mudar de "
           "resultado; à direita, o código que faz cada peça funcionar.")
controles, chat, direita = st.columns([1.1, 2.4, 2], gap="medium")

# ------------------------------------------------------------------ peças
with controles:
    st.markdown("**Níveis prontos**")
    with st.container(horizontal=True, gap="small"):
        for n in NIVEIS:
            st.button(str(n), key=f"d02_nivel_{n}", on_click=aplicar_nivel, args=(n,),
                      help=" + ".join(PECAS[p][0] for p in NIVEIS[n]) or "Só LLM")
    st.markdown("**Peças**")
    st.checkbox(":material/smart_toy: LLM", value=True, disabled=True, help="O modelo é sempre o mesmo.")
    for p, (rotulo, icone, _, descricao) in PECAS.items():
        st.checkbox(f"{icone} {rotulo}", key=f"d02_{p}", help=descricao)
    pecas = [p for p in PECAS if ss[f"d02_{p}"]]
    alcada, aprova = 2000.0, False
    if "guardrails" in pecas:
        alcada = st.number_input("Alçada (R$)", min_value=0.0, value=2000.0, step=500.0, key="d02_alcada")
        aprova = st.toggle("Analista aprova acima da alçada", key="d02_aprova")
    nivel = next((n for n, lista in NIVEIS.items() if lista == pecas), None)
    st.markdown(f"**{'Nível ' + str(nivel) if nivel else 'Montagem personalizada'}**")
    st.code(",\n".join(["agente = Agente(llm"] + [f"    {PECAS[p][2]}" for p in pecas]) + ")", language="python")
    aberto = st.toggle("Abrir o ciclo em cada resposta", key="d02_aberto")
    if st.button("Nova conversa", icon=":material/restart_alt:"):
        ss.d02_conversa += 1
        ss.d02_anteriores = []

# ------------------------------------------------------------------ monta (ou remonta) o agente
config = (ss.provedor, ss.modelo, tuple(pecas), alcada, aprova, ss.d02_conversa)
agente, mudou = web.sessao("d02_agente", config,
                           lambda: montar(web.llm(), pecas, alcada, lambda chamada: aprova))
if mudou:
    if ss.d02_mensagens:
        ss.d02_anteriores = list(ss.d02_mensagens)
        descricao = " + ".join(["LLM"] + [PECAS[p][0] for p in pecas])
        ss.d02_historico.append({"divisor": f"Nova montagem: {descricao}"})
    ss.d02_mensagens = []

# ------------------------------------------------------------------ conversa
with chat:
    web.sugestoes("d02", EVOLUCAO)
    for e in ss.d02_historico:
        if "divisor" in e:
            st.divider()
            st.markdown(f":material/extension: **{web.md(e['divisor'])}**")
        elif e["papel"] == "user":
            with st.chat_message("user"):
                st.markdown(web.md(e["texto"]))
        else:
            with st.chat_message("assistant"):
                web.resposta(e["r"], aberto)
                web.indicadores(e["avaliacao"], e["r"], e["memoria"], alcada)

    if ss.d02_anteriores and not novas:
        st.info(f"As peças mudaram e a conversa recomeçou. Repetir as {len(ss.d02_anteriores)} mensagens "
                "anteriores com a nova montagem?", icon=":material/replay:")
        st.button(f"Repetir {len(ss.d02_anteriores)} mensagens", on_click=repetir, type="primary",
                  icon=":material/replay:")

    for mensagem in novas:
        ss.d02_anteriores = []
        ss.d02_historico.append({"papel": "user", "texto": mensagem})
        with st.chat_message("user"):
            st.markdown(web.md(mensagem))
        with st.chat_message("assistant"):
            r = web.executar(agente, mensagem, aberto=aberto)
            if not r:
                continue
            st.markdown(web.md(r["resposta"]))
            web.metricas(r)
            a = avaliacao.avaliar(len(ss.d02_mensagens), mensagem, r, CLIENTE, "ferramentas" in pecas)
            memoria = agente.memoria.turnos() if agente.memoria else None
            web.indicadores(a, r, memoria, alcada)
        ss.d02_historico.append({"papel": "assistant", "r": r, "avaliacao": a, "memoria": memoria})
        ss.d02_mensagens.append(mensagem)

# ------------------------------------------------------------------ por dentro
with direita:
    st.subheader("Por dentro")
    st.caption(f"Cliente logada no canal: {CLIENTES[CLIENTE]['nome']} ({CLIENTE}). A última peça encaixada aparece aberta.")
    web.codigo("Montando o agente", "Cada checkbox vira um argumento do `Agente`. Nada mais muda.",
               web.fonte(montar))
    for p in ["llm", *PECAS]:
        web.peca(p, aberto=p in pecas[-1:])
