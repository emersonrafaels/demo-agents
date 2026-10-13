"""
DEMO 03 — O ciclo do agente, passo a passo (interativa)

    PERCEBER → PLANEJAR → AGIR → OBSERVAR → (repete) → RESPONDER

Você manda a mensagem e acompanha o agente decidindo cada passo; ENTER avança (o modo passo a passo
começa ligado e /passo alterna). Com --provedor ambos, o MESMO agente (mesmas instruções, ferramentas e
guardrails) responde no Claude e no GPT, e cada mensagem termina com a comparação: voltas, tokens e tempo.

Executar:
  python 03_ciclo_do_agente.py --provedor claude
  python 03_ciclo_do_agente.py --provedor ambos
  python 03_ciclo_do_agente.py --provedor claude --web    (abre no navegador)

Na demo: digite qualquer mensagem, ou um número para usar uma mensagem pronta.
  /passo            liga/desliga o ENTER a cada etapa
  /cliente C-1002   troca o cliente logado (nova conversa)
  /trilha           mostra a trilha de auditoria desta sessão
  /nova             recomeça a conversa
"""

import json
import os

from agente import FERRAMENTAS_CARTAO, Agente, Auditoria, BaseConhecimento, Guardrails, Memoria
from agente.dados import CLIENTES
from utils import criar_provedor
from utils.console import C, FLAGS, alternar_passo, opcao, secao, titulo
from utils.interativo import (Encerrar, abrir_web, ao_vivo, argumento, ler_cliente, mostrar_comandos,
                              mostrar_sugestoes, perguntar)
from utils.roteiro import CICLO

ARQUIVO = "auditoria_demo03.jsonl"
SUGESTOES = CICLO
COMANDOS = {"/passo": "liga/desliga o ENTER a cada etapa", "/cliente C-100X": "troca o cliente logado",
            "/trilha": "mostra a trilha de auditoria", "/nova": "recomeça a conversa",
            "/ajuda": "mostra mensagens prontas e comandos"}

if "--web" in FLAGS:
    abrir_web("ciclo")
escolha = (opcao("provedor") or "").lower()
nomes = ["claude", "gpt"] if escolha == "ambos" else [escolha or None]
llms = [criar_provedor(n, opcao("modelo") if len(nomes) == 1 else None) for n in nomes]
if os.path.exists(ARQUIVO):
    os.remove(ARQUIVO)
auditoria = Auditoria(ARQUIVO)


def montar(cliente):
    return [Agente(llm, memoria=Memoria(), ferramentas=FERRAMENTAS_CARTAO, conhecimento=BaseConhecimento(),
                   guardrails=Guardrails(cliente_sessao=cliente, auditoria=auditoria), nome=f"ciclo-{llm.nome}")
            for llm in llms]


def resumo(resultados):
    if len(resultados) == 1:
        r = resultados[0]
        print(f"\n  {C.CINZA}↻ {r['voltas']} voltas no ciclo • {len(r['ferramentas'])} ferramentas • "
              f"{r['tokens_entrada'] + r['tokens_saida']} tokens • {r['segundos']} s{C.FIM}")
        if r["ferramentas"]:
            print(f"  {C.CINZA}  caminho escolhido pelo modelo: {' → '.join(r['ferramentas'])}{C.FIM}")
        return
    secao("Comparação")
    print(f"  {'':<22}" + "".join(f"{r['provedor']:<18}" for r in resultados))
    for rotulo, chave in [("Voltas no ciclo", "voltas"), ("Tempo (s)", "segundos"),
                          ("Tokens de entrada", "tokens_entrada"), ("Tokens de saída", "tokens_saida")]:
        print(f"  {rotulo:<22}" + "".join(f"{str(r[chave]):<18}" for r in resultados))
    print(f"  {'Ferramentas usadas':<22}" + "".join(f"{len(r['ferramentas']):<18}" for r in resultados))
    for r in resultados:
        print(f"  {C.CINZA}{r['provedor']}: {' → '.join(r['ferramentas']) or '(respondeu direto)'}{C.FIM}")


