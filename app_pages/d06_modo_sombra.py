"""DEMO 06 (web) — Modo sombra: medir o agente contra analistas, ajustar e medir de novo antes da autonomia."""

import streamlit as st

from agente import BaseConhecimento, Guardrails
from agente.dados import CLIENTES
from agente.modo_sombra import propor
from utils import web
from utils.roteiro import AJUSTE_SUGERIDO, HISTORICO_SOMBRA

DECISOES = ["ESTORNO", "SEM ESTORNO"]

ss = st.session_state
ss.setdefault("d06_casos", [dict(c) for c in HISTORICO_SOMBRA])
ss.setdefault("d06_rodadas", [])            # [{"rodada", "ajustes", "concordancia", "resultados": [...]}]
ss.setdefault("d06_ajustes", "")


def sugerir_ajuste():
    ss.d06_ajustes = (ss.d06_ajustes.strip() + "\n" + AJUSTE_SUGERIDO).strip()


st.title("Modo sombra: medir antes de dar autonomia")
st.caption("O agente analisa casos já decididos por analistas, mas nada é executado: as ações viram propostas. "
           "Comparamos com a decisão humana, ajustamos o agente e medimos de novo.")
esquerda, direita = st.columns([3, 2], gap="large")

with esquerda:
    st.markdown("**Casos históricos** — edite, acrescente linhas ou mude a decisão do analista")
    casos = st.data_editor(
        ss.d06_casos, num_rows="dynamic", hide_index=True, key="d06_editor",
        column_config={
            "cliente": st.column_config.SelectboxColumn("Cliente", options=list(CLIENTES), required=True,
                                                        default="C-1001", width="small"),
            "mensagem": st.column_config.TextColumn("Mensagem do cliente", required=True, width="large"),
            "humano": st.column_config.SelectboxColumn("Decisão do analista", options=DECISOES, required=True,
                                                       default="ESTORNO"),
        }, alt="Casos históricos com a decisão do analista")
    casos = [c for c in casos if c.get("cliente") and c.get("mensagem") and c.get("humano")]

    with st.container(border=True):
        st.text_area("Ajustes nas instruções do agente (uma por linha)", key="d06_ajustes", height=90,
                     placeholder="Divergiu? Escreva aqui uma instrução a mais e rode de novo.")
        with st.container(horizontal=True, vertical_alignment="center"):
            st.button("Sugerir ajuste", icon=":material/lightbulb:", on_click=sugerir_ajuste)
            meta = st.slider("Meta de concordância (%)", 50, 100, 90, step=5, key="d06_meta")
            rodar = st.button("Rodar em modo sombra", type="primary", icon=":material/play_arrow:",
                              disabled=not casos)

    if rodar:
        ajustes = [a.strip() for a in ss.d06_ajustes.splitlines() if a.strip()]
        conhecimento, resultados = BaseConhecimento(), []
        barra = st.progress(0.0, text="Rodando os casos…")
        for i, caso in enumerate(casos, 1):
            barra.progress((i - 1) / len(casos), text=f"Caso {i} de {len(casos)}: {caso['mensagem'][:60]}")
            passos = []
            try:
                r = propor(web.llm(), caso, conhecimento, ajustes, eco=lambda et, tx: passos.append((et, tx)))
            except Exception as e:
                st.error(f"Caso {i}: {type(e).__name__}: {str(e)[:200]}")
                continue
            r["passos"] = [p for p in passos if p[0] != "RESPONDER"]
            resultados.append({**caso, "r": r, "ok": r["proposta"] == caso["humano"]})
        barra.empty()
        if resultados:
            concordancia = 100 * sum(x["ok"] for x in resultados) / len(resultados)
            ss.d06_rodadas.append({"rodada": len(ss.d06_rodadas) + 1, "ajustes": len(ajustes),
                                   "concordancia": concordancia, "resultados": resultados})
            ss.d06_casos = [{k: c[k] for k in ("cliente", "mensagem", "humano")} for c in casos]

    if ss.d06_rodadas:
        ultima = ss.d06_rodadas[-1]
        anterior = ss.d06_rodadas[-2]["concordancia"] if len(ss.d06_rodadas) > 1 else None
        res = ultima["resultados"]
        with st.container(horizontal=True):
            st.metric("Concordância com os analistas", f"{ultima['concordancia']:.0f}%", border=True,
                      delta=None if anterior is None else f"{ultima['concordancia'] - anterior:+.0f} p.p.",
                      chart_data=[r["concordancia"] for r in ss.d06_rodadas], chart_type="line")
            st.metric("Tokens por caso", sum(x["r"]["tokens_entrada"] + x["r"]["tokens_saida"] for x in res) // len(res),
                      border=True)
            st.metric("Tempo total", f"{sum(x['r']['segundos'] for x in res):.1f} s", border=True)
        if ultima["concordancia"] >= meta:
            st.success(f"Meta de {meta}% atingida: pronto para propor autonomia assistida ao comitê, começando "
                       "pela menor alçada.", icon=":material/verified:")
        else:
            st.warning(f"Abaixo da meta de {meta}%: continua em modo sombra. Veja os casos divergentes, escreva um "
                       "ajuste e rode de novo.", icon=":material/pending:")
        st.dataframe([{"#": i, "Cliente": x["cliente"], "Pedido": x["mensagem"], "Agente": x["r"]["proposta"],
                       "Analista": x["humano"], "Concorda": "✓" if x["ok"] else "✕"}
                      for i, x in enumerate(res, 1)], hide_index=True,
                     alt=f"Rodada {ultima['rodada']}: proposta do agente e decisão do analista por caso")

        st.markdown("**Raciocínio do agente em um caso**")
        i = st.selectbox("Caso", range(1, len(res) + 1), key="d06_detalhe", label_visibility="collapsed",
                         format_func=lambda n: f"{n}. {'✓' if res[n - 1]['ok'] else '✕'} {res[n - 1]['mensagem']}")
        x = res[i - 1]
        with st.container(border=True):
            st.caption(f"{CLIENTES[x['cliente']]['nome']} ({x['cliente']}) • agente: {x['r']['proposta']} • "
                       f"analista: {x['humano']}")
            web.resposta(x["r"], aberto=True)

with direita:
    st.subheader("Por dentro")
    web.codigo("O modo sombra é uma linha nos guardrails",
               "Com `modo_sombra=True`, toda **ação** (bloquear, estornar) vira uma proposta registrada e "
               "**não é executada**. Consultas continuam funcionando: o agente raciocina como em produção.",
               web.trecho(Guardrails.verificar_acao, "if not ferramenta.acao", "return Veredito(True)",
                          "if self.modo_sombra", "SOMBRA", "PROPOSTA"), aberto=True, icone=":material/visibility_off:")
    web.codigo("Propor e comparar com o analista",
               "Cada caso roda com o agente em modo sombra; os ajustes digitados entram como instruções extras. "
               "A proposta é *ESTORNO* se o agente tentou abrir um estorno.",
               web.fonte(propor), icone=":material/compare:")
