"""Início: o que é um agente, as peças e o acesso a cada demonstração."""

import streamlit as st

from agente import Agente
from utils.web import DEMOS, codigo, trecho

st.title("Agentes de IA: do assistente que responde ao colaborador digital que resolve")
st.caption("Caso usado em todas as demos: contestação de compra no cartão, com dados 100% fictícios. "
           "Escolha o modelo na barra lateral; ele vale para todas as páginas.")

esquerda, direita = st.columns([3, 2], gap="large")
with esquerda:
    st.subheader("Demonstrações")
    for i in range(0, len(DEMOS), 2):
        for coluna, demo in zip(st.columns(2), DEMOS[i:i + 2]):
            with coluna.container(border=True, height="stretch"):
                st.markdown(f"**{demo['icone']} {demo['titulo']}**")
                st.caption(demo["resumo"])
                if st.button("Abrir", key=f"abrir_{demo['url']}", icon=":material/arrow_forward:"):
                    st.switch_page(demo["arquivo"])

with direita:
    st.subheader("Anatomia de um agente")
    st.markdown("Um agente é **um modelo de linguagem + as peças que você decide encaixar**. "
                "Cada peça é um arquivo da pasta `agente/`:")
    st.markdown("""
| Peça | O que dá ao agente | Arquivo |
|---|---|---|
| :material/smart_toy: LLM | entende e decide o próximo passo | `utils/conexao_*.py` |
| :material/memory: Memória | lembra da conversa | `agente/memoria.py` |
| :material/build: Ferramentas | consulta sistemas e age | `agente/ferramentas.py` |
| :material/menu_book: Conhecimento | consulta normas e cita a fonte | `agente/conhecimento.py` |
| :material/shield: Guardrails | limites, aprovação humana, auditoria | `agente/guardrails.py` |
""")
    st.code('''from utils import criar_provedor
from agente import Agente, Memoria, BaseConhecimento, Guardrails, FERRAMENTAS_CARTAO

llm = criar_provedor("claude")                      # ou "gpt", "iara", "simulado"
agente = Agente(llm,
                memoria=Memoria(),
                ferramentas=FERRAMENTAS_CARTAO,
                conhecimento=BaseConhecimento(),
                guardrails=Guardrails(cliente_sessao="C-1001", alcada=2000))
agente.conversar("Não reconheço uma compra de R$ 1.249,90")''', language="python")
    codigo("Por dentro: o agente recebe as peças", "O construtor só guarda cada peça; quem dá vida a elas é o "
           "ciclo (demo 03). Repare: o conhecimento vira mais uma ferramenta, e as instruções são montadas "
           "conforme as peças presentes.",
           trecho(Agente.__init__, "self.memoria", "self.guardrails", "self.ferramentas", "if conhecimento", "buscar_conhecimento",
                  "self.instrucoes", "if instrucoes_automaticas"))
