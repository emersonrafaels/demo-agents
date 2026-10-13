"""
DEMO 01 — Chatbot × Agente (interativa)

Você digita como se fosse o cliente. Cada mensagem vai para o MESMO modelo duas vezes:
  1) CHATBOT: LLM + memória da conversa, sem acesso a sistemas → só consegue orientar;
  2) AGENTE:  LLM + memória + ferramentas + conhecimento + guardrails → consulta sistemas e resolve.
Depois de cada mensagem aparece a comparação; ao sair, o placar da conversa inteira.

Executar:
  python 01_chatbot_vs_agente.py --provedor claude      (ou gpt, iara, simulado)
  python 01_chatbot_vs_agente.py --provedor claude --web  (abre no navegador)

Na demo: digite qualquer mensagem, ou um número para usar uma mensagem pronta.
  /cliente C-1002   troca o cliente logado (nova conversa)
  /nova             recomeça a conversa
"""

from agente import FERRAMENTAS_CARTAO, Agente, BaseConhecimento, Guardrails, Memoria
from agente.dados import CLIENTES
from utils import criar_provedor
from utils.console import C, FLAGS, digitar, opcao, secao, titulo
from utils.interativo import (Encerrar, abrir_web, ao_vivo, argumento, ler_cliente, mostrar_comandos,
                              mostrar_sugestoes, perguntar)
from utils.roteiro import CHATBOT_VS_AGENTE

SUGESTOES = CHATBOT_VS_AGENTE
COMANDOS = {"/cliente C-100X": "troca o cliente logado (nova conversa)",
            "/nova": "recomeça a conversa", "/ajuda": "mostra mensagens prontas e comandos"}

if "--web" in FLAGS:
    abrir_web("chatbot-vs-agente")
llm = criar_provedor(opcao("provedor"), opcao("modelo"))
INSTR_CHATBOT = ("Você é o chatbot de FAQ de um banco. Responda em até 3 frases, em português, apenas "
                 "orientando o cliente. Você não tem acesso a nenhum sistema.")


def montar(cliente):
    chatbot = Agente(llm, INSTR_CHATBOT, memoria=Memoria(), verboso=False, nome="chatbot")
    agente = Agente(llm, memoria=Memoria(), ferramentas=FERRAMENTAS_CARTAO, conhecimento=BaseConhecimento(),
                    guardrails=Guardrails(cliente_sessao=cliente), nome="contestacoes")
    return chatbot, agente


def acoes(r):
    return sum(a["status"] in ("executada", "aprovada") for a in r["acoes"])


def comparar(linhas):
    print(f"\n  {'':<24}{C.CINZA}{'CHATBOT':<16}{C.FIM}{C.VERDE}{'AGENTE'}{C.FIM}")
    for rotulo, a, b in linhas:
        print(f"  {rotulo:<24}{str(a):<16}{b}")


def apresentar(cliente):
    c = CLIENTES[cliente]
    print(f"\n{C.CINZA}Cliente logado: {C.FIM}{C.NEGRITO}{c['nome']} ({cliente}){C.FIM}{C.CINZA} • cartão final "
          f"{c['cartao']}. Você fala como cliente; a mesma mensagem vai ao chatbot e ao agente.{C.FIM}")


titulo(f"DEMO 01 • Chatbot × Agente • {llm.nome} ({llm.modelo})")
cliente = "C-1001"
chatbot, agente = montar(cliente)
apresentar(cliente)
mostrar_sugestoes(SUGESTOES)
mostrar_comandos(COMANDOS)
total = {"chatbot": [0, 0, 0, 0], "agente": [0, 0, 0, 0]}    # mensagens, sistemas, ações, tokens

try:
    while True:
        texto = perguntar(f"Cliente {cliente}", SUGESTOES)
        if texto.startswith("/"):
            cmd = texto.split()[0].lower()
            if cmd == "/cliente" and ler_cliente(argumento(texto)) in CLIENTES:
                cliente = ler_cliente(argumento(texto))
                chatbot, agente = montar(cliente)
                apresentar(cliente)
            elif cmd == "/nova":
                chatbot, agente = montar(cliente)
                print(f"  {C.CINZA}Conversa reiniciada.{C.FIM}")
            elif cmd == "/cliente":
                print(f"  {C.CINZA}Clientes disponíveis: {', '.join(CLIENTES)}{C.FIM}")
            else:
                mostrar_sugestoes(SUGESTOES)
                mostrar_comandos(COMANDOS)
            continue

        secao("1) CHATBOT — só o modelo, sem acesso a sistemas")
        r1 = ao_vivo(chatbot.conversar, texto)
        if r1:
            digitar(f"  🤖 {r1['resposta']}", C.CINZA)

        secao("2) AGENTE — o mesmo modelo + ferramentas, conhecimento e guardrails")
        r2 = ao_vivo(agente.conversar, texto, contexto=f"[cliente_id: {cliente}] ")
        if not (r1 and r2):
            continue

        comparar([
            ("Chamadas ao modelo", r1["voltas"], r2["voltas"]),
            ("Consultas a sistemas", 0, len(r2["ferramentas"])),
            ("Ações executadas", 0, acoes(r2)),
            ("Tokens", r1["tokens_entrada"] + r1["tokens_saida"], r2["tokens_entrada"] + r2["tokens_saida"]),
        ])
        for chave, r, sistemas, n_acoes in [("chatbot", r1, 0, 0), ("agente", r2, len(r2["ferramentas"]), acoes(r2))]:
            t = total[chave]
            t[0] += 1
            t[1] += sistemas
            t[2] += n_acoes
            t[3] += r["tokens_entrada"] + r["tokens_saida"]
except Encerrar:
    pass

if total["agente"][0]:
    secao(f"Placar da conversa ({total['agente'][0]} mensagens)")
    a, b = total["chatbot"], total["agente"]
    comparar([("Consultas a sistemas", a[1], b[1]), ("Ações executadas", a[2], b[2]), ("Tokens", a[3], b[3]),
              ("Papel", "orienta", f"{C.VERDE}resolve{C.FIM}" if b[2] else f"{C.VERDE}consulta e encaminha{C.FIM}")])
print(f"\n{C.AZUL}{C.NEGRITO}Mensagem-chave:{C.FIM} o modelo é o mesmo; o que muda são as peças ao redor dele. "
      f"O chatbot RESPONDE, o agente RESOLVE.\n")
