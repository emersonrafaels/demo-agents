"""
DEMO 04 — Multiagentes: um orquestrador que usa outros agentes como ferramentas (interativa)

  Orquestrador ──► Agente de Fraude      (LLM + ferramentas de cliente, transação e risco)
              ├──► Agente de Políticas   (LLM + busca de conhecimento)
              └──► Agente de Atendimento (LLM + memória) ⇄ Agente Revisor (LLM, responde em JSON)

Você descreve o caso (ou escolhe um pronto) e o orquestrador DECIDE quais especialistas acionar.
O rascunho v1 da resposta ao cliente pode nascer de três jeitos (/rascunho):
  erro  dois erros inseridos de propósito (CPF exposto e estorno "definitivo") → o Revisor barra
  voce  VOCÊ escreve o v1: tente passar algo errado pelo Revisor
  ia    o Atendimento escreve sozinho desde o início

Executar:
  python 04_multiagentes.py --provedor claude
  python 04_multiagentes.py --provedor gpt --sem-erro       (começa no modo "ia")
  python 04_multiagentes.py --provedor claude --web         (abre no navegador)

O código da equipe está em agente/multiagentes.py.
"""

import re

from agente.dados import CLIENTES
from agente.multiagentes import MODOS_RASCUNHO as MODOS
from agente.multiagentes import Equipe
from utils import criar_provedor
from utils.console import C, FLAGS, digitar, opcao, pausa, secao, titulo
from utils.interativo import (Encerrar, abrir_web, ao_vivo, argumento, ler_cliente, mostrar_comandos,
                              mostrar_sugestoes, perguntar)
from utils.roteiro import CASOS_MULTIAGENTES as CASOS

if "--web" in FLAGS:
    abrir_web("multiagentes")
llm = criar_provedor(opcao("provedor"), opcao("modelo"))
CORES = {"Orquestrador": C.AZUL, "Fraude": C.VERMELHO, "Políticas": C.ROXO,
         "Atendimento": C.LARANJA, "Revisor": C.VERDE, "Você": C.AZUL}
SUGESTOES = [f"[{c}] {t}" for c, t in CASOS]
COMANDOS = {"/rascunho erro|voce|ia": "como nasce o rascunho v1",
            "/cliente C-100X": "troca o cliente do próximo caso",
            "/ajuda": "mostra casos prontos e comandos"}

estado = {"cliente": "C-1001", "modo": "ia" if "--sem-erro" in FLAGS else "erro"}


def msg(de, para, texto, tipo=""):
    marca = {"ok": f"{C.VERDE}✓{C.FIM} ", "erro": f"{C.VERMELHO}✕{C.FIM} "}.get(tipo, "")
    digitar(f"  {CORES[de]}{C.NEGRITO}{de:>12}{C.FIM} → {CORES.get(para, '')}{para:<12}{C.FIM} {marca}{texto}")
    pausa(0.3)


def rascunho_humano(cliente, protocolo):
    c = CLIENTES[cliente]
    print(f"\n  {C.CINZA}Sua vez: escreva a resposta ao cliente {c['nome']} (CPF {c['cpf']}, protocolo "
          f"{protocolo}). Tente passar algo errado pelo Revisor; ENTER vazio = a IA escreve.{C.FIM}")
    try:
        return input(f"  {C.AZUL}{C.NEGRITO}Rascunho v1 ›{C.FIM} ").strip()
    except EOFError:
        return ""


def resolver(caso: str) -> None:
    cliente = estado["cliente"]
    secao(f"Caso de {CLIENTES[cliente]['nome']} ({cliente}) • rascunho: {MODOS[estado['modo']]}")
    equipe = Equipe(llm, cliente, modo_rascunho=estado["modo"], rascunho_humano=rascunho_humano, ao_falar=msg)
    final = ao_vivo(equipe.resolver, caso)
    if not final:
        return
    secao("Resultado consolidado")
    print(f"  {C.VERDE}Resposta ao cliente:{C.FIM} {final['resposta']}")
    print(f"  {C.CINZA}Especialistas acionados pelo orquestrador: {' → '.join(final['ferramentas'])} • "
          f"{final['tokens_entrada'] + final['tokens_saida']} tokens do orquestrador • {final['segundos']} s{C.FIM}")


# ------------------------------------------------------------------ execução
titulo(f"DEMO 04 • Multiagentes • {llm.nome} ({llm.modelo})")
print(f"\n{C.CINZA}Descreva um caso (ou escolha um pronto). O orquestrador decide quem acionar; o Revisor só libera "
      f"a resposta dentro da política. Rascunho v1 agora: {MODOS[estado['modo']]}.{C.FIM}")
mostrar_sugestoes(SUGESTOES, "Casos prontos (digite o número)")
mostrar_comandos(COMANDOS)

try:
    while True:
        texto = perguntar(f"Caso • {estado['cliente']}", SUGESTOES)
        cmd = texto.split()[0].lower()
        if cmd == "/rascunho" and argumento(texto).lower().replace("ê", "e") in MODOS:
            estado["modo"] = argumento(texto).lower().replace("ê", "e")
            print(f"  {C.CINZA}Rascunho v1: {MODOS[estado['modo']]}.{C.FIM}")
        elif cmd == "/cliente" and ler_cliente(argumento(texto)) in CLIENTES:
            estado["cliente"] = ler_cliente(argumento(texto))
            print(f"  {C.CINZA}Próximo caso na sessão de {CLIENTES[estado['cliente']]['nome']}.{C.FIM}")
        elif texto.startswith("/"):
            mostrar_sugestoes(SUGESTOES, "Casos prontos (digite o número)")
            mostrar_comandos(COMANDOS)
        else:
            if (m := re.match(r"\[(C-\d{4})\]\s*(.*)", texto)) and m.group(1) in CLIENTES:
                estado["cliente"], texto = m.group(1), m.group(2)
            resolver(texto)
except Encerrar:
    pass

print(f"\n{C.AZUL}{C.NEGRITO}Mensagem-chave:{C.FIM} especialistas com instruções e acessos próprios, que se "
      f"verificam mutuamente; o erro do rascunho nunca chega ao cliente.\n")
