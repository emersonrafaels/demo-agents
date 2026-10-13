"""
agente/ciclo.py — o agente: um modelo de linguagem + as peças que você decidir encaixar.

    Agente(llm)                                         só LLM
    Agente(llm, memoria=...)                            + lembra da conversa
    Agente(llm, memoria=..., ferramentas=...)           + consulta sistemas e age
    Agente(..., conhecimento=BaseConhecimento())        + consulta políticas e normas
    Agente(..., guardrails=Guardrails(...))             + limites, aprovação humana e auditoria

O ciclo é sempre o mesmo: PERCEBER → PLANEJAR → AGIR → OBSERVAR, até responder.
Quem decide o próximo passo é o modelo; quem executa, aplica os guardrails e registra é este código.
"""

from __future__ import annotations

import json
import time

from utils.console import C, etapa, pausa

from . import instrucoes as instr
from .ferramentas import resumir


class Agente:
    def __init__(self, provedor, instrucoes: str = instr.BASE, *, memoria=None, ferramentas=None,
                 conhecimento=None, guardrails=None, nome: str = "agente", max_voltas: int = 12,
                 instrucoes_automaticas: bool = True, verboso: bool = True, recuo: str = "  ", eco=None):
        self.provedor = provedor
        self.memoria = memoria
        self.conhecimento = conhecimento
        self.guardrails = guardrails
        self.ferramentas = {f.nome: f for f in (ferramentas or [])}
        if conhecimento:
            self.ferramentas["buscar_conhecimento"] = conhecimento.como_ferramenta()
        self.instrucoes = (instr.montar(instrucoes, bool(ferramentas), bool(conhecimento), bool(guardrails))
                           if instrucoes_automaticas else instrucoes)
        self.nome = nome
        self.max_voltas = max_voltas            # nunca entra em loop infinito
        self.verboso = verboso
        self.recuo = recuo
        self.eco = eco                          # função(etiqueta, texto): recebe cada etapa (ex.: interface web)

    # ------------------------------------------------------------------ utilidades
    def _log(self, etiqueta, cor, texto):
        if self.eco:
            self.eco(etiqueta, texto)
        if self.verboso:
            etapa(etiqueta, cor, texto, self.recuo)

    def _registrar(self, tipo, detalhe):
        if self.guardrails:
            self.guardrails.registrar(self.nome, tipo, detalhe)

    # ------------------------------------------------------------------ o ciclo
    def conversar(self, mensagem: str, contexto: str = "") -> dict:
        """Processa uma mensagem do cliente. Com memória, lembra das mensagens anteriores."""
        estado = {"inicio": time.time(), "tokens": [0, 0], "voltas": 0,
                  "executadas": [], "acoes": [], "eventos": []}
        novos = [{"tipo": "usuario", "texto": f"{contexto}{mensagem}"}]
        anteriores = self.memoria.mensagens() if self.memoria else []
        self._registrar("inicio", {"mensagem": mensagem, "provedor": self.provedor.nome})

        # 1) PERCEBER
        self._log("PERCEBER", C.AZUL, f"“{mensagem}”")
        if self.guardrails and (motivo := self.guardrails.verificar_entrada(mensagem)):
            self._log("GUARDRAIL", C.ROXO, motivo)
            estado["eventos"].append(("GUARDRAIL", motivo))
            self._registrar("bloqueio_entrada", {"mensagem": mensagem})
            resposta = "Recebemos sua mensagem; um especialista vai analisar o caso."
            novos.append({"tipo": "assistente", "texto": resposta, "chamadas": [], "bruto": None, "provedor": ""})
            return self._fim("bloqueado", resposta, novos, estado)

        for _ in range(self.max_voltas):
            # 2) PLANEJAR: o modelo lê tudo o que já sabe e decide o próximo passo
            r = self.provedor.conversar(self.instrucoes, anteriores + novos,
                                        list(self.ferramentas.values()) or None)
            estado["voltas"] += 1
            estado["tokens"][0] += r.tokens_entrada
            estado["tokens"][1] += r.tokens_saida
            novos.append({"tipo": "assistente", "texto": r.texto, "chamadas": r.chamadas,
                          "bruto": r.bruto, "provedor": self.provedor.nome})

            if not r.chamadas:                                        # nada mais a fazer: responde
                resposta = self.guardrails.verificar_saida(r.texto) if self.guardrails else r.texto
                self._log("RESPONDER", C.VERDE, resposta)
                self._registrar("resposta", resposta)
                return self._fim("concluido", resposta, novos, estado)

            self._log("PLANEJAR", C.CINZA, r.texto or f"(decidiu chamar {', '.join(c.nome for c in r.chamadas)})")
            pausa(0.2)
            for ch in r.chamadas:
                resultado = self._agir(ch, estado)                     # 3) AGIR
                self._log("OBSERVAR", C.VERDE, resumir(resultado))     # 4) OBSERVAR
                novos.append({"tipo": "resultado", "id": ch.id, "nome": ch.nome,
                              "conteudo": json.dumps(resultado, ensure_ascii=False)})
                pausa(0.3)

        self._log("LIMITE", C.VERMELHO, f"{self.max_voltas} voltas sem concluir: caso enviado a um humano.")
        return self._fim("limite", None, novos, estado)

    executar = conversar   # nome alternativo, usado nas demos de execução única

    def _agir(self, ch, estado):
        f = self.ferramentas.get(ch.nome)
        args_txt = ", ".join(f"{k}={v!r}" for k, v in ch.args.items())
        self._log("AGIR", C.LARANJA, f"{f.icone if f else '🔧'} {ch.nome}({args_txt})")
        if not f:
            return {"erro": f"ferramenta {ch.nome} não existe"}

        status = "executada"
        if self.guardrails:
            v = self.guardrails.verificar_acao(ch, f, [e["nome"] for e in estado["executadas"]],
                                               set(self.ferramentas))
            if v.motivo:
                self._log(v.etiqueta, C.ROXO, v.motivo)
                estado["eventos"].append((v.etiqueta, v.motivo))
                self._registrar(v.etiqueta.lower(), {"ferramenta": ch.nome, "args": ch.args, "status": v.status})
            if f.acao:
                estado["acoes"].append({"ferramenta": ch.nome, "args": ch.args, "status": v.status})
            if not v.permitido:
                return v.resultado
            status = v.status
        elif f.acao:
            estado["acoes"].append({"ferramenta": ch.nome, "args": ch.args, "status": status})

        try:
            resultado = f.funcao(**ch.args)
        except Exception as e:              # falha de sistema volta ao modelo como informação
            resultado = {"erro": f"falha ao executar {ch.nome}: {e}"}
        estado["executadas"].append({"nome": ch.nome, "args": ch.args, "status": status})
        self._registrar("ferramenta", {"nome": ch.nome, "args": ch.args})
        return resultado

    def _fim(self, status, resposta, novos, estado):
        if self.memoria:
            self.memoria.registrar(novos)
        return {"status": status, "resposta": resposta, "voltas": estado["voltas"],
                "ferramentas": [e["nome"] for e in estado["executadas"]], "executadas": estado["executadas"],
                "acoes": estado["acoes"], "eventos": estado["eventos"],
                "tokens_entrada": estado["tokens"][0], "tokens_saida": estado["tokens"][1],
                "segundos": round(time.time() - estado["inicio"], 1),
                "provedor": self.provedor.nome, "modelo": getattr(self.provedor, "modelo", "")}
