"""
DEMO 04 — Multiagentes: um orquestrador que usa outros agentes como ferramentas

  Orquestrador ──► Agente de Fraude      (LLM + ferramentas de cliente, transação e risco)
              ├──► Agente de Políticas   (LLM + busca de conhecimento)
              └──► Agente de Atendimento (LLM + memória) ⇄ Agente Revisor (LLM, responde em JSON)

O orquestrador recebe o caso e DECIDE quais especialistas acionar, como faria com qualquer ferramenta.
Para a demonstração, o primeiro rascunho do Atendimento recebe de propósito dois erros (CPF exposto e
promessa de estorno "definitivo"), para mostrar o Revisor barrando. Use --sem-erro para desligar.

Executar:
  python 04_multiagentes.py --provedor claude
  python 04_multiagentes.py --provedor gpt --sem-erro
"""

import json
import re

from agente import Agente, BaseConhecimento, Guardrails, Memoria, ferramenta, selecionar
from agente.dados import CLIENTES
from utils import criar_provedor
from utils.console import C, FLAGS, digitar, opcao, pausa, secao, titulo

llm = criar_provedor(opcao("provedor"), opcao("modelo"))
ERRO_PROPOSITAL = "--sem-erro" not in FLAGS
CLIENTE = "C-1001"
CORES = {"Orquestrador": C.AZUL, "Fraude": C.VERMELHO, "Políticas": C.ROXO,
         "Atendimento": C.LARANJA, "Revisor": C.VERDE}


def msg(de, para, texto):
    digitar(f"  {CORES[de]}{C.NEGRITO}{de:>12}{C.FIM} → {CORES.get(para, '')}{para:<12}{C.FIM} {texto}")
    pausa(0.3)


# ------------------------------------------------------------------ instruções de cada especialista
INSTR_FRAUDE = ("Você é o Agente de Fraude. Identifique o cliente, localize a transação citada pelo valor e "
                "avalie o risco. Responda em 1 frase: id da transação, loja, valor, score e principais sinais.")
INSTR_POLITICAS = ("Você é o Agente de Políticas. Consulte a base de conhecimento e diga, em até 2 frases, o que a "
                   "política permite para o caso (bloqueio, estorno provisório, aprovação humana). Cite a fonte.")
INSTR_ATENDIMENTO = ("Você é o Agente de Atendimento. Escreva a resposta final ao cliente em português, em até 3 "
                     "frases, cordial e objetiva. Use só o primeiro nome. Nunca inclua CPF. Informe o número de "
                     "protocolo. O estorno é sempre PROVISÓRIO, na próxima fatura. Responda só com o texto.")
INSTR_REVISOR = ("Você é o Agente Revisor de comunicações de um banco. Verifique se o texto: (1) não expõe CPF ou "
                 "dados sensíveis; (2) não promete estorno definitivo (só provisório é permitido); (3) informa o "
                 "número de protocolo. Responda APENAS com JSON: "
                 '{"aprovado": true|false, "problemas": ["..."]}')
INSTR_ORQUESTRADOR = ("Você é o Orquestrador de um time de agentes de um banco. Para resolver a contestação: "
                      "1) peça a análise ao agente de fraude; 2) pergunte ao agente de políticas o que é permitido; "
                      "3) peça ao agente de atendimento a resposta final ao cliente, com o resumo do que foi decidido "
                      "(cartão bloqueado e estorno provisório, se a política permitir). Antes de cada chamada, diga "
                      "em uma frase o que vai fazer. Ao final, devolva exatamente a resposta aprovada pelo atendimento.")


# ------------------------------------------------------------------ especialistas: cada um é um Agente
def agente_fraude(pedido: str) -> dict:
    msg("Orquestrador", "Fraude", pedido)
    especialista = Agente(llm, INSTR_FRAUDE, nome="fraude", verboso=False, instrucoes_automaticas=False,
                          ferramentas=selecionar("buscar_cliente", "consultar_transacoes", "analisar_risco_fraude"),
                          guardrails=Guardrails(cliente_sessao=CLIENTE))
    r = especialista.conversar(pedido, contexto=f"[cliente_id: {CLIENTE}] ")
    msg("Fraude", "Orquestrador", r["resposta"])
    return {"resposta": r["resposta"]}


def agente_politicas(pedido: str) -> dict:
    msg("Orquestrador", "Políticas", pedido)
    especialista = Agente(llm, INSTR_POLITICAS, nome="politicas", verboso=False, instrucoes_automaticas=False,
                          conhecimento=BaseConhecimento())
    r = especialista.conversar(pedido)
    msg("Políticas", "Orquestrador", r["resposta"])
    return {"resposta": r["resposta"]}


