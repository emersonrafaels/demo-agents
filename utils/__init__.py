"""
utils — conexões com os modelos de linguagem e utilidades de console.

    from utils import criar_provedor
    llm = criar_provedor("claude")     # "claude" | "gpt" | "iara" | "simulado"
"""

from __future__ import annotations

import os

from .base import Chamada, Provedor, Resposta

PROVEDORES = {
    "claude": ("conexao_anthropic", "ProvedorClaude", "ANTHROPIC_API_KEY", "anthropic"),
    "gpt": ("conexao_openai", "ProvedorGPT", "OPENAI_API_KEY", "openai"),
    "iara": ("conexao_iara", "ProvedorIara", None, None),
    "simulado": ("conexao_simulada", "ProvedorSimulado", None, None),
}


def criar_provedor(nome: str | None = None, modelo: str | None = None) -> Provedor:
    """Cria a conexão pedida. Sem nome: usa PROVEDOR do ambiente ou a primeira chave configurada."""
    nome = (nome or os.getenv("PROVEDOR") or "").lower()
    if not nome:
        nome = "claude" if os.getenv("ANTHROPIC_API_KEY") else "gpt" if os.getenv("OPENAI_API_KEY") else "simulado"
    nome = {"openai": "gpt", "anthropic": "claude"}.get(nome, nome)
    if nome not in PROVEDORES:
        raise SystemExit(f"Provedor desconhecido: {nome}. Use {', '.join(PROVEDORES)}.")

    modulo, classe, chave, pacote = PROVEDORES[nome]
    if pacote:
        try:
            __import__(pacote)
        except ImportError:
            raise SystemExit(f"Instale o SDK:  pip install {pacote}")
    if chave and not os.getenv(chave):
        raise SystemExit(f"Defina a variável de ambiente {chave} (ou rode com --provedor simulado).")

    mod = __import__(f"utils.{modulo}", fromlist=[classe])
    try:
        return getattr(mod, classe)(modelo)
    except NotImplementedError as e:
        raise SystemExit(f"{e} Use --provedor claude, gpt ou simulado por enquanto.")


__all__ = ["Chamada", "Provedor", "Resposta", "criar_provedor", "PROVEDORES"]
