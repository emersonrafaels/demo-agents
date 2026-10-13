"""
DEMO 01 — Chatbot × Agente

A MESMA mensagem vai para o MESMO modelo duas vezes:
  1) CHATBOT: só o LLM, sem ferramentas → o modelo só consegue orientar;
  2) AGENTE: LLM + memória + ferramentas + conhecimento + guardrails → consulta sistemas e resolve.

Executar:
  python 01_chatbot_vs_agente.py --provedor claude      (ou gpt, iara, simulado)
"""

from agente import FERRAMENTAS_CARTAO, Agente, BaseConhecimento, Guardrails, Memoria
from utils import criar_provedor
from utils.console import C, digitar, opcao, pausa, secao, titulo

MENSAGEM = "Não reconheço uma compra de R$ 1.249,90 no meu cartão. O que eu faço?"
llm = criar_provedor(opcao("provedor"), opcao("modelo"))
titulo(f"DEMO 01 • Chatbot × Agente • {llm.nome} ({llm.modelo})")
print(f"\n{C.NEGRITO}Cliente:{C.FIM} {MENSAGEM}")
pausa(1)

# ---------------------------------------------------------------- 1) CHATBOT: só o LLM
secao("1) CHATBOT — só o modelo, sem ferramentas")
chatbot = Agente(llm, "Você é o chatbot de FAQ de um banco. Responda em até 3 frases, em português, apenas "
                      "orientando o cliente. Você não tem acesso a nenhum sistema.", verboso=False)
r1 = chatbot.conversar(MENSAGEM)
digitar(f"  🤖 {r1['resposta']}", C.CINZA)
print(f"\n  {C.CINZA}→ {r1['voltas']} chamada • 0 sistemas consultados • "
      f"{r1['tokens_entrada'] + r1['tokens_saida']} tokens{C.FIM}")
pausa(1.5)

# ---------------------------------------------------------------- 2) AGENTE: o mesmo modelo + as peças
secao("2) AGENTE — o mesmo modelo, com memória, ferramentas, conhecimento e guardrails")
agente = Agente(llm, memoria=Memoria(), ferramentas=FERRAMENTAS_CARTAO, conhecimento=BaseConhecimento(),
                guardrails=Guardrails(cliente_sessao="C-1001"), nome="contestacoes")
r2 = agente.conversar(MENSAGEM, contexto="[cliente_id: C-1001] ")

# ---------------------------------------------------------------- comparação
secao("Comparação")
n_acoes = sum(a["status"] in ("executada", "aprovada") for a in r2["acoes"])
print(f"  {'':<26}{'CHATBOT':<20}{'AGENTE'}")
print(f"  {'Chamadas ao modelo':<26}{r1['voltas']:<20}{r2['voltas']}")
print(f"  {'Chamadas a sistemas':<26}{'0':<20}{len(r2['ferramentas'])}")
print(f"  {'Ações executadas':<26}{'0':<20}{n_acoes}")
print(f"  {'Tokens':<26}{r1['tokens_entrada'] + r1['tokens_saida']:<20}{r2['tokens_entrada'] + r2['tokens_saida']}")
print(f"  {'Problema resolvido?':<26}{'Não (orienta)':<20}{C.VERDE}{'Sim' if n_acoes else 'Encaminhado'}{C.FIM}")
print(f"\n{C.AZUL}{C.NEGRITO}Mensagem-chave:{C.FIM} o modelo é o mesmo; o que muda são as peças ao redor dele. "
      f"O chatbot RESPONDE, o agente RESOLVE.\n")
