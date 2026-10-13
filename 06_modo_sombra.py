"""
DEMO 06 — Modo sombra: medir o agente contra decisões humanas ANTES de dar autonomia

O agente analisa casos já decididos por analistas, mas suas AÇÕES não são executadas: ficam
registradas como propostas (Guardrails(modo_sombra=True)). Ao final, comparamos proposta × decisão
humana e calculamos a concordância — o primeiro número que um comitê pede antes de liberar autonomia.

Executar:
  python 06_modo_sombra.py --provedor claude
  python 06_modo_sombra.py --provedor gpt
"""

from agente import FERRAMENTAS_CARTAO, Agente, Auditoria, BaseConhecimento, Guardrails
from utils import criar_provedor
from utils.console import C, opcao, secao, titulo

# Casos históricos (fictícios) com a decisão final tomada pelo analista
HISTORICO = [
    ("C-1001", "Não reconheço uma compra de R$ 1.249,90 no meu cartão.", "ESTORNO"),
    ("C-1003", "Não reconheço uma compra de R$ 89,90 numa farmácia.", "SEM ESTORNO"),
    ("C-1004", "Apareceu uma compra de R$ 459,00 que eu não fiz.", "ESTORNO"),
    ("C-1002", "Não fiz essa compra de R$ 8.900,00 numa agência de viagens.", "ESTORNO"),
    ("C-1005", "Não reconheço uma compra de R$ 640,00 no cartão.", "SEM ESTORNO"),
]

llm = criar_provedor(opcao("provedor"), opcao("modelo"))
conhecimento = BaseConhecimento()
titulo(f"DEMO 06 • Modo sombra • {llm.nome} ({llm.modelo})")
print(f"\n{C.CINZA}O agente propõe; nada é executado. Comparamos com a decisão real do analista.{C.FIM}")

secao("Agente × analista, caso a caso")
print(f"  {'Cliente':<9}{'Pedido':<58}{'Agente':<14}{'Analista':<14}")
acertos, tokens, segundos = 0, 0, 0.0
for cliente, mensagem, decisao_humana in HISTORICO:
    agente = Agente(llm, ferramentas=FERRAMENTAS_CARTAO, conhecimento=conhecimento, nome=f"sombra-{cliente}",
                    guardrails=Guardrails(cliente_sessao=cliente, modo_sombra=True,
                                          auditoria=Auditoria("auditoria_demo06.jsonl")),
                    verboso=False)
    r = agente.conversar(mensagem, contexto=f"[cliente_id: {cliente}] ")
    proposta = ("ESTORNO" if any(a["ferramenta"] == "abrir_estorno_provisorio" for a in r["acoes"])
                else "SEM ESTORNO")
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
print(f"  Propostas registradas em ........ auditoria_demo06.jsonl")
print(f"\n{C.AZUL}{C.NEGRITO}Mensagem-chave:{C.FIM} primeiro medimos, depois liberamos autonomia; "
      f"divergências viram ajustes nas instruções, nas ferramentas e na base de conhecimento.\n")
