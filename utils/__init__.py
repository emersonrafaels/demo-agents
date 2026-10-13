"""
utils — conexões com os modelos de linguagem e utilidades de console.

    from utils import criar_provedor
    llm = criar_provedor("claude")     # "claude" | "gpt" | "iara" | "simulado"
"""

from __future__ import annotations

import os
from pathlib import Path

from .base import Chamada, Provedor, Resposta

ARQUIVO_ENV = Path(__file__).resolve().parent.parent / ".env"


def carregar_env(caminho: Path = ARQUIVO_ENV) -> None:
    """Carrega o .env da raiz do projeto. Variáveis já definidas no terminal têm prioridade."""
    if not caminho.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(caminho, override=False)
        return
    except ImportError:
        pass
    # sem python-dotenv: leitura simples de linhas CHAVE=valor
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.removeprefix("export ").split("=", 1)
        valor = valor.split(" #", 1)[0].strip().strip("'\"")
        os.environ.setdefault(chave.strip(), valor)


carregar_env()

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
        raise SystemExit(f"Defina {chave} no arquivo .env (ou rode com --provedor simulado).")

    mod = __import__(f"utils.{modulo}", fromlist=[classe])
    try:
        return getattr(mod, classe)(modelo)
    except NotImplementedError as e:
        raise SystemExit(f"{e} Use --provedor claude, gpt ou simulado por enquanto.")


__all__ = ["Chamada", "Provedor", "Resposta", "criar_provedor", "PROVEDORES"]
