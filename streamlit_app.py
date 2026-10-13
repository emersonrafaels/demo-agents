"""
App web das demos: todas as demonstrações num só lugar, no navegador.

Executar (qualquer um):
  python streamlit_app.py --provedor claude
  streamlit run streamlit_app.py -- --provedor claude
  python 02_evolucao_do_agente.py --provedor claude --web      (abre direto na página da demo)

Cada página fica em app_pages/; as peças comuns da interface, em utils/web.py.
"""

import os

import streamlit as st
from streamlit import runtime

if not runtime.exists():                 # rodado com "python streamlit_app.py": sobe o servidor e abre o navegador
    from utils.interativo import abrir_web
    abrir_web()

from utils.console import opcao
from utils.web import DEMOS, PROVEDORES

st.set_page_config(page_title="Agentes de IA • demos", page_icon=":material/smart_toy:", layout="wide")

ss = st.session_state
if "provedor" not in ss:
    padrao = (opcao("provedor") or os.getenv("PROVEDOR") or "").lower()
    ss.provedor = padrao if padrao in PROVEDORES else ("claude" if os.getenv("ANTHROPIC_API_KEY") else
                                                        "gpt" if os.getenv("OPENAI_API_KEY") else "simulado")
    ss.modelo = opcao("modelo") or ""

paginas = {
    "": [st.Page("app_pages/inicio.py", title="Início", icon=":material/home:", default=True)],
    "Demonstrações": [st.Page(d["arquivo"], title=d["titulo"], icon=d["icone"], url_path=d["url"]) for d in DEMOS],
}
pagina = st.navigation(paginas)

with st.sidebar:
    st.selectbox("Modelo de linguagem (LLM)", PROVEDORES, key="provedor",
                 help="O mesmo modelo é usado em todas as demos. Simulado = ensaio offline, sem chave e sem custo.")
    st.text_input("Nome do modelo (opcional)", key="modelo", placeholder="padrão do .env",
                  help="Sobrescreve MODELO_CLAUDE / MODELO_GPT só nesta sessão.")
    st.caption("Dados 100% fictícios • ambiente de demonstração")

pagina.run()