def trilha(n=10):
    if not os.path.exists(ARQUIVO):
        print(f"  {C.CINZA}Trilha vazia.{C.FIM}")
        return
    with open(ARQUIVO, encoding="utf-8") as f:
        linhas = f.readlines()
    secao(f"Trilha de auditoria ({ARQUIVO}) — últimos {min(n, len(linhas))} de {len(linhas)} eventos")
    for linha in linhas[-n:]:
        e = json.loads(linha)
        print(f"  {C.CINZA}{e['quando'][11:]}{C.FIM} {e['agente']:<14} {e['tipo']:<12} {e['detalhe'][:80]}")


titulo("DEMO 03 • O ciclo do agente • " + " × ".join(f"{l.nome} ({l.modelo})" for l in llms))
print(f"""
{C.CINZA}Legenda:{C.FIM}
  {C.AZUL}{C.NEGRITO}PERCEBER{C.FIM}   o que chegou para o agente
  {C.CINZA}{C.NEGRITO}PLANEJAR{C.FIM}   o modelo explica o próximo passo e por quê
  {C.LARANJA}{C.NEGRITO}AGIR{C.FIM}       a ferramenta (sistema) que o modelo pediu para chamar
  {C.VERDE}{C.NEGRITO}OBSERVAR{C.FIM}   o que o sistema devolveu; volta para o modelo como memória
  {C.ROXO}{C.NEGRITO}GUARDRAIL{C.FIM}  limite verificado no código, fora do modelo""")
alternar_passo(True)
cliente = "C-1001"
agentes = montar(cliente)
print(f"\n{C.CINZA}Cliente logado: {CLIENTES[cliente]['nome']} ({cliente}). Modo passo a passo ligado: "
      f"ENTER avança cada etapa.{C.FIM}")
mostrar_sugestoes(SUGESTOES)
mostrar_comandos(COMANDOS)

try:
    while True:
        texto = perguntar(f"Cliente {cliente}", SUGESTOES)
        cmd = texto.split()[0].lower()
        if cmd == "/passo":
            print(f"  {C.CINZA}Passo a passo {'ligado' if alternar_passo() else 'desligado'}.{C.FIM}")
        elif cmd == "/cliente" and ler_cliente(argumento(texto)) in CLIENTES:
            cliente = ler_cliente(argumento(texto))
            agentes = montar(cliente)
            print(f"  {C.CINZA}Sessão de {CLIENTES[cliente]['nome']} ({cliente}); conversa nova.{C.FIM}")
        elif cmd == "/trilha":
            trilha()
        elif cmd == "/nova":
            agentes = montar(cliente)
            print(f"  {C.CINZA}Conversa reiniciada.{C.FIM}")
        elif texto.startswith("/"):
            mostrar_sugestoes(SUGESTOES)
            mostrar_comandos(COMANDOS)
        else:
            resultados = []
            for agente in agentes:
                if len(agentes) > 1:
                    secao(f"Execução • {agente.provedor.nome} ({agente.provedor.modelo})")
                r = ao_vivo(agente.conversar, texto, contexto=f"[cliente_id: {cliente}] ")
                if r:
                    resultados.append(r)
            if resultados:
                resumo(resultados)
except Encerrar:
    pass

print(f"\n{C.AZUL}{C.NEGRITO}Mensagem-chave:{C.FIM} ninguém programou a ordem dos passos: o modelo decide o "
      f"próximo passo com base no que já descobriu. Trilha completa em {ARQUIVO}.\n")
if any(l.nome == "Simulado" for l in llms):
    print(f"{C.CINZA}(Modo simulado: as decisões vieram de regras locais, só para ensaio. "
          f"Rode com --provedor claude ou gpt para ver o modelo decidindo.){C.FIM}\n")
