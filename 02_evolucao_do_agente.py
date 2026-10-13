"""
DEMO 02 — A evolução do agente, peça por peça (interativa)

Você conversa com o agente e, a qualquer momento, encaixa ou tira uma peça:

    Nível 1  Só LLM                    Agente(llm)
    Nível 2  + memória                 Agente(llm, memoria=Memoria())
    Nível 3  + ferramentas             ... ferramentas=FERRAMENTAS_CARTAO
    Nível 4  + busca de conhecimento   ... conhecimento=BaseConhecimento()
    Nível 5  + guardrails              ... guardrails=Guardrails(cliente_sessao="C-1001", ...)

Ao trocar de nível, a demo oferece repetir a conversa feita até ali: a plateia vê a MESMA conversa
mudar de resultado quando a peça entra. /comparar roda a conversa nos cinco níveis e mostra o placar.

Roteiro sugerido (mensagens prontas 1 a 4):
    1) apresentação             → base para testar a memória
    2) contestação de compra    → lembra quem é a cliente? resolve o caso?
    3) pergunta sobre prazos    → responde com base nas normas, citando a fonte?
    4) pedido sobre outra conta → protege os dados e a conta de outro cliente?

Executar:
  python 02_evolucao_do_agente.py --provedor claude
  python 02_evolucao_do_agente.py --provedor gpt --nivel 3        (começa no nível 3)
  python 02_evolucao_do_agente.py --provedor simulado --detalhe   (mostra o ciclo completo)
  python 02_evolucao_do_agente.py --provedor claude --web         (abre no navegador: peças em checkboxes)
"""

from agente import FERRAMENTAS_CARTAO, Agente, Auditoria, BaseConhecimento, Guardrails, Memoria, avaliacao
from agente.dados import CLIENTES
from utils import criar_provedor
from utils.console import C, FLAGS, brl, digitar, opcao, pausa, secao, titulo
from utils.roteiro import EVOLUCAO
from utils.interativo import (Encerrar, abrir_web, ao_vivo, argumento, confirmar, mostrar_comandos,
                              mostrar_sugestoes, perguntar)

if "--web" in FLAGS:     # versão web: as mesmas peças, escolhidas em checkboxes
    abrir_web("evolucao")

llm = criar_provedor(opcao("provedor"), opcao("modelo"))
CLIENTE = "C-1001"                                  # quem está logado no canal
PRIMEIRO_NOME = CLIENTES[CLIENTE]["nome"].split()[0]

SUGESTOES = EVOLUCAO
COMANDOS = {
    "/subir  (ou +)": "encaixa a próxima peça",
    "/descer (ou -)": "tira a última peça",
    "/nivel N": "vai direto para o nível N (1 a 5)",
    "/pecas": "mostra a montagem atual",
    "/roteiro": "roda as 4 mensagens prontas neste nível",
    "/comparar": "roda a conversa atual nos 5 níveis e mostra o placar",
    "/detalhe": "liga/desliga o ciclo completo (perceber → planejar → agir → observar)",
    "/nova": "recomeça a conversa no mesmo nível",
    "/ajuda": "mostra mensagens prontas e comandos",
}

NIVEIS = {
    1: ("Só LLM", "agente = Agente(llm)",
        "Conversa bem, mas cada mensagem chega isolada: não lembra, não acessa sistemas e não conhece as normas."),
    2: ("LLM + memória", "+ memoria=Memoria()",
        "Lembra da conversa; ainda só sabe falar."),
    3: ("LLM + memória + ferramentas", "+ ferramentas=FERRAMENTAS_CARTAO",
        "Consulta sistemas e age; mas não conhece as normas do banco."),
    4: ("… + busca de conhecimento", "+ conhecimento=BaseConhecimento()",
        "Consulta políticas e cita a fonte; mas nada no sistema impede uma ação indevida."),
    5: ("… + guardrails", f'+ guardrails=Guardrails(cliente_sessao="{CLIENTE}", alcada=2000)',
        "Limites no código: só o titular, alçada com aprovação humana, bloqueio de manipulação e auditoria."),
}


def montar(nivel: int, verboso: bool) -> Agente:
    """Cada nível acrescenta UMA peça ao anterior."""
    pecas = {}
    if nivel >= 2:
        pecas["memoria"] = Memoria(max_turnos=20)
    if nivel >= 3:
        pecas["ferramentas"] = FERRAMENTAS_CARTAO
    if nivel >= 4:
        pecas["conhecimento"] = BaseConhecimento("base_conhecimento")
    if nivel >= 5:
        pecas["guardrails"] = Guardrails(cliente_sessao=CLIENTE, alcada=2000,
                                         aprovador=lambda chamada: False,       # ninguém aprovou durante a demo
                                         auditoria=Auditoria("auditoria_demo02.jsonl"))
    return Agente(llm, nome=f"nivel-{nivel}", verboso=verboso, recuo="       ", **pecas)


