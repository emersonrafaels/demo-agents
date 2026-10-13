"""DEMO 01 (web) — Chatbot × Agente: a mesma mensagem, o mesmo modelo, lado a lado."""

import streamlit as st

from agente import FERRAMENTAS_CARTAO, Agente, BaseConhecimento, Guardrails, Memoria
from agente.dados import CLIENTES
from utils import web
from utils.roteiro import CHATBOT_VS_AGENTE, CLIENTE_PADRAO

INSTR_CHATBOT = ("Você é o chatbot de FAQ de um banco. Responda em até 3 frases, em português, apenas "
                 "orientando o cliente. Você não tem acesso a nenhum sistema.")


def montar(llm, cliente):
    """A única diferença entre os dois: as peças encaixadas ao redor do MESMO modelo."""
    chatbot = Agente(llm, INSTR_CHATBOT, memoria=Memoria(), verboso=False, nome="chatbot")
    agente = Agente(llm, memoria=Memoria(), ferramentas=FERRAMENTAS_CARTAO, conhecimento=BaseConhecimento(),
                    guardrails=Guardrails(cliente_sessao=cliente), verboso=False, nome="contestacoes")
    return chatbot, agente


def acoes(r):
    return sum(a["status"] in ("executada", "aprovada") for a in r["acoes"])


def lado(titulo, icone, r, ao_vivo=None):
    with st.container(border=True):
        st.markdown(f"**{icone} {titulo}**")
        if ao_vivo:
            r = ao_vivo()
            if r:
                st.markdown(web.md(r["resposta"]))
                web.metricas(r)
        elif r:
            web.resposta(r)
    return r


ss = st.session_state
ss.setdefault("d01_turnos", [])
ss.setdefault("d01_conversa", 0)
novas = web.mensagens("d01")

st.title("Chatbot × agente")
st.caption("Você fala como cliente. A mesma mensagem vai ao MESMO modelo duas vezes: como chatbot (só conversa) "
           "e como agente (com memória, ferramentas, conhecimento e guardrails).")
chat, direita = st.columns([3, 2], gap="large")

with chat:
    with st.container(horizontal=True, vertical_alignment="bottom"):
        cliente = st.selectbox("Cliente logado no canal", list(CLIENTES), key="d01_cliente",
                               index=list(CLIENTES).index(CLIENTE_PADRAO),
                               format_func=lambda c: f"{CLIENTES[c]['nome']} ({c})")
        if st.button("Nova conversa", icon=":material/restart_alt:"):
            ss.d01_conversa += 1
    (chatbot, agente), mudou = web.sessao("d01_pecas", (ss.provedor, ss.modelo, cliente, ss.d01_conversa),
                                         lambda: montar(web.llm(), cliente))
    if mudou:
        ss.d01_turnos = []
    placar = st.container()
    web.sugestoes("d01", CHATBOT_VS_AGENTE)

    for t in ss.d01_turnos:
        with st.chat_message("user"):
            st.markdown(web.md(t["mensagem"]))
        esq, dir_ = st.columns(2)
        with esq:
            lado("Chatbot", ":material/chat:", t["chatbot"])
        with dir_:
            lado("Agente", ":material/smart_toy:", t["agente"])

    for mensagem in novas:
        with st.chat_message("user"):
            st.markdown(web.md(mensagem))
        esq, dir_ = st.columns(2)
        with esq:
            r1 = lado("Chatbot", ":material/chat:", None, lambda: web.executar(chatbot, mensagem))
        with dir_:
            r2 = lado("Agente", ":material/smart_toy:", None,
                      lambda: web.executar(agente, mensagem, contexto=f"[cliente_id: {cliente}] "))
        if r1 and r2:
            ss.d01_turnos.append({"mensagem": mensagem, "chatbot": r1, "agente": r2})

    with placar:
        if ss.d01_turnos:
            ag = [t["agente"] for t in ss.d01_turnos]
            cb = [t["chatbot"] for t in ss.d01_turnos]
            with st.container(horizontal=True):
                st.metric("Consultas a sistemas", sum(len(r["ferramentas"]) for r in ag), border=True,
                          delta="chatbot: 0", delta_color="off")
                st.metric("Ações executadas", sum(acoes(r) for r in ag), border=True,
                          delta="chatbot: 0", delta_color="off")
                st.metric("Tokens do agente", sum(r["tokens_entrada"] + r["tokens_saida"] for r in ag), border=True,
                          delta=f"chatbot: {sum(r['tokens_entrada'] + r['tokens_saida'] for r in cb)}",
                          delta_color="off")

with direita:
    st.subheader("Por dentro")
    web.codigo("O mesmo modelo, peças diferentes",
               "Os dois usam **o mesmo `llm`**. O chatbot recebe só instruções e memória; o agente recebe também "
               "ferramentas, conhecimento e guardrails. É isso que separa *responder* de *resolver*.",
               web.fonte(montar), aberto=True)
    web.peca("llm")
    web.peca("ferramentas")
