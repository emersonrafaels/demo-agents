"""
agente/modo_sombra.py — medir o agente contra decisões humanas ANTES de dar autonomia.

O agente analisa um caso já decidido por um analista, mas com Guardrails(modo_sombra=True): as ações
viram propostas registradas, sem execução. Comparando proposta × decisão humana, chega-se à
concordância — o primeiro número que um comitê pede antes de liberar autonomia.
"""

from __future__ import annotations

from . import instrucoes as instr
from .ciclo import Agente
from .ferramentas import FERRAMENTAS_CARTAO
from .guardrails import Auditoria, Guardrails


def propor(llm, caso: dict, conhecimento, ajustes=(), arquivo: str = "auditoria_demo06.jsonl", eco=None) -> dict:
    """Roda o agente em modo sombra e devolve o resultado com a proposta ("ESTORNO" ou "SEM ESTORNO")."""
    agente = Agente(llm, "\n".join([instr.BASE, *ajustes]),       # ajustes = instruções acrescentadas
                    ferramentas=FERRAMENTAS_CARTAO, conhecimento=conhecimento, nome=f"sombra-{caso['cliente']}",
                    guardrails=Guardrails(cliente_sessao=caso["cliente"], modo_sombra=True,
                                          auditoria=Auditoria(arquivo)),
                    verboso=False, eco=eco)
    r = agente.conversar(caso["mensagem"], contexto=f"[cliente_id: {caso['cliente']}] ")
    propos_estorno = any(a["ferramenta"] == "abrir_estorno_provisorio" for a in r["acoes"])
    r["proposta"] = "ESTORNO" if propos_estorno else "SEM ESTORNO"
    return r