def mostrar_pecas(nivel: int) -> None:
    secao(f"Montagem atual • Nível {nivel} • {NIVEIS[nivel][0]}")
    for n, (_, codigo, _) in NIVEIS.items():
        if n <= nivel:
            print(f"  {C.VERDE}✓{C.FIM} {C.LARANJA}{codigo}{C.FIM}")
        else:
            print(f"  {C.CINZA}· {codigo}{C.FIM}")
    print(f"\n  {C.CINZA}{NIVEIS[nivel][2]}{C.FIM}")


# ------------------------------------------------------------------ avaliação de cada resposta
def avaliar(turno: int, mensagem: str, r: dict, nivel: int) -> dict:
    return avaliacao.avaliar(turno, mensagem, r, CLIENTE, tem_ferramentas=nivel >= 3)


def marca(ok, largura=1):
    simbolo, cor = ("—", C.CINZA) if ok is None else ("✓", C.VERDE) if ok else ("✕", C.VERMELHO)
    return f"{cor}{simbolo.ljust(largura)}{C.FIM}"


def mostrar_avaliacao(a: dict, r: dict, nivel: int, memoria) -> None:
    recuo = "       "
    if nivel == 1:
        print(f"{recuo}{C.CINZA}🧠 sem memória: esta mensagem chegou isolada ao modelo{C.FIM}")
    elif memoria:
        n = memoria.turnos()
        print(f"{recuo}{C.CINZA}🧠 memória: {n} {'mensagem' if n == 1 else 'mensagens'} desta conversa{C.FIM}")
    if a["lembra"]:
        print(f"{recuo}{marca(True)} lembrou da cliente sem ela repetir quem é")
    if a["resolve"]:
        print(f"{recuo}{marca(True)} agiu nos sistemas para resolver")
    if a["fonte"]:
        print(f"{recuo}{marca(True)} respondeu com base na norma, citando a fonte")
    elif a["sem_fonte"]:
        print(f"{recuo}{marca(False)} citou prazo sem fonte: pode ter sido inventado")
    if a["invadiu"]:
        print(f"{recuo}{marca(False)} acessou/agiu na conta de outro cliente ({', '.join(sorted(a['invadiu']))})")
    elif a["protege"]:
        print(f"{recuo}{marca(True)} protegeu a conta de outro cliente")
    for valor in avaliacao.estornos_sem_aprovacao(r):
        print(f"{recuo}{C.VERMELHO}⚠ estorno de {brl(valor)} acima da alçada, sem aprovação humana{C.FIM}")


# ------------------------------------------------------------------ conversa
class Palco:
    def __init__(self, nivel: int):
        self.detalhe = "--detalhe" in FLAGS
        self.mensagens: list[str] = []
        self.trocar(nivel)

    def trocar(self, nivel: int) -> None:
        self.nivel = max(1, min(5, nivel))
        self.agente = montar(self.nivel, self.detalhe)
        self.mensagens = []

    def falar(self, mensagem: str, eco: bool = False) -> None:
        if eco:
            print(f"\n  {C.AZUL}{C.NEGRITO}👤 Cliente{C.FIM}  {mensagem}")
        r = ao_vivo(self.agente.conversar, mensagem)
        if not r:
            return
        if not self.detalhe:
            if r["executadas"] or r["eventos"]:
                cadeia = " → ".join(e["nome"] for e in r["executadas"]) or "nenhuma ferramenta executada"
                print(f"       {C.CINZA}🔧 {cadeia}{C.FIM}")
            for etiqueta, motivo in r["eventos"]:
                print(f"       {C.ROXO}🛡️  {etiqueta}: {motivo}{C.FIM}")
            digitar(f"  {C.VERDE}{C.NEGRITO}🤖 Agente{C.FIM}   {r['resposta']}")
        mostrar_avaliacao(avaliar(len(self.mensagens), mensagem, r, self.nivel), r, self.nivel, self.agente.memoria)
        self.mensagens.append(mensagem)

    def mudar_nivel(self, novo: int) -> None:
        novo = max(1, min(5, novo))
        if novo == self.nivel:
            print(f"  {C.CINZA}Já está no nível {novo}.{C.FIM}")
            return
        anteriores = list(self.mensagens)
        acao = "Encaixando" if novo > self.nivel else "Tirando"
        print(f"\n  {C.LARANJA}{C.NEGRITO}{acao} peça → nível {novo}: {NIVEIS[novo][0]}{C.FIM}")
        self.trocar(novo)
        mostrar_pecas(novo)
        if anteriores and confirmar(f"Repetir as {len(anteriores)} mensagens desta conversa no nível {novo}?", True):
            for m in anteriores:
                self.falar(m, eco=True)
                pausa(0.4)
        else:
            print(f"  {C.CINZA}Conversa nova no nível {novo}.{C.FIM}")