def agente_atendimento(pedido: str) -> dict:
    """Atendimento redige; Revisor confere; repete até aprovar (máx. 3 rodadas)."""
    msg("Orquestrador", "Atendimento", pedido)
    c = CLIENTES[CLIENTE]
    contexto = (f"Cliente: {c['nome']} (CPF {c['cpf']}), cartão final {c['cartao']}. "
                f"Protocolo 2026-48214. Caso: {pedido}")
    redator = Agente(llm, INSTR_ATENDIMENTO, memoria=Memoria(), nome="atendimento", verboso=False,
                     instrucoes_automaticas=False)       # com memória: lembra do próprio rascunho ao reescrever
    revisor = Agente(llm, INSTR_REVISOR, nome="revisor", verboso=False, instrucoes_automaticas=False)

    pedido_redacao = contexto
    for rodada in range(1, 4):
        if rodada == 1 and ERRO_PROPOSITAL:
            rascunho = (f"Olá {c['nome']} (CPF {c['cpf']}), o estorno de R$ 1.249,90 é definitivo e já foi "
                        f"creditado na sua conta.")
            redator.memoria.registrar([{"tipo": "usuario", "texto": contexto},
                                       {"tipo": "assistente", "texto": rascunho, "chamadas": [], "bruto": None,
                                        "provedor": ""}])
            msg("Atendimento", "Revisor", f"Rascunho v1 {C.CINZA}(erros inseridos de propósito){C.FIM}: “{rascunho}”")
        else:
            rascunho = redator.conversar(pedido_redacao)["resposta"]           # chamada real ao modelo
            msg("Atendimento", "Revisor", f"Rascunho v{rodada}: “{rascunho}”")

        parecer = ler_json(revisor.conversar(f"Rascunho para revisar:\n{rascunho}")["resposta"])
        if parecer.get("aprovado"):
            msg("Revisor", "Orquestrador", f"{C.VERDE}✓ Aprovado{C.FIM}: sem dados sensíveis, dentro da política.")
            return {"resposta_cliente": rascunho}
        for p in parecer.get("problemas", []):
            msg("Revisor", "Atendimento", f"{C.VERMELHO}✕{C.FIM} {p}")
        pedido_redacao = ("O revisor reprovou o rascunho pelos motivos: " + "; ".join(parecer.get("problemas", []))
                          + ". Reescreva corrigindo todos os pontos.")
    return {"resposta_cliente": None, "erro": "rascunho não aprovado após 3 rodadas"}


def ler_json(texto: str) -> dict:
    m = re.search(r"\{.*\}", texto or "", re.S)
    try:
        return json.loads(m.group(0)) if m else {"aprovado": False, "problemas": ["revisor não respondeu em JSON"]}
    except json.JSONDecodeError:
        return {"aprovado": False, "problemas": ["revisor respondeu JSON inválido"]}


# ------------------------------------------------------------------ os especialistas viram FERRAMENTAS do orquestrador
def como_ferramenta(nome, descricao, funcao, icone):
    return ferramenta(nome, descricao, {"pedido": {"type": "string", "description": "O que você precisa"}},
                      ["pedido"], funcao, icone=icone)


EQUIPE = [
    como_ferramenta("agente_fraude", "Especialista em fraude: localiza a transação e calcula o risco.",
                    agente_fraude, "🛡️ "),
    como_ferramenta("agente_politicas", "Especialista em políticas: diz o que a política permite, com fonte.",
                    agente_politicas, "📜"),
    como_ferramenta("agente_atendimento", "Redige a resposta ao cliente; um revisor confere antes de liberar.",
                    agente_atendimento, "✍️ "),
]

# ------------------------------------------------------------------ execução
titulo(f"DEMO 04 • Multiagentes • {llm.nome} ({llm.modelo})")
caso = "Cliente não reconhece uma compra de R$ 1.249,90 no cartão."
print(f"\n{C.NEGRITO}Caso:{C.FIM} {caso}")
secao("O orquestrador decide quem acionar")
orquestrador = Agente(llm, INSTR_ORQUESTRADOR, ferramentas=EQUIPE, nome="orquestrador", verboso=False,
                      instrucoes_automaticas=False)
final = orquestrador.conversar(caso, contexto=f"[cliente_id: {CLIENTE}] ")

secao("Resultado consolidado")
print(f"  {C.VERDE}Resposta ao cliente:{C.FIM} {final['resposta']}")
print(f"  {C.CINZA}Especialistas acionados pelo orquestrador: {' → '.join(final['ferramentas'])}{C.FIM}")
print(f"\n{C.AZUL}{C.NEGRITO}Mensagem-chave:{C.FIM} especialistas com instruções e acessos próprios, que se "
      f"verificam mutuamente; o erro do rascunho nunca chega ao cliente.\n")
