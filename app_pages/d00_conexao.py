"""DEMO 00 (web) — Teste de conexão: uma chamada mínima a cada modelo, com tempo e tokens."""

import time

import streamlit as st

from utils import criar_provedor
from utils.base import Provedor
from utils.conexao_anthropic import ProvedorClaude
from utils.conexao_openai import ProvedorGPT
from utils.web import bloco_arquivo, codigo, fonte, trecho

st.title("Teste de conexão")
st.caption("Rode antes da apresentação: confere cada modelo com uma chamada mínima.")

esquerda, direita = st.columns([3, 2], gap="large")
with esquerda:
    escolhidos = st.pills("Modelos", ["claude", "gpt", "iara", "simulado"], selection_mode="multi",
                          default=["claude", "gpt", "iara"])
    if st.button("Testar conexões", type="primary", icon=":material/play_arrow:"):
        linhas = []
        for nome in escolhidos:
            with st.spinner(f"Chamando {nome}…"):
                try:
                    p = criar_provedor(nome)
                except SystemExit as e:
                    linhas.append({"Modelo": nome, "Status": "não configurado", "Detalhe": str(e)})
                    continue
                try:
                    t = time.time()
                    r = p.conversar("Responda apenas: OK", [{"tipo": "usuario", "texto": "Teste de conexão."}])
                    linhas.append({"Modelo": f"{p.nome} ({p.modelo})", "Status": "ok",
                                   "Tempo (s)": round(time.time() - t, 1),
                                   "Tokens": r.tokens_entrada + r.tokens_saida, "Detalhe": r.texto[:40]})
                except Exception as e:
                    linhas.append({"Modelo": p.nome, "Status": "erro", "Detalhe": f"{type(e).__name__}: {str(e)[:160]}"})
        st.dataframe(linhas, hide_index=True, alt="Resultado do teste de conexão com cada modelo")
        if any(l["Status"] == "ok" for l in linhas):
            st.success("Pronto para apresentar com os modelos marcados como ok.", icon=":material/check_circle:")
    st.info("Sem chave ou sem internet? Todas as demos rodam com o modelo **simulado** (ensaio offline).",
            icon=":material/info:")

with direita:
    st.subheader("Por dentro")
    codigo("Um contrato, vários fornecedores",
           "Claude, GPT e Iara têm APIs diferentes. Cada conexão traduz para **o mesmo contrato**: recebe "
           "instruções, histórico e ferramentas e devolve texto e pedidos de ferramenta. O resto do código não "
           "sabe qual fornecedor está por trás — trocar de modelo é trocar uma palavra.",
           trecho(Provedor, "nome: str", "modelo: str", "def conversar", "max_tokens", '"""Envia'), aberto=True)
    codigo("Como a conversa chega ao Claude",
           "As instruções vão à parte (`system`) e as ferramentas viram `tools`. O modelo devolve texto e/ou "
           "pedidos para usar ferramentas (`tool_use`).",
           fonte(ProvedorClaude.conversar))
    codigo("Como a mesma conversa chega ao GPT",
           "Mesma ideia, outro formato: as instruções são a primeira mensagem e as ferramentas viram `functions`.",
           fonte(ProvedorGPT.conversar))
    codigo("Escolhendo o fornecedor", "Uma tabela liga o nome ao arquivo de conexão e à chave exigida no `.env`.",
           bloco_arquivo("utils/__init__.py", "PROVEDORES = {", "}"), fonte(criar_provedor))
