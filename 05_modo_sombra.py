"""
DEMO 05 — Modo sombra: medir o agente contra decisões humanas ANTES de dar autonomia

O agente analisa casos já decididos por analistas, mas suas AÇÕES não são executadas: ficam
registradas como propostas. Ao final, comparamos proposta × decisão humana e calculamos a
concordância — o primeiro número que um comitê pede antes de liberar autonomia.

Executar:
  python 05_modo_sombra.py --provedor claude
  python 05_modo_sombra.py --provedor gpt
"""

from agente import INSTRUCOES_CONTESTACAO, Agente
from console import C, opcao, secao, titulo
from ferramentas import TODAS_CONTESTACAO
from guardrails import Auditoria
from llm import criar_provedor

# Casos históricos (fictícios) com a decisão final tomada pelo analista
HISTORICO = [
    ("C-1001", "Não reconheço uma compra de R$ 1.249,90 no meu cartão.", "ESTORNO"),
    ("C-1003", "Não reconheço uma compra de R$ 89,90 numa farmácia.", "SEM ESTORNO"),
    ("C-1004", "Apareceu uma compra de R$ 459,00 que eu não fiz.", "ESTORNO"),
    ("C-1002", "Não fiz essa compra de R$ 8.900,00 numa agência de viagens.", "ESTORNO"),
    ("C-1005", "Não reconheço uma compra de R$ 640,00 no cartão.", "SEM ESTORNO"),
]

provedor = criar_provedor(opcao("provedor"), opcao("modelo"))
titulo(f"DEMO 05 • Modo sombra • {provedor.nome} ({provedor.modelo})")
print(f"\n{C.CINZA}O agente propõe; nada é executado. Comparamos com a decisão real do analista.{C.FIM}")

secao("Agente × analista, caso a caso")
print(f"  {'Cliente':<9}{'Pedido':<58}{'Agente':<14}{'Analista':<14}")
acertos, tokens, segundos = 0, 0, 0.0
for cliente, mensagem, decisao_humana in HISTORICO:
    agente = Agente(provedor, INSTRUCOES_CONTESTACAO, TODAS_CONTESTACAO,
                    nome=f"sombra-{cliente}", modo_sombra=True, verboso=False,
                    auditoria=Auditoria("auditoria_demo05.jsonl"))
    r = agente.executar(mensagem, contexto=f"[cliente_id: {cliente}] ")
    proposta = "ESTORNO" if any(a["ferramenta"] == "abrir_estorno_provisorio" for a in r["acoes"]) else "SEM ESTORNO"
    ok = proposta == decisao_humana
    acertos += ok
    tokens += r["tokens_entrada"] + r["tokens_saida"]
    segundos += r["segundos"]
    marca = f"{C.VERDE}✓{C.FIM}" if ok else f"{C.VERMELHO}✕{C.FIM}"
    print(f"  {cliente:<9}{mensagem[:56]:<58}{proposta:<14}{decisao_humana:<14}{marca}")

secao("Resultado")
pct = 100 * acertos / len(HISTORICO)
print(f"  Concordância com os analistas ... {C.NEGRITO}{pct:.0f}%{C.FIM} ({acertos} de {len(HISTORICO)})")
print(f"  Tokens consumidos ............... {tokens}  (≈ {tokens // len(HISTORICO)} por caso)")
print(f"  Tempo total ..................... {segundos:.1f} s")
print(f"  Propostas registradas em ........ auditoria_demo05.jsonl")
print(f"\n{C.AZUL}{C.NEGRITO}Mensagem-chave:{C.FIM} primeiro medimos, depois liberamos autonomia; "
      f"divergências viram ajustes nas instruções e nas ferramentas.\n")
