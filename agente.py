"""
agente.py — o ciclo do agente: PERCEBER → PLANEJAR → AGIR → OBSERVAR, repetido até cumprir o objetivo.

Funciona igual com Claude, GPT ou o provedor simulado: quem decide o próximo passo é o modelo;
quem EXECUTA as ferramentas, aplica os guardrails e registra a auditoria é este código.
"""

import json
import time

import guardrails as g
from console import C, etapa, pausa
from ferramentas import resumir

# Instruções-padrão do agente de contestações (o "objetivo e instruções" da anatomia)
INSTRUCOES_CONTESTACAO = """Você é o Agente de Contestações de cartão de um banco (ambiente de demonstração, dados fictícios).
Objetivo: resolver a contestação do cliente de ponta a ponta usando as ferramentas.
Como trabalhar:
- Antes de CADA chamada de ferramenta, escreva uma frase curta dizendo o que vai fazer e por quê.
- Identifique o cliente, localize a transação pelo valor, avalie o risco e consulte a política ANTES de qualquer ação.
- Siga a política à risca. Nunca invente regras, prazos ou valores.
- Ao final, registre um protocolo e responda ao cliente em português, em até 3 frases, dizendo o que foi feito.
- Nunca inclua CPF ou dados sensíveis na resposta.
- Se uma ação for negada ou ficar pendente de aprovação, informe que um especialista vai concluir a análise."""


class Agente:
    def __init__(self, provedor, instrucoes, ferramentas, nome="Agente", max_voltas=12,
                 aprovador=None, auditoria=None, modo_sombra=False, verboso=True, recuo="  "):
        self.provedor = provedor
        self.instrucoes = instrucoes
        self.ferramentas = {f["nome"]: f for f in ferramentas}
        self.nome = nome
        self.max_voltas = max_voltas            # guardrail: nunca entra em loop infinito
        self.aprovador = aprovador              # função que pede OK humano acima da alçada
        self.auditoria = auditoria or g.Auditoria()
        self.modo_sombra = modo_sombra          # True: propõe ações, mas não executa
        self.verboso = verboso
        self.recuo = recuo

    def _log(self, etiqueta, cor, texto):
        if self.verboso:
            etapa(etiqueta, cor, texto, self.recuo)

    def executar(self, mensagem: str, contexto: str = "") -> dict:
        inicio, tokens = time.time(), [0, 0]
        executadas, acoes, historico = [], [], [{"tipo": "usuario", "texto": f"{contexto}{mensagem}"}]
        self.auditoria.registrar(self.nome, "inicio", {"mensagem": mensagem, "provedor": self.provedor.nome})

        # ---------- 1) PERCEBER
        self._log("PERCEBER", C.AZUL, f"“{mensagem}”")
        if g.detectar_instrucao_maliciosa(mensagem):                       # guardrail de entrada
            self._log("GUARDRAIL", C.ROXO, "Instrução suspeita: o modelo nem é acionado e nenhuma "
                                            "ferramenta roda. Caso enviado ao time de segurança.")
            self.auditoria.registrar(self.nome, "bloqueio_entrada", {"mensagem": mensagem})
            return self._fim("bloqueado", "Recebemos sua mensagem; um especialista vai analisar o caso.",
                             0, executadas, acoes, tokens, inicio)

        for volta in range(1, self.max_voltas + 1):
            # ---------- 2) PLANEJAR: o modelo decide o próximo passo
            r = self.provedor.conversar(self.instrucoes, historico, list(self.ferramentas.values()))
            tokens[0] += r.tokens_entrada
            tokens[1] += r.tokens_saida
            historico.append({"tipo": "assistente", "texto": r.texto, "chamadas": r.chamadas,
                              "bruto": r.bruto, "provedor": self.provedor.nome})

            if not r.chamadas:                                              # sem ferramentas: terminou
                self._log("RESPONDER", C.VERDE, r.texto)
                self.auditoria.registrar(self.nome, "resposta", r.texto)
                return self._fim("concluido", r.texto, volta, executadas, acoes, tokens, inicio)

            self._log("PLANEJAR", C.CINZA, r.texto or f"(decidiu chamar {', '.join(c.nome for c in r.chamadas)})")
            pausa(0.2)

            for ch in r.chamadas:
                # ---------- 3) AGIR (com guardrails de ação)
                resultado = self._agir(ch, executadas, acoes)
                # ---------- 4) OBSERVAR: o resultado volta para o modelo como memória
                self._log("OBSERVAR", C.VERDE, resumir(resultado))
                historico.append({"tipo": "resultado", "id": ch.id, "nome": ch.nome,
                                  "conteudo": json.dumps(resultado, ensure_ascii=False)})
                pausa(0.3)

        self._log("LIMITE", C.VERMELHO, f"{self.max_voltas} voltas sem concluir: caso enviado a um humano.")
        return self._fim("limite", None, self.max_voltas, executadas, acoes, tokens, inicio)

    def _agir(self, ch, executadas, acoes):
        f = self.ferramentas.get(ch.nome)
        args_txt = ", ".join(f"{k}={v!r}" for k, v in ch.args.items())
        self._log("AGIR", C.LARANJA, f"{f['icone'] if f else '🔧'} {ch.nome}({args_txt})")
        if not f:
            return {"erro": f"ferramenta {ch.nome} não existe"}

        if f["acao"]:
            if not g.pre_condicoes_ok(set(executadas), set(self.ferramentas)):
                self._log("GUARDRAIL", C.ROXO, "Ação negada: falta checar risco e política antes.")
                return {"erro": "Ação negada pelo sistema: consulte o risco e a política antes de agir."}
            acoes.append({"ferramenta": ch.nome, "args": ch.args})
            if self.modo_sombra:
                self._log("SOMBRA", C.ROXO, "Modo sombra: ação registrada como proposta, NÃO executada.")
                self.auditoria.registrar(self.nome, "acao_proposta", {"ferramenta": ch.nome, "args": ch.args})
                return {"status": "PROPOSTA REGISTRADA (modo sombra, não executada)"}
            if g.exige_aprovacao(ch.nome, ch.args):
                self._log("ALÇADA", C.ROXO, "Acima da alçada do agente: pedindo aprovação humana.")
                aprovado = bool(self.aprovador and self.aprovador(ch))
                self.auditoria.registrar(self.nome, "aprovacao_humana", {"acao": ch.nome, "aprovado": aprovado})
                if not aprovado:
                    acoes[-1]["status"] = "pendente"
                    return {"erro": "Ação pendente: exige aprovação humana. Caso encaminhado a um especialista."}

        try:
            resultado = f["funcao"](**ch.args)
        except Exception as e:                       # erro de ferramenta volta ao modelo, não derruba o agente
            resultado = {"erro": f"falha ao executar {ch.nome}: {e}"}
        executadas.append(ch.nome)
        self.auditoria.registrar(self.nome, "ferramenta", {"nome": ch.nome, "args": ch.args})
        return resultado

    def _fim(self, status, resposta, voltas, executadas, acoes, tokens, inicio):
        return {"status": status, "resposta": resposta, "voltas": voltas, "ferramentas": executadas,
                "acoes": acoes, "tokens_entrada": tokens[0], "tokens_saida": tokens[1],
                "segundos": round(time.time() - inicio, 1), "provedor": self.provedor.nome,
                "modelo": getattr(self.provedor, "modelo", "")}
