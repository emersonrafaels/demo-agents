"""
agente — as peças de um agente de IA, uma por arquivo (espelham o slide "Anatomia de um agente"):

    ciclo.py         o agente e o ciclo perceber → planejar → agir → observar
    instrucoes.py    objetivo e instruções
    memoria.py       memória da conversa
    ferramentas.py   ferramentas (as "mãos")
    conhecimento.py  busca de conhecimento em políticas e normas
    guardrails.py    limites, aprovação humana e auditoria
    avaliacao.py     o que uma resposta demonstrou (lembrou, resolveu, citou fonte, protegeu)
    multiagentes.py  orquestrador que usa outros agentes como ferramentas
    modo_sombra.py   propor sem executar e comparar com a decisão humana
    dados.py         dados fictícios que simulam os sistemas do banco
"""

from . import avaliacao, instrucoes
from .ciclo import Agente
from .conhecimento import BaseConhecimento
from .ferramentas import FERRAMENTAS_CARTAO, Ferramenta, ferramenta, selecionar
from .guardrails import Auditoria, Guardrails
from .memoria import Memoria

__all__ = ["Agente", "Memoria", "BaseConhecimento", "Guardrails", "Auditoria", "Ferramenta",
           "ferramenta", "selecionar", "FERRAMENTAS_CARTAO", "instrucoes", "avaliacao"]
