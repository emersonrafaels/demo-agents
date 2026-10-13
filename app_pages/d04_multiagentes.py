"""DEMO 04 (web) — Multiagentes: o orquestrador aciona especialistas; o Revisor barra o rascunho errado."""

import streamlit as st

from agente import multiagentes
from agente.dados import CLIENTES
from agente.multiagentes import MODOS_RASCUNHO, Equipe
from utils import web
from utils.roteiro import CASOS_MULTIAGENTES

AGENTES = {   # quem fala → ícone
    "Orquestrador": ":material/account_tree:", "Fraude": ":material/policy:", "Políticas": ":material/gavel:",
    "Atendimento": ":material/support_agent:", "Revisor": ":material/fact_check:", "Você": ":material/person:",
}

ss = st.session_state
ss.setdefault("d04_casos", [])

st.title("Multiagentes")
st.caption("Especialistas com instruções e acessos próprios. O orquestrador decide quem acionar; o Revisor só "
           "libera a resposta ao cliente dentro da política.")
esquerda, direita = st.columns([3, 2], gap="large")


def fala(de, para, texto, tipo=""):
    """Cada mensagem entre agentes vira uma bolha de chat com o ícone de quem fala."""
    with st.chat_message(de, avatar=AGENTES.get(de, ":material/smart_toy:")):
        marca = {"ok": ":green-badge[:material/check: aprovado] ", "erro": ":red-badge[:material/close: problema] "}
        st.markdown(f"**{de}** → {para}  \n{marca.get(tipo, '')}{web.md(texto)}")


def mostrar_caso(c):
    st.markdown(f"#### {web.md(c['caso'])}")
    st.caption(f"{CLIENTES[c['cliente']]['nome']} ({c['cliente']}) • rascunho: {MODOS_RASCUNHO[c['modo']]}")
    for f in c["falas"]:
        fala(*f)
    if c.get("final"):
        st.success(web.md(c["final"]["resposta"]), icon=":material/mark_email_read:")
        st.caption(f"Especialistas acionados: {' → '.join(c['final']['ferramentas'])} • "
                   f"{c['final']['segundos']} s")


with esquerda:
    with st.container(border=True):
        rotulos = {f"{c} • {t}": (c, t) for c, t in CASOS_MULTIAGENTES}
        escolhido = st.selectbox("Caso", [*rotulos, "Escrever outro caso…"], key="d04_escolha")
        if escolhido in rotulos:
            cliente, caso = rotulos[escolhido]
        else:
            cliente = st.selectbox("Cliente", list(CLIENTES), format_func=lambda c: f"{CLIENTES[c]['nome']} ({c})",
                                   key="d04_cliente")
            caso = st.text_input("Descreva o caso", key="d04_caso",
                                 placeholder="Ex.: Cliente não reconhece uma compra de R$ 459,00.")
        modo = st.segmented_control("Rascunho v1 da resposta", list(MODOS_RASCUNHO), default="erro", required=True,
                                    format_func=MODOS_RASCUNHO.get, key="d04_modo")
        rascunho = ""
        if modo == "voce":
            rascunho = st.text_area("Seu rascunho v1 — tente passar algo errado pelo Revisor",
                                    value=f"Olá {CLIENTES[cliente]['nome']}, o estorno é definitivo.", key="d04_rascunho")
        resolver = st.button("Resolver caso", type="primary", icon=":material/play_arrow:", disabled=not caso)

    if resolver:
        registro = {"caso": caso, "cliente": cliente, "modo": modo, "falas": []}
        st.markdown(f"#### {web.md(caso)}")
        with st.status(":shimmer[O time de agentes está trabalhando…]", expanded=True) as status:
            def ao_falar(de, para, texto, tipo=""):
                registro["falas"].append((de, para, texto, tipo))
                fala(de, para, texto, tipo)

            equipe = Equipe(web.llm(), cliente, modo_rascunho=modo, ao_falar=ao_falar,
                            rascunho_humano=lambda _cliente, _protocolo: rascunho)
            try:
                registro["final"] = equipe.resolver(caso)
                status.update(label=f"Caso resolvido • {len(registro['falas'])} mensagens entre agentes",
                              state="complete", expanded=True)
            except Exception as e:
                status.update(label="Falha na chamada ao modelo", state="error")
                st.error(f"{type(e).__name__}: {str(e)[:300]}")
        if registro.get("final"):
            st.success(web.md(registro["final"]["resposta"]), icon=":material/mark_email_read:")
            ss.d04_casos.insert(0, registro)
            anteriores = ss.d04_casos[1:]
        else:
            anteriores = ss.d04_casos
    else:
        anteriores = ss.d04_casos

    for c in anteriores:
        with st.expander(f"{c['cliente']} • {c['caso']}", icon=":material/history:"):
            mostrar_caso(c)

with direita:
    st.subheader("Por dentro")
    web.codigo("Especialistas viram ferramentas do orquestrador",
               "Para o orquestrador, cada especialista é **só mais uma ferramenta**: nome, descrição e um pedido em "
               "texto. O modelo decide quando acionar cada um, como faria com qualquer sistema.",
               web.fonte(multiagentes.como_ferramenta), web.fonte(Equipe.ferramentas), aberto=True,
               icone=":material/account_tree:")
    web.codigo("Cada especialista é um agente com acesso mínimo",
               "O Agente de Fraude recebe **só as 3 ferramentas de que precisa** (`selecionar`) e guardrails de "
               "escopo. Não consegue bloquear cartão nem estornar: permissão mínima.",
               web.fonte(Equipe.fraude), icone=":material/policy:")
    web.codigo("Atendimento ⇄ Revisor: um agente confere o outro",
               "O Revisor recebe o rascunho e responde em JSON se aprova. Se reprovar, o Atendimento reescreve "
               "com os motivos — até 3 rodadas. O erro nunca chega ao cliente.",
               web.trecho(Equipe.atendimento, "revisor", "for rodada", "rascunho", "parecer", "aprovado",
                          "problemas", "return"),
               web.bloco_arquivo("agente/multiagentes.py", "INSTR_REVISOR =", "}'"), icone=":material/fact_check:")
