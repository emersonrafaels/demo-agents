"""DEMO 05 (web) — Guardrails: tente quebrar o agente; você é o analista que aprova acima da alçada."""

import json
import os

import streamlit as st

from agente import FERRAMENTAS_CARTAO, Agente, Auditoria, BaseConhecimento, Guardrails, Memoria, avaliacao
from agente.dados import CLIENTES
from agente.ferramentas import CATALOGO
from utils import web
from utils.console import brl
from utils.roteiro import CASOS_GUARDRAILS

ARQUIVO = "auditoria_demo05.jsonl"
COR_DECISAO = {"entrada": "violet", "escopo": "violet", "precondicao": "violet", "pendente": "orange",
               "humano": "orange", "agente": "green", "sem_estorno": "gray"}
CASOS = {mensagem: (cliente, rotulo) for cliente, mensagem, rotulo in CASOS_GUARDRAILS}
MODOS = {"perguntar": "Eu decido na hora", "aprovar": "Aprovar sempre", "negar": "Negar sempre"}

ss = st.session_state
ss.setdefault("d05_historico", [])
ss.setdefault("d05_pendente", None)
ss.setdefault("d05_conversa", 0)
auditoria = Auditoria(ARQUIVO)


def aprovador(chamada) -> bool:
    """Chamado pelo guardrail de alçada. No modo 'Eu decido na hora', a ação fica pendente até o clique."""
    modo = ss.get("d05_modo", "perguntar")
    if modo != "perguntar":
        return modo == "aprovar"
    ss.d05_pendente = {"ferramenta": chamada.nome, "args": dict(chamada.args)}
    return False


def escolher_caso():
    """Um caso pronto já vem com o cliente da sessão: troca o cliente logado e manda a mensagem."""
    if (mensagem := ss.get("d05_sugestao")) is not None:
        ss.d05_cliente = CASOS[mensagem][0]
        ss.d05_fila.append(mensagem)
        ss.d05_sugestao = None


def decidir(aprovado: bool):
    """O analista decide: aprovado, o sistema executa a ação; em ambos os casos, fica na auditoria e na conversa."""
    p, ss.d05_pendente = ss.d05_pendente, None
    auditoria.registrar("analista", "decisao_humana", {**p, "aprovado": aprovado})
    valor = brl(float(p["args"].get("valor", 0)))
    if aprovado:
        resultado = CATALOGO[p["ferramenta"]].funcao(**p["args"])
        auditoria.registrar("analista", "ferramenta", {"nome": p["ferramenta"], "args": p["args"]})
        texto = f"Analista APROVOU: estorno provisório de {valor} ({p['args'].get('transacao_id')}) criado."
    else:
        resultado = None
        texto = f"Analista NEGOU o estorno de {valor} ({p['args'].get('transacao_id')})."
    ss.d05_historico.append({"papel": "analista", "texto": texto, "aprovado": aprovado, "resultado": resultado})
    if ss.d05_agente.memoria:                         # o agente fica sabendo na próxima mensagem
        ss.d05_agente.memoria.registrar([{"tipo": "usuario", "texto": f"[Sistema] {texto}"}])


st.title("Guardrails: tente quebrar o agente")
st.caption("Autonomia é decisão de negócio; as proteções ficam no código e valem para qualquer modelo.")
novas = web.mensagens("d05", "Tente fazer o agente errar…")
chat, direita = st.columns([3, 2], gap="large")

