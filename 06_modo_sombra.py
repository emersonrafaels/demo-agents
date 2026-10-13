"""
DEMO 06 — Modo sombra: medir o agente contra decisões humanas ANTES de dar autonomia (interativa)

O agente analisa casos já decididos por analistas, mas suas AÇÕES não são executadas: ficam
registradas como propostas (Guardrails(modo_sombra=True)). Comparamos proposta × decisão humana e
calculamos a concordância — o primeiro número que um comitê pede antes de liberar autonomia.

Na demo você conduz o ciclo de melhoria:
  ENTER / /rodar     roda todos os casos              N           mostra o raciocínio do caso N
  /novo              cadastra um caso histórico       /meta 90    define a meta de concordância
  /ajuste TEXTO      acrescenta uma instrução ao agente e permite rodar de novo para comparar

Executar:
  python 06_modo_sombra.py --provedor claude
  python 06_modo_sombra.py --provedor gpt
  python 06_modo_sombra.py --provedor claude --web   (abre no navegador)
"""

import re

from agente import BaseConhecimento
from agente.dados import CLIENTES
from agente.modo_sombra import propor
from utils import criar_provedor
from utils.console import C, FLAGS, opcao, secao, titulo
from utils.interativo import (Encerrar, abrir_web, argumento, ao_vivo, ler_cliente, mostrar_comandos, perguntar)
from utils.roteiro import AJUSTE_SUGERIDO, HISTORICO_SOMBRA

HISTORICO = [dict(c) for c in HISTORICO_SOMBRA]
COMANDOS = {"ENTER ou /rodar": "roda todos os casos em modo sombra",
            "N (número)": "mostra o raciocínio do agente no caso N",
            "/novo": "cadastra um caso histórico (cliente, mensagem, decisão do analista)",
            "/ajuste TEXTO": "acrescenta uma instrução ao agente (/ajuste sozinho sugere uma)",
            "/meta N": "meta de concordância para liberar autonomia (padrão 90%)",
            "/casos": "lista os casos e os ajustes feitos",
            "/ajuda": "mostra os comandos"}

if "--web" in FLAGS:
    abrir_web("modo-sombra")
llm = criar_provedor(opcao("provedor"), opcao("modelo"))
conhecimento = BaseConhecimento()
estado = {"ajustes": [], "meta": 90.0, "rodada": 0, "historico_rodadas": []}


def rodar_caso(caso) -> dict | None:
    return ao_vivo(propor, llm, caso, conhecimento, estado["ajustes"])


def rodar_todos() -> None:
    estado["rodada"] += 1
    rotulo = f"Rodada {estado['rodada']}" + (f" • {len(estado['ajustes'])} ajuste(s)" if estado["ajustes"] else "")
    secao(f"{rotulo} • agente × analista, caso a caso")
    print(f"  {'#':<3}{'Cliente':<9}{'Pedido':<58}{'Agente':<14}{'Analista':<14}")
    acertos, tokens, segundos, rodados = 0, 0, 0.0, 0
    for i, caso in enumerate(HISTORICO, 1):
        print(f"  {i:<3}{caso['cliente']:<9}{caso['mensagem'][:56]:<58}", end="", flush=True)
        r = rodar_caso(caso)
        caso["r"] = r
        if not r:
            continue
        ok = r["proposta"] == caso["humano"]
        acertos += ok
        rodados += 1
        tokens += r["tokens_entrada"] + r["tokens_saida"]
        segundos += r["segundos"]
        print(f"{r['proposta']:<14}{caso['humano']:<14}{C.VERDE + '✓' if ok else C.VERMELHO + '✕'}{C.FIM}")
    if not rodados:
        return
    pct = 100 * acertos / rodados
    estado["historico_rodadas"].append((estado["rodada"], len(estado["ajustes"]), pct))

    secao("Resultado")
    print(f"  Concordância com os analistas ... {C.NEGRITO}{pct:.0f}%{C.FIM} ({acertos} de {rodados})")
    print(f"  Tokens consumidos ............... {tokens}  (≈ {tokens // rodados} por caso)")
    print(f"  Tempo total ..................... {segundos:.1f} s")
    print(f"  Propostas registradas em ........ auditoria_demo06.jsonl")
    if len(estado["historico_rodadas"]) > 1:
        evolucao = " → ".join(f"{p:.0f}%" for _, _, p in estado["historico_rodadas"])
        print(f"  Evolução entre rodadas .......... {evolucao}")
    if pct >= estado["meta"]:
        print(f"\n  {C.VERDE}{C.NEGRITO}✓ Meta de {estado['meta']:.0f}% atingida:{C.FIM} pronto para propor autonomia "
              f"assistida ao comitê (começando pela menor alçada).")
    else:
        divergentes = [str(i) for i, c in enumerate(HISTORICO, 1) if c.get("r") and c["r"]["proposta"] != c["humano"]]
        print(f"\n  {C.LARANJA}{C.NEGRITO}Abaixo da meta de {estado['meta']:.0f}%:{C.FIM} continua em modo sombra. "
              f"Investigue {('o caso ' if len(divergentes) == 1 else 'os casos ') + ', '.join(divergentes)} "
              f"(digite o número) e use /ajuste.")


