"""DEMO 03 (web) — O ciclo do agente: perceber → planejar → agir → observar, ao vivo; Claude × GPT."""

import json
import os

import streamlit as st

from agente import FERRAMENTAS_CARTAO, Agente, Auditoria, BaseConhecimento, Guardrails, Memoria
from agente.dados import CLIENTES
from utils import web
from utils.roteiro import CICLO, CLIENTE_PADRAO

ARQUIVO = "auditoria_demo03.jsonl"


def montar(llm, cliente):
    return Agente(llm, memoria=Memoria(), ferramentas=FERRAMENTAS_CARTAO, conhecimento=BaseConhecimento(),
                  guardrails=Guardrails(cliente_sessao=cliente, auditoria=Auditoria(ARQUIVO)),
                  nome=f"ciclo-{llm.nome}", verboso=False)


ss = st.session_state
ss.setdefault("d03_turnos", [])
ss.setdefault("d03_conversa", 0)
novas = web.mensagens("d03")

st.title("O ciclo do agente")
st.caption("Ninguém programou a ordem dos passos: a cada volta o modelo decide o próximo passo com base no que "
           "já descobriu. Mande uma mensagem e acompanhe.")
chat, direita = st.columns([3, 2], gap="large")

with chat:
    with st.container(horizontal=True, vertical_alignment="bottom"):
        cliente = st.selectbox("Cliente logado no canal", list(CLIENTES), key="d03_cliente",
                               index=list(CLIENTES).index(CLIENTE_PADRAO),
                               format_func=lambda c: f"{CLIENTES[c]['nome']} ({c})")
        comparar = st.toggle("Comparar Claude × GPT", key="d03_comparar",
                             help="O MESMO agente (instruções, ferramentas e guardrails) em dois modelos.")
        if st.button("Nova conversa", icon=":material/restart_alt:"):
            ss.d03_conversa += 1
    nomes = ["claude", "gpt"] if comparar else [ss.provedor]
    config = (tuple(nomes), ss.modelo, cliente, ss.d03_conversa)
    agentes, mudou = web.sessao("d03_agentes", config,
                                lambda: [montar(web.llm(n, "" if comparar else None), cliente) for n in nomes])
    if mudou:
        ss.d03_turnos = []
    web.sugestoes("d03", CICLO)

    for t in ss.d03_turnos:
        with st.chat_message("user"):
            st.markdown(web.md(t["mensagem"]))
        for coluna, r in zip(st.columns(len(t["respostas"])), t["respostas"]):
            with coluna, st.chat_message("assistant"):
                if len(t["respostas"]) > 1:
                    st.markdown(f"**{r['provedor']}** · {r['modelo']}")
                web.resposta(r)

    for mensagem in novas:
        with st.chat_message("user"):
            st.markdown(web.md(mensagem))
        respostas = []
        for coluna, agente in zip(st.columns(len(agentes)), agentes):
            with coluna, st.chat_message("assistant"):
                if len(agentes) > 1:
                    st.markdown(f"**{agente.provedor.nome}** · {agente.provedor.modelo}")
                r = web.executar(agente, mensagem, contexto=f"[cliente_id: {cliente}] ", aberto=True)
                if r:
                    st.markdown(web.md(r["resposta"]))
                    web.metricas(r)
                    respostas.append(r)
        if len(respostas) > 1:
            st.dataframe([{"Modelo": r["provedor"], "Voltas no ciclo": r["voltas"], "Ferramentas": len(r["ferramentas"]),
                           "Tokens de entrada": r["tokens_entrada"], "Tokens de saída": r["tokens_saida"],
                           "Tempo (s)": r["segundos"]} for r in respostas],
                         hide_index=True, alt="Comparação do mesmo agente em dois modelos")
        if respostas:
            ss.d03_turnos.append({"mensagem": mensagem, "respostas": respostas})

    if os.path.exists(ARQUIVO):
        with st.expander("Trilha de auditoria", icon=":material/receipt_long:"):
            with open(ARQUIVO, encoding="utf-8") as f:
                eventos = [json.loads(linha) for linha in f.readlines()[-30:]]
            st.dataframe([{"Quando": e["quando"][11:], "Agente": e["agente"], "Tipo": e["tipo"],
                           "Detalhe": e["detalhe"][:120]} for e in eventos],
                         hide_index=True, alt="Últimos eventos da trilha de auditoria, com dados mascarados")

with direita:
    st.subheader("Por dentro")
    web.codigo("O ciclo inteiro em um método",
               "**Perceber** a mensagem (e barrar manipulação) → **planejar**: o modelo lê tudo o que já sabe e "
               "decide → **agir**: o código executa a ferramenta pedida → **observar**: o resultado volta ao "
               "histórico → repete até o modelo responder sem pedir ferramentas. `max_voltas` impede loop infinito.",
               web.fonte(Agente.conversar), aberto=True, icone=":material/autorenew:")
    web.codigo("Agir: quem executa é o código",
               "O modelo só *pede*. O código confere os guardrails, executa e devolve o resultado — inclusive "
               "erros, que voltam ao modelo como informação.",
               web.fonte(Agente._agir), icone=":material/build:")
