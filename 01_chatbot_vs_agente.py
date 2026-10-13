"""
DEMO 01 — Chatbot × Agente (chamadas reais ao Claude ou ao GPT)

A MESMA mensagem do cliente vai para o MESMO modelo duas vezes:
  1) como CHATBOT: uma chamada, sem ferramentas → o modelo só consegue orientar;
  2) como AGENTE: com ferramentas e o ciclo do agente → o modelo consulta sistemas e resolve.

Executar:
  python 01_chatbot_vs_agente.py --provedor claude
  python 01_chatbot_vs_agente.py --provedor gpt
  python 01_chatbot_vs_agente.py --provedor simulado     (ensaio offline, sem chave)
"""

from agente import INSTRUCOES_CONTESTACAO, Agente
from console import C, digitar, opcao, pausa, secao, titulo
from ferramentas import TODAS_CONTESTACAO
from llm import criar_provedor

MENSAGEM = "Não reconheço uma compra de R$ 1.249,90 no meu cartão. O que eu faço?"

provedor = criar_provedor(opcao("provedor"), opcao("modelo"))
titulo(f"DEMO 01 • Chatbot × Agente • {provedor.nome} ({provedor.modelo})")
print(f"\n{C.NEGRITO}Cliente:{C.FIM} {MENSAGEM}")
pausa(1)

# ---------------------------------------------------------------- 1) CHATBOT: uma chamada, sem ferramentas
secao("1) CHATBOT — uma chamada ao modelo, sem ferramentas")
INSTRUCOES_CHATBOT = ("Você é o chatbot de FAQ de um banco. Responda em até 3 frases, em português, apenas "
                      "orientando o cliente. Você não tem acesso a nenhum sistema e não pode executar ações.")
r = provedor.conversar(INSTRUCOES_CHATBOT, [{"tipo": "usuario", "texto": MENSAGEM}])
digitar(f"  🤖 {r.texto}", C.CINZA)
print(f"\n  {C.CINZA}→ 1 chamada • 0 sistemas consultados • {r.tokens_entrada + r.tokens_saida} tokens{C.FIM}")
pausa(1.5)

# ---------------------------------------------------------------- 2) AGENTE: mesmo modelo + ferramentas + ciclo
secao("2) AGENTE — o mesmo modelo, agora com ferramentas")
agente = Agente(provedor, INSTRUCOES_CONTESTACAO, TODAS_CONTESTACAO, nome="contestacoes")
res = agente.executar(MENSAGEM, contexto="[cliente_id: C-1001] ")

# ---------------------------------------------------------------- comparação
secao("Comparação")
n_acoes = sum(f in ("bloquear_cartao", "abrir_estorno_provisorio") for f in res["ferramentas"])
print(f"  {'':<26}{'CHATBOT':<20}{'AGENTE'}")
print(f"  {'Chamadas ao modelo':<26}{'1':<20}{res['voltas']}")
print(f"  {'Chamadas a sistemas':<26}{'0':<20}{len(res['ferramentas'])}")
print(f"  {'Ações executadas':<26}{'0':<20}{n_acoes}")
print(f"  {'Tokens':<26}{r.tokens_entrada + r.tokens_saida:<20}{res['tokens_entrada'] + res['tokens_saida']}")
print(f"  {'Problema resolvido?':<26}{'Não (orienta)':<20}{C.VERDE}{'Sim' if n_acoes else 'Encaminhado'}{C.FIM}")
print(f"\n{C.AZUL}{C.NEGRITO}Mensagem-chave:{C.FIM} o modelo é o mesmo; o que muda são as ferramentas e o ciclo. "
      f"O chatbot RESPONDE, o agente RESOLVE.\n")