def comparar(mensagens: list[str]) -> None:
    secao(f"Comparação dos níveis • {len(mensagens)} mensagens")
    placar = []
    print(f"  {C.CINZA}rodando os níveis:", end="", flush=True)
    for nivel, (nome, _, _) in NIVEIS.items():
        print(f" {nivel}…", end="", flush=True)
        agente = montar(nivel, verboso=False)
        linha = {"nivel": nivel, "nome": nome, "voltas": 0, "tokens": 0}
        for turno, m in enumerate(mensagens):
            r = ao_vivo(agente.conversar, m)
            if not r:
                break
            linha["voltas"] += r["voltas"]
            linha["tokens"] += r["tokens_entrada"] + r["tokens_saida"]
            a = avaliar(turno, m, r, nivel)
            for chave in ("lembra", "resolve", "fonte"):
                if a[chave]:
                    linha[chave] = True
                elif a[chave] is False:
                    linha.setdefault(chave, False)
            if a["protege"] is not None:
                linha["protege"] = linha.get("protege", True) and a["protege"]
        placar.append(linha)
    print(f" pronto.{C.FIM}\n")
    print(f"  {'':<34}{'Lembra':<9}{'Resolve':<9}{'Fonte':<8}{'Protege':<9}{'Chamadas':<10}{'Tokens'}")
    for l in placar:
        print(f"  {l['nivel']}. {l['nome']:<31}{marca(l.get('lembra'), 9)}{marca(l.get('resolve'), 9)}"
              f"{marca(l.get('fonte'), 8)}{marca(l.get('protege'), 9)}{l['voltas']:<10}{l['tokens']}")
    print(f"\n{C.CINZA}Lembra = lembrou da cliente sem ela repetir • Resolve = agiu nos sistemas • Fonte = citou a "
          f"norma • Protege = não tocou na conta de outro cliente (— = não testado){C.FIM}")
    if llm.nome != "Simulado":
        print(f"{C.CINZA}Com um modelo real, os níveis 3 e 4 às vezes recusam sozinhos o pedido sobre a outra conta. "
              f"O nível 5 garante a proteção no código, qualquer que seja o modelo.{C.FIM}")


# ------------------------------------------------------------------ execução
titulo(f"DEMO 02 • A evolução do agente • {llm.nome} ({llm.modelo})")
print(f"\n{C.CINZA}Você é a cliente {CLIENTES[CLIENTE]['nome']} ({CLIENTE}). Converse com o agente e encaixe as "
      f"peças uma a uma: o modelo é sempre o mesmo.{C.FIM}")
palco = Palco(int(opcao("nivel") or 1))
mostrar_pecas(palco.nivel)
mostrar_sugestoes(SUGESTOES)
mostrar_comandos(COMANDOS)

try:
    while True:
        texto = perguntar(f"Cliente • nível {palco.nivel}", SUGESTOES)
        cmd = texto.split()[0].lower()
        if cmd in ("/subir", "+"):
            palco.mudar_nivel(palco.nivel + 1)
        elif cmd in ("/descer", "-"):
            palco.mudar_nivel(palco.nivel - 1)
        elif cmd == "/nivel" and argumento(texto).isdigit():
            palco.mudar_nivel(int(argumento(texto)))
        elif cmd == "/pecas":
            mostrar_pecas(palco.nivel)
        elif cmd == "/roteiro":
            palco.trocar(palco.nivel)
            secao(f"Roteiro no nível {palco.nivel} • {NIVEIS[palco.nivel][0]}")
            for m in SUGESTOES:
                palco.falar(m, eco=True)
                pausa(0.6)
        elif cmd == "/comparar":
            comparar(palco.mensagens or SUGESTOES)
        elif cmd == "/detalhe":
            palco.detalhe = not palco.detalhe
            palco.agente.verboso = palco.detalhe
            print(f"  {C.CINZA}Ciclo completo {'ligado' if palco.detalhe else 'desligado'}.{C.FIM}")
        elif cmd == "/nova":
            palco.trocar(palco.nivel)
            print(f"  {C.CINZA}Conversa reiniciada no nível {palco.nivel}.{C.FIM}")
        elif texto.startswith("/"):
            mostrar_sugestoes(SUGESTOES)
            mostrar_comandos(COMANDOS)
        else:
            palco.falar(texto)
except Encerrar:
    pass

print(f"\n{C.AZUL}{C.NEGRITO}Mensagem-chave:{C.FIM} o modelo é o mesmo nos cinco níveis; "
      f"o que transforma um LLM num agente confiável são as peças ao redor dele.\n")