with chat:
    with st.container(border=True):
        with st.container(horizontal=True, vertical_alignment="bottom"):
            cliente = st.selectbox("Cliente logado", list(CLIENTES), key="d05_cliente",
                                   format_func=lambda c: f"{CLIENTES[c]['nome']} ({c})")
            alcada = st.number_input("Alçada do agente (R$)", min_value=0.0, value=2000.0, step=1000.0,
                                     key="d05_alcada", help="Acima disso, só com aprovação humana.")
            if st.button("Nova conversa", icon=":material/restart_alt:"):
                ss.d05_conversa += 1
        st.segmented_control("Aprovação acima da alçada", list(MODOS), default="perguntar", required=True,
                             format_func=MODOS.get, key="d05_modo")
    agente, mudou = web.sessao(
        "d05_agente", (ss.provedor, ss.modelo, cliente, alcada, ss.d05_conversa),
        lambda: Agente(web.llm(), memoria=Memoria(), ferramentas=FERRAMENTAS_CARTAO, conhecimento=BaseConhecimento(),
                       guardrails=Guardrails(cliente_sessao=cliente, alcada=alcada, aprovador=aprovador,
                                             auditoria=auditoria),
                       nome=f"sessao-{cliente}", verboso=False))
    if mudou and ss.d05_historico:
        ss.d05_historico.append({"papel": "divisor", "texto": f"Nova sessão: {CLIENTES[cliente]['nome']} ({cliente}) "
                                                             f"• alçada {brl(alcada)}"})
        ss.d05_pendente = None

    st.pills("Casos e ataques prontos", list(CASOS), key="d05_sugestao", on_change=escolher_caso,
             format_func=lambda m: f"{CASOS[m][1]} ({CASOS[m][0]})")

    def decisao(r):
        codigo, descricao = avaliacao.quem_decidiu(r)
        st.markdown(f":{COR_DECISAO[codigo]}-badge[:material/gavel: {descricao}]")

    for e in ss.d05_historico:
        if e["papel"] == "divisor":
            st.divider()
            st.markdown(f":material/badge: **{web.md(e['texto'])}**")
        elif e["papel"] == "user":
            with st.chat_message("user"):
                st.markdown(web.md(e["texto"]))
        elif e["papel"] == "analista":
            with st.chat_message("analista", avatar=":material/person_check:"):
                (st.success if e["aprovado"] else st.warning)(web.md(e["texto"]))
        else:
            with st.chat_message("assistant"):
                web.resposta(e["r"])
                decisao(e["r"])

    for mensagem in novas:
        ss.d05_historico.append({"papel": "user", "texto": mensagem})
        with st.chat_message("user"):
            st.markdown(web.md(mensagem))
        with st.chat_message("assistant"):
            r = web.executar(agente, mensagem, contexto=f"[cliente_id: {cliente}] ")
            if r:
                st.markdown(web.md(r["resposta"]))
                web.metricas(r)
                decisao(r)
                ss.d05_historico.append({"papel": "assistant", "r": r})

    if p := ss.d05_pendente:
        with st.container(border=True):
            st.markdown("### :material/front_hand: Pedido de aprovação")
            st.markdown(f"O agente propôs **{p['ferramenta']}** na transação **{p['args'].get('transacao_id')}**, "
                        f"valor **{web.md(brl(float(p['args'].get('valor', 0))))}** — acima da alçada de "
                        f"{web.md(brl(alcada))}. O código pausou a ação e espera você.")
            with st.container(horizontal=True):
                st.button("Aprovar", type="primary", icon=":material/check:", on_click=decidir, args=(True,))
                st.button("Negar", icon=":material/close:", on_click=decidir, args=(False,))

    if os.path.exists(ARQUIVO):
        with st.expander("Trilha de auditoria (CPF e nomes mascarados)", icon=":material/receipt_long:"):
            with open(ARQUIVO, encoding="utf-8") as f:
                eventos = [json.loads(linha) for linha in f.readlines()[-40:]]
            st.dataframe([{"Quando": e["quando"][11:], "Quem": e["agente"], "Tipo": e["tipo"],
                           "Detalhe": e["detalhe"][:140]} for e in reversed(eventos)],
                         hide_index=True, alt="Últimos eventos da trilha de auditoria")

with direita:
    st.subheader("Por dentro")
    web.codigo("Antes de qualquer ação, o código decide",
               "Cada pedido de ferramenta passa por aqui **antes** de executar: escopo (só o cliente logado), "
               "pré-condições (analisar risco e consultar a política), modo sombra e alçada com aprovação humana. "
               "O modelo não tem como pular essas linhas.",
               web.fonte(Guardrails.verificar_acao), aberto=True, icone=":material/shield:")
    web.codigo("Entrada: manipulação nem chega ao modelo",
               "Padrões de *prompt injection* são barrados antes da chamada ao modelo.",
               web.bloco_arquivo("agente/guardrails.py", "PADROES_INJECAO = [", "]"),
               web.fonte(Guardrails.verificar_entrada),
               web.trecho(Agente.conversar, "verificar_entrada", "GUARDRAIL", "bloqueado"),
               icone=":material/block:")
    web.codigo("Auditoria: cada decisão vira uma linha de log",
               "Tudo é registrado — inclusive a decisão do analista — com CPF e nomes mascarados.",
               web.fonte(Auditoria.registrar), icone=":material/receipt_long:")
