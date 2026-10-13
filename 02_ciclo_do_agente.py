"""
DEMO 02 — O ciclo do agente, passo a passo (chamadas reais ao Claude e/ou ao GPT)

    PERCEBER → PLANEJAR → AGIR → OBSERVAR → (repete) → RESPONDER

Com --provedor ambos, o MESMO agente (mesmas instruções e ferramentas) roda no Claude e no GPT,
e ao final aparece a comparação: voltas, ferramentas, tokens e tempo.

Executar:
  python 02_ciclo_do_agente.py --provedor claude --passo     (ENTER a cada etapa)
  python 02_ciclo_do_agente.py --provedor ambos
"""

from agente import INSTRUCOES_CONTESTACAO, Agente
from console import C, opcao, secao, titulo
from ferramentas import TODAS_CONTESTACAO
from llm import criar_provedor

MENSAGEM = "Não reconheço uma compra de R$ 1.249,90 no meu cartão."
escolha = (opcao("provedor") or "").lower()
nomes = ["claude", "gpt"] if escolha == "ambos" else [escolha or None]

titulo("DEMO 02 • O ciclo do agente")
print(f"""
{C.CINZA}Legenda:{C.FIM}
  {C.AZUL}{C.NEGRITO}PERCEBER{C.FIM}   o que chegou para o agente
  {C.CINZA}{C.NEGRITO}PLANEJAR{C.FIM}   o modelo explica o próximo passo e por quê
  {C.LARANJA}{C.NEGRITO}AGIR{C.FIM}       a ferramenta (sistema) que o modelo pediu para chamar
  {C.VERDE}{C.NEGRITO}OBSERVAR{C.FIM}   o que o sistema devolveu; volta para o modelo como memória""")

resultados = []
for nome in nomes:
    provedor = criar_provedor(nome, opcao("modelo") if len(nomes) == 1 else None)
    secao(f"Execução • {provedor.nome} ({provedor.modelo})")
    agente = Agente(provedor, INSTRUCOES_CONTESTACAO, TODAS_CONTESTACAO, nome=f"contestacoes-{provedor.nome}")
    resultados.append(agente.executar(MENSAGEM, contexto="[cliente_id: C-1001] "))

secao("Resumo")
print(f"  {'':<22}" + "".join(f"{r['provedor']:<18}" for r in resultados))
for rotulo, chave in [("Voltas no ciclo", "voltas"), ("Tempo (s)", "segundos"),
                      ("Tokens de entrada", "tokens_entrada"), ("Tokens de saída", "tokens_saida")]:
    print(f"  {rotulo:<22}" + "".join(f"{str(r[chave]):<18}" for r in resultados))
print(f"  {'Ferramentas usadas':<22}" + "".join(f"{len(r['ferramentas']):<18}" for r in resultados))
for r in resultados:
    print(f"  {C.CINZA}{r['provedor']}: {' → '.join(r['ferramentas'])}{C.FIM}")
print(f"\n{C.AZUL}{C.NEGRITO}Mensagem-chave:{C.FIM} ninguém programou a ordem dos passos: o modelo decide o "
      f"próximo passo com base no que já descobriu. Trilha completa em auditoria_agentes.jsonl.\n")
if any(r["provedor"] == "Simulado" for r in resultados):
    print(f"{C.CINZA}(Modo simulado: as decisões vieram de regras locais, só para ensaio. "
          f"Rode com --provedor claude ou gpt para ver o modelo decidindo.){C.FIM}\n")
