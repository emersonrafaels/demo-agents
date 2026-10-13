"""
DEMO 05 — Autonomia com guardrails e humano no circuito (interativa: "tente quebrar o agente")

Você (ou a plateia) manda mensagens para o agente tentando fazê-lo errar. As proteções estão no código
(agente/guardrails.py) e valem qualquer que seja o modelo:
  • dentro da alçada               → o agente resolve sozinho
  • acima da alçada                → o código pausa e pede aprovação a um HUMANO (você decide na hora)
  • instrução maliciosa            → bloqueada ANTES de chegar ao modelo
  • conta de outro cliente         → o escopo da sessão nega o acesso
  • agir sem analisar              → a pré-condição exige análise de risco e consulta à política
A alçada é decisão de negócio: mude ao vivo com /alcada e veja o mesmo pedido ter outro desfecho.

Executar:
  python 05_guardrails.py --provedor claude          (pergunta a aprovação ao apresentador)
  python 05_guardrails.py --provedor gpt --auto      (aprova sozinho, para ensaio)
  python 05_guardrails.py --provedor claude --web    (abre no navegador)
"""

import json
import os

from agente import FERRAMENTAS_CARTAO, Agente, Auditoria, BaseConhecimento, Guardrails, Memoria, avaliacao
from agente.dados import CLIENTES
from utils import criar_provedor
from utils.console import C, FLAGS, brl, opcao, secao, titulo
from utils.interativo import (Encerrar, abrir_web, ao_vivo, argumento, confirmar, ler_cliente, mostrar_comandos,
                              mostrar_sugestoes, perguntar)
from utils.roteiro import CASOS_GUARDRAILS

if "--web" in FLAGS:
    abrir_web("guardrails")
ARQUIVO = "auditoria_demo05.jsonl"
if os.path.exists(ARQUIVO):
    os.remove(ARQUIVO)
auditoria = Auditoria(ARQUIVO)
llm = criar_provedor(opcao("provedor"), opcao("modelo"))

CASOS = [(c, m) for c, m, _ in CASOS_GUARDRAILS]   # (cliente da sessão, mensagem)
SUGESTOES = [f"[{c}] {m}" for c, m in CASOS]
COMANDOS = {"/alcada VALOR": "muda a alçada do agente (ex.: /alcada 10000)",
            "/cliente C-100X": "troca o cliente logado (nova sessão)",
            "/auditoria": "mostra a trilha de auditoria",
            "/placar": "quem decidiu o quê até agora",
            "/nova": "recomeça a conversa",
            "/ajuda": "mostra casos prontos e comandos"}

estado = {"cliente": "C-1001", "alcada": 2000.0}


def aprovador_humano(chamada) -> bool:
    print(f"""
  {C.ROXO}{C.NEGRITO}┌─ PEDIDO DE APROVAÇÃO ───────────────────────────────────────┐{C.FIM}
  {C.ROXO}│{C.FIM} Ação proposta pelo agente: {chamada.nome}
  {C.ROXO}│{C.FIM} Transação {chamada.args.get('transacao_id')} • valor {brl(float(chamada.args.get('valor', 0)))}
  {C.ROXO}│{C.FIM} Motivo da pausa: acima da alçada de {brl(estado['alcada'])}
  {C.ROXO}{C.NEGRITO}└─────────────────────────────────────────────────────────────┘{C.FIM}""")
    if "--auto" in FLAGS:
        print(f"  Analista: {C.VERDE}aprovado (modo --auto){C.FIM}")
        return True
    aprovado = confirmar("Analista, aprova?")
    auditoria.registrar("analista", "decisao_humana", {"ferramenta": chamada.nome, "args": chamada.args,
                                                        "aprovado": aprovado})
    return aprovado


def montar() -> Agente:
    return Agente(llm, memoria=Memoria(), ferramentas=FERRAMENTAS_CARTAO, conhecimento=BaseConhecimento(),
                  guardrails=Guardrails(cliente_sessao=estado["cliente"], alcada=estado["alcada"],
                                        aprovador=aprovador_humano, auditoria=auditoria),
                  nome=f"sessao-{estado['cliente']}")


def sessao():
    c = CLIENTES[estado["cliente"]]
    print(f"  {C.CINZA}Sessão: {c['nome']} ({estado['cliente']}) • alçada do agente {brl(estado['alcada'])}{C.FIM}")