def detalhar(n: int) -> None:
    caso = HISTORICO[n - 1]
    r = caso.get("r")
    secao(f"Caso {n} • {CLIENTES[caso['cliente']]['nome']} ({caso['cliente']}) • analista: {caso['humano']}")
    print(f"  {C.AZUL}Pedido:{C.FIM} {caso['mensagem']}")
    if not r:
        print(f"  {C.CINZA}Ainda não rodado. ENTER roda todos.{C.FIM}")
        return
    print(f"  {C.CINZA}Caminho: {' → '.join(r['ferramentas']) or '(nenhuma ferramenta)'}{C.FIM}")
    for etiqueta, motivo in r["eventos"]:
        print(f"  {C.ROXO}🛡️  {etiqueta}: {motivo}{C.FIM}")
    print(f"  {C.VERDE}Conclusão do agente:{C.FIM} {r['resposta']}")
    ok = r["proposta"] == caso["humano"]
    print(f"  Proposta {C.NEGRITO}{r['proposta']}{C.FIM} × analista {C.NEGRITO}{caso['humano']}{C.FIM} → "
          f"{C.VERDE + 'concordou' if ok else C.VERMELHO + 'divergiu'}{C.FIM}")


def novo_caso() -> None:
    cliente = ler_cliente(perguntar(f"Cliente ({', '.join(CLIENTES)})"))
    if cliente not in CLIENTES:
        print(f"  {C.CINZA}Cliente desconhecido.{C.FIM}")
        return
    mensagem = perguntar("Mensagem do cliente")
    decisao = perguntar("Decisão do analista (E = estorno, S = sem estorno)").strip().upper()
    humano = "ESTORNO" if decisao.startswith("E") else "SEM ESTORNO"
    HISTORICO.append({"cliente": cliente, "mensagem": mensagem, "humano": humano})
    print(f"  {C.VERDE}Caso {len(HISTORICO)} cadastrado.{C.FIM} ENTER roda todos de novo.")


def listar() -> None:
    secao(f"Casos históricos ({len(HISTORICO)})")
    for i, c in enumerate(HISTORICO, 1):
        print(f"  {i:<3}{c['cliente']:<9}{c['mensagem'][:56]:<58}{C.CINZA}analista: {c['humano']}{C.FIM}")
    for a in estado["ajustes"]:
        print(f"  {C.LARANJA}ajuste:{C.FIM} {a}")


titulo(f"DEMO 06 • Modo sombra • {llm.nome} ({llm.modelo})")
print(f"\n{C.CINZA}O agente propõe; nada é executado. Comparamos com a decisão real do analista e "
      f"melhoramos o agente até atingir a meta.{C.FIM}")
listar()
mostrar_comandos(COMANDOS)

try:
    while True:
        try:
            texto = input(f"\n{C.AZUL}{C.NEGRITO}Modo sombra ›{C.FIM} ").strip()
        except (EOFError, KeyboardInterrupt):
            raise Encerrar
        cmd = texto.split()[0].lower() if texto else "/rodar"
        if cmd in ("/sair", "/fim", "sair"):
            raise Encerrar
        if cmd == "/rodar":
            rodar_todos()
        elif texto.isdigit() and 1 <= int(texto) <= len(HISTORICO):
            detalhar(int(texto))
        elif cmd == "/novo":
            novo_caso()
        elif cmd == "/ajuste":
            ajuste = argumento(texto) or AJUSTE_SUGERIDO
            estado["ajustes"].append(ajuste)
            print(f"  {C.LARANJA}Instrução acrescentada:{C.FIM} {ajuste}\n  {C.CINZA}ENTER roda de novo para medir o "
                  f"efeito.{C.FIM}")
        elif cmd == "/meta" and re.fullmatch(r"\d+(\.\d+)?%?", argumento(texto)):
            estado["meta"] = float(argumento(texto).rstrip("%"))
            print(f"  {C.CINZA}Meta de concordância: {estado['meta']:.0f}%.{C.FIM}")
        elif cmd == "/casos":
            listar()
        else:
            mostrar_comandos(COMANDOS)
except Encerrar:
    pass

print(f"\n{C.AZUL}{C.NEGRITO}Mensagem-chave:{C.FIM} primeiro medimos, depois liberamos autonomia; "
      f"divergências viram ajustes nas instruções, nas ferramentas e na base de conhecimento.\n")
