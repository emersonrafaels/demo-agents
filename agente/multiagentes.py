"""
agente/multiagentes.py — um orquestrador que usa outros agentes como ferramentas.

  Orquestrador ──► Agente de Fraude      (LLM + ferramentas de cliente, transação e risco)
              ├──► Agente de Políticas   (LLM + busca de conhecimento)
              └──► Agente de Atendimento (LLM + memória) ⇄ Agente Revisor (LLM, responde em JSON)

Cada especialista é um Agente comum, com instruções e acessos próprios. Para o orquestrador, ele é só
mais uma ferramenta: o modelo decide quando acioná-lo, como faria com qualquer sistema.

Quem exibe a conversa (terminal ou navegador) recebe cada mensagem entre agentes por `ao_falar`.
"""

from __future__ import annotations

import json
import re

from .ciclo import Agente
from .conhecimento import BaseConhecimento
from .dados import CLIENTES
from .ferramentas import ferramenta, registrar_protocolo, selecionar
from .guardrails import Guardrails
from .memoria import Memoria

INSTR_FRAUDE = ("Você é o Agente de Fraude. Identifique o cliente, localize a transação citada pelo valor e "
                "avalie o risco. Responda em 1 frase: id da transação, loja, valor, score e principais sinais.")
INSTR_POLITICAS = ("Você é o Agente de Políticas. Consulte a base de conhecimento e diga, em até 2 frases, o que a "
                   "política permite para o caso (bloqueio, estorno provisório, aprovação humana, histórico de "
                   "contestações). Cite a fonte.")
INSTR_ATENDIMENTO = ("Você é o Agente de Atendimento. Escreva a resposta final ao cliente em português, em até 3 "
                     "frases, cordial e objetiva. Use só o primeiro nome. Nunca inclua CPF. Informe o número de "
                     "protocolo. Se houver estorno, ele é sempre PROVISÓRIO, na próxima fatura. Responda só com o texto.")
INSTR_REVISOR = ("Você é o Agente Revisor de comunicações de um banco. Verifique se o texto: (1) não expõe CPF ou "
                 "dados sensíveis; (2) não promete estorno definitivo (só provisório é permitido); (3) informa o "
                 "número de protocolo. Responda APENAS com JSON: "
                 '{"aprovado": true|false, "problemas": ["..."]}')
INSTR_ORQUESTRADOR = ("Você é o Orquestrador de um time de agentes de um banco. Para resolver a contestação: "
                      "1) peça a análise ao agente de fraude; 2) pergunte ao agente de políticas o que é permitido "
                      "para esse risco, valor e histórico; 3) peça ao agente de atendimento a resposta final ao "
                      "cliente, com o resumo do que foi decidido conforme a política. Antes de cada chamada, diga "
                      "em uma frase o que vai fazer. Ao final, devolva exatamente a resposta aprovada pelo atendimento.")

MODOS_RASCUNHO = {"erro": "v1 com dois erros de propósito", "voce": "você escreve o v1", "ia": "a IA escreve desde o v1"}


def ler_json(texto: str) -> dict:
    m = re.search(r"\{.*\}", texto or "", re.S)
    try:
        return json.loads(m.group(0)) if m else {"aprovado": False, "problemas": ["revisor não respondeu em JSON"]}
    except json.JSONDecodeError:
        return {"aprovado": False, "problemas": ["revisor respondeu JSON inválido"]}


def como_ferramenta(nome, descricao, funcao, icone):
    """Um agente especialista vira uma ferramenta: o orquestrador só precisa mandar um pedido em texto."""
    return ferramenta(nome, descricao, {"pedido": {"type": "string", "description": "O que você precisa"}},
                      ["pedido"], funcao, icone=icone)