CORES_DECISAO = {"entrada": C.ROXO, "escopo": C.ROXO, "precondicao": C.ROXO, "pendente": C.LARANJA,
                 "humano": C.LARANJA, "agente": C.VERDE, "sem_estorno": C.CINZA}


def quem_decidiu(r) -> str:
    codigo, descricao = avaliacao.quem_decidiu(r)
    return f"{CORES_DECISAO[codigo]}{descricao}{C.FIM}"


def mostrar_placar(placar):
    secao("Quem decidiu o quê")
    for i, (cliente, alcada, mensagem, r) in enumerate(placar, 1):
        print(f"  {i}. {C.CINZA}[{cliente} • alçada {brl(alcada)}]{C.FIM} {mensagem[:60]}")
        print(f"     → {quem_decidiu(r)} • ferramentas: {len(r['ferramentas'])} • "
              f"tokens: {r['tokens_entrada'] + r['tokens_saida']}")


def mostrar_auditoria(n=8):
    if not os.path.exists(ARQUIVO):
        print(f"  {C.CINZA}Trilha vazia.{C.FIM}")
        return
    with open(ARQUIVO, encoding="utf-8") as f:
        linhas = f.readlines()
    secao(f"Trilha de auditoria ({ARQUIVO}) — últimas linhas")
    for linha in linhas[-n:]:
        e = json.loads(linha)
        print(f"  {C.CINZA}{e['quando'][11:]}{C.FIM} {e['agente']:<13} {e['tipo']:<17} {e['detalhe'][:80]}")
    print(f"  {C.CINZA}… {len(linhas)} eventos registrados, com CPF e nomes mascarados.{C.FIM}")


titulo(f"DEMO 05 • Guardrails • {llm.nome} ({llm.modelo})")
print(f"\n{C.CINZA}Tente fazer o agente errar. Acima da alçada (decisão de negócio), o código pede aprovação "
      f"humana, não importa o que o modelo decida.{C.FIM}")
sessao()
agente = montar()
mostrar_sugestoes(SUGESTOES, "Casos e ataques prontos (digite o número)")
mostrar_comandos(COMANDOS)
placar = []

try:
    while True:
        texto = perguntar(f"Cliente {estado['cliente']}", SUGESTOES)
        cmd = texto.split()[0].lower()
        if cmd in ("/alcada", "/alçada"):
            try:
                estado["alcada"] = float(argumento(texto).replace(".", "").replace(",", "."))
            except ValueError:
                print(f"  {C.CINZA}Use: /alcada 10000{C.FIM}")
                continue
            agente = montar()
            print(f"  {C.LARANJA}Nova alçada definida pelo negócio.{C.FIM} Conversa nova.")
            sessao()
        elif cmd == "/cliente" and ler_cliente(argumento(texto)) in CLIENTES:
            estado["cliente"] = ler_cliente(argumento(texto))
            agente = montar()
            sessao()
        elif cmd == "/auditoria":
            mostrar_auditoria()
        elif cmd == "/placar":
            mostrar_placar(placar)
        elif cmd == "/nova":
            agente = montar()
            print(f"  {C.CINZA}Conversa reiniciada.{C.FIM}")
        elif texto.startswith("/"):
            mostrar_sugestoes(SUGESTOES, "Casos e ataques prontos (digite o número)")
            mostrar_comandos(COMANDOS)
        else:
            cliente = ler_cliente(texto[:9]) if texto.startswith("[") else None
            if cliente in CLIENTES:
                texto = texto.split("]", 1)[1].strip()
                if cliente != estado["cliente"]:
                    estado["cliente"] = cliente
                    agente = montar()
                    print(f"  {C.CINZA}Trocando de sessão:{C.FIM}")
                    sessao()
            r = ao_vivo(agente.conversar, texto, contexto=f"[cliente_id: {estado['cliente']}] ")
            if r:
                print(f"\n  {C.NEGRITO}Quem decidiu:{C.FIM} {quem_decidiu(r)}")
                placar.append((estado["cliente"], estado["alcada"], texto, r))
except Encerrar:
    pass

if placar:
    mostrar_placar(placar)
    mostrar_auditoria(6)
print(f"\n{C.AZUL}{C.NEGRITO}Mensagem-chave:{C.FIM} autonomia é decisão de negócio; as proteções ficam no código.\n")
