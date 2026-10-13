"""
utils/base.py — o contrato comum a todas as conexões com modelos de linguagem.

Cada fornecedor (Anthropic, OpenAI, Iara...) tem seu próprio formato de API. Para o resto do código
não precisar saber disso, toda conexão implementa a mesma interface:

    provedor.conversar(instrucoes, historico, ferramentas) -> Resposta

Histórico neutro (igual para qualquer provedor):
    {"tipo": "usuario",    "texto": "..."}
    {"tipo": "assistente", "texto": "...", "chamadas": [Chamada, ...], "bruto": <resposta original>, "provedor": "Claude"}
    {"tipo": "resultado",  "id": "...", "nome": "...", "conteudo": "<json>"}

Ferramentas: objetos com os atributos .nome, .descricao e .parametros (JSON Schema).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Chamada:
    """Pedido do modelo para executar uma ferramenta."""
    id: str
    nome: str
    args: dict


@dataclass
class Resposta:
    texto: str
    chamadas: list = field(default_factory=list)
    bruto: object = None
    tokens_entrada: int = 0
    tokens_saida: int = 0


class Provedor(ABC):
    """Interface que toda conexão com LLM implementa."""

    nome: str = "base"
    modelo: str = ""

    @abstractmethod
    def conversar(self, instrucoes: str, historico: list, ferramentas: list | None = None,
                  max_tokens: int = 1500) -> Resposta:
        """Envia instruções + histórico (+ ferramentas) ao modelo e devolve texto e pedidos de ferramenta."""