class Equipe:
    """
    modo_rascunho   "erro" | "voce" | "ia" — como nasce o primeiro rascunho da resposta ao cliente
    rascunho_humano função(cliente, protocolo) -> texto ou None; usada no modo "voce"
    ao_falar        função(de, para, texto, tipo) — tipo: "" | "ok" | "erro"; recebe cada mensagem entre agentes
    """

    def __init__(self, llm, cliente: str, *, modo_rascunho: str = "erro", rascunho_humano=None, ao_falar=None):
        self.llm = llm
        self.cliente = cliente
        self.modo_rascunho = modo_rascunho
        self.rascunho_humano = rascunho_humano
        self.ao_falar = ao_falar or (lambda de, para, texto, tipo="": None)
        self.protocolo = None

    def resolver(self, caso: str) -> dict:
        self.protocolo = registrar_protocolo(self.cliente, caso)["protocolo"]
        orquestrador = Agente(self.llm, INSTR_ORQUESTRADOR, ferramentas=self.ferramentas(), nome="orquestrador",
                              verboso=False, instrucoes_automaticas=False)
        return orquestrador.conversar(caso, contexto=f"[cliente_id: {self.cliente}] ")

    # ------------------------------------------------------------------ os especialistas viram FERRAMENTAS
    def ferramentas(self):
        return [
            como_ferramenta("agente_fraude", "Especialista em fraude: localiza a transação e calcula o risco.",
                            self.fraude, "🛡️ "),
            como_ferramenta("agente_politicas", "Especialista em políticas: diz o que a política permite, com fonte.",
                            self.politicas, "📜"),
            como_ferramenta("agente_atendimento", "Redige a resposta ao cliente; um revisor confere antes de liberar.",
                            self.atendimento, "✍️ "),
        ]

    # ------------------------------------------------------------------ cada especialista é um Agente
    def fraude(self, pedido: str) -> dict:
        self.ao_falar("Orquestrador", "Fraude", pedido)
        especialista = Agente(self.llm, INSTR_FRAUDE, nome="fraude", verboso=False, instrucoes_automaticas=False,
                              ferramentas=selecionar("buscar_cliente", "consultar_transacoes", "analisar_risco_fraude"),
                              guardrails=Guardrails(cliente_sessao=self.cliente))
        r = especialista.conversar(pedido, contexto=f"[cliente_id: {self.cliente}] ")
        self.ao_falar("Fraude", "Orquestrador", r["resposta"])
        return {"resposta": r["resposta"]}

    def politicas(self, pedido: str) -> dict:
        self.ao_falar("Orquestrador", "Políticas", pedido)
        especialista = Agente(self.llm, INSTR_POLITICAS, nome="politicas", verboso=False,
                              instrucoes_automaticas=False, conhecimento=BaseConhecimento())
        r = especialista.conversar(pedido)
        self.ao_falar("Políticas", "Orquestrador", r["resposta"])
        return {"resposta": r["resposta"]}

    def atendimento(self, pedido: str) -> dict:
        """Atendimento redige; Revisor confere; repete até aprovar (máx. 3 rodadas)."""
        self.ao_falar("Orquestrador", "Atendimento", pedido)
        c = CLIENTES[self.cliente]
        contexto = (f"Cliente: {c['nome']} (CPF {c['cpf']}), cartão final {c['cartao']}. "
                    f"Protocolo {self.protocolo}. Caso: {pedido}")
        redator = Agente(self.llm, INSTR_ATENDIMENTO, memoria=Memoria(), nome="atendimento", verboso=False,
                         instrucoes_automaticas=False)       # com memória: lembra do próprio rascunho ao reescrever
        revisor = Agente(self.llm, INSTR_REVISOR, nome="revisor", verboso=False, instrucoes_automaticas=False)

        pedido_redacao = contexto
        for rodada in range(1, 4):
            rascunho = self._rascunho_v1(c, contexto, redator) if rodada == 1 else None
            if rascunho is None:
                rascunho = redator.conversar(pedido_redacao)["resposta"]           # chamada real ao modelo
                self.ao_falar("Atendimento", "Revisor", f"Rascunho v{rodada}: “{rascunho}”")

            parecer = ler_json(revisor.conversar(f"Rascunho para revisar:\n{rascunho}")["resposta"])
            if parecer.get("aprovado"):
                self.ao_falar("Revisor", "Orquestrador", "Aprovado: sem dados sensíveis, dentro da política.", "ok")
                return {"resposta_cliente": rascunho}
            for p in parecer.get("problemas", []):
                self.ao_falar("Revisor", "Atendimento", p, "erro")
            pedido_redacao = ("O revisor reprovou o rascunho pelos motivos: " + "; ".join(parecer.get("problemas", []))
                              + ". Reescreva corrigindo todos os pontos.")
        return {"resposta_cliente": None, "erro": "rascunho não aprovado após 3 rodadas"}

    def _rascunho_v1(self, c, contexto, redator) -> str | None:
        """Primeiro rascunho conforme o modo escolhido. None = deixa a IA escrever."""
        if self.modo_rascunho == "erro":
            texto = (f"Olá {c['nome']} (CPF {c['cpf']}), o estorno da compra é definitivo e já foi creditado "
                     f"na sua conta.")
            autor, nota = "Atendimento", "erros inseridos de propósito"
        elif self.modo_rascunho == "voce" and self.rascunho_humano:
            texto = self.rascunho_humano(self.cliente, self.protocolo)
            autor, nota = "Você", "escrito por você"
        else:
            return None
        if not texto:
            return None
        redator.memoria.registrar([{"tipo": "usuario", "texto": contexto},
                                   {"tipo": "assistente", "texto": texto, "chamadas": [], "bruto": None,
                                    "provedor": ""}])
        self.ao_falar(autor, "Revisor", f"Rascunho v1 ({nota}): “{texto}”")
        return texto
