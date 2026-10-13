"""
agente/guardrails.py — proteções que ficam FORA do modelo.

O modelo pode errar ou ser manipulado; por isso as regras críticas são verificadas em código,
antes de qualquer ação, e valem para qualquer modelo (Claude, GPT, Iara...):

  1. Entrada      bloqueia tentativas de manipulação antes de chegar ao modelo
  2. Escopo       a sessão só acessa dados do cliente autenticado (identidade vem do login, não da conversa)
  3. Pré-condição nenhuma ação antes de avaliar o risco e consultar a política
  4. Modo sombra  ações viram propostas registradas, sem execução
  5. Alçada       acima do limite, só com aprovação humana
  6. Saída        mascara dados sensíveis na resposta
  7. Auditoria    cada decisão vira uma linha de log, com dados pessoais mascarados
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime

from .dados import CLIENTES, dono_dos_dados

PADROES_INJECAO = [
    r"ignore (as|todas as)? ?(regras|instru)", r"desconsidere (as|suas) (regras|instru)",
    r"voc[eê] agora [eé]", r"modo (administrador|desenvolvedor)", r"sem aprova[cç][aã]o",
    r"transfira .* para a conta",
]
CPF = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")


@dataclass
class Veredito:
    permitido: bool
    etiqueta: str = ""          # como aparece no terminal: GUARDRAIL, ALÇADA, SOMBRA
    motivo: str = ""
    resultado: dict | None = None
    status: str = "executada"   # executada | aprovada | negada | pendente | proposta


class Auditoria:
    """Trilha de auditoria em JSON Lines, com CPF e nomes completos mascarados."""

    def __init__(self, arquivo: str = "auditoria_agentes.jsonl"):
        self.arquivo = arquivo

    def registrar(self, agente: str, tipo: str, detalhe) -> None:
        texto = CPF.sub("***.***.***-**", json.dumps(detalhe, ensure_ascii=False, default=str))
        for c in CLIENTES.values():
            texto = texto.replace(c["nome"], c["nome"].split()[0] + " ***")
        evento = {"quando": datetime.now().isoformat(timespec="seconds"), "agente": agente,
                  "tipo": tipo, "detalhe": texto}
        with open(self.arquivo, "a", encoding="utf-8") as f:
            f.write(json.dumps(evento, ensure_ascii=False) + "\n")


class Guardrails:
    def __init__(self, cliente_sessao: str | None = None, alcada: float = 2000.0, aprovador=None,
                 modo_sombra: bool = False, auditoria: Auditoria | None = None,
                 pre_requisitos=("analisar_risco_fraude", "buscar_conhecimento")):
        self.cliente_sessao = cliente_sessao   # vem do login no canal, nunca do texto da conversa
        self.alcada = alcada                   # decisão de negócio
        self.aprovador = aprovador             # função(chamada) -> bool: pede OK a um humano
        self.modo_sombra = modo_sombra
        self.auditoria = auditoria or Auditoria()
        self.pre_requisitos = set(pre_requisitos)

    # 1) entrada
    def verificar_entrada(self, texto: str) -> str | None:
        if any(re.search(p, texto, flags=re.IGNORECASE) for p in PADROES_INJECAO):
            return "Instrução suspeita: o modelo nem é acionado. Caso enviado ao time de segurança."
        return None

    # 2) a 5) cada pedido de ferramenta
    def verificar_acao(self, chamada, ferramenta, executadas: list[str], disponiveis: set[str]) -> Veredito:
        dono = dono_dos_dados(chamada.args)
        if self.cliente_sessao and dono and dono != self.cliente_sessao:
            return Veredito(False, "GUARDRAIL", "Escopo: dados de outro cliente; a sessão é do titular "
                            f"{self.cliente_sessao}. Acesso negado.",
                            {"erro": "Acesso negado pelo sistema: esta sessão só pode consultar e agir sobre os "
                                     "dados do cliente autenticado."}, "negada")
        if not ferramenta.acao:
            return Veredito(True)

        faltam = (self.pre_requisitos & disponiveis) - set(executadas)
        if faltam:
            return Veredito(False, "GUARDRAIL", f"Pré-condição: falta {', '.join(sorted(faltam))} antes de agir.",
                            {"erro": "Ação negada pelo sistema: antes de agir, execute "
                                     + " e ".join(sorted(faltam)) + "."}, "negada")
        if self.modo_sombra:
            return Veredito(False, "SOMBRA", "Modo sombra: ação registrada como proposta, NÃO executada.",
                            {"status": "PROPOSTA REGISTRADA (modo sombra, não executada)"}, "proposta")
        if chamada.nome == "abrir_estorno_provisorio" and float(chamada.args.get("valor", 0)) > self.alcada:
            aprovado = bool(self.aprovador and self.aprovador(chamada))
            if not aprovado:
                return Veredito(False, "ALÇADA", "Acima da alçada: aguardando aprovação de um analista.",
                                {"erro": "Ação pendente: exige aprovação humana. Caso encaminhado a um especialista."},
                                "pendente")
            return Veredito(True, "ALÇADA", "Acima da alçada: aprovado pelo analista.", status="aprovada")
        return Veredito(True)

    # 6) saída
    @staticmethod
    def verificar_saida(texto: str) -> str:
        return CPF.sub("***.***.***-**", texto or "")

    # 7) auditoria
    def registrar(self, agente: str, tipo: str, detalhe) -> None:
        self.auditoria.registrar(agente, tipo, detalhe)
