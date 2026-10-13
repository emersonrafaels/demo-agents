"""
DEMO 00 — Teste de conexão (rode antes da apresentação)

Faz uma chamada mínima a cada provedor configurado e mostra modelo, tempo e tokens.

Executar:  python 00_teste_conexao.py
"""

import os
import time

from console import C, titulo
from llm import ProvedorClaude, ProvedorGPT

titulo("Teste de conexão com as APIs")
for nome, classe, chave in [("Claude", ProvedorClaude, "ANTHROPIC_API_KEY"), ("GPT", ProvedorGPT, "OPENAI_API_KEY")]:
    if not os.getenv(chave):
        print(f"  {C.CINZA}{nome:<7} — {chave} não definida, pulando{C.FIM}")
        continue
    try:
        p = classe()
        t = time.time()
        r = p.conversar("Responda apenas: OK", [{"tipo": "usuario", "texto": "Teste de conexão."}])
        print(f"  {C.VERDE}✓ {nome:<7}{C.FIM} modelo {p.modelo} • {time.time() - t:.1f}s • "
              f"{r.tokens_entrada + r.tokens_saida} tokens • resposta: {r.texto[:40]!r}")
    except Exception as e:
        print(f"  {C.VERMELHO}✕ {nome:<7}{C.FIM} {type(e).__name__}: {str(e)[:160]}")
print(f"\n{C.CINZA}Sem chave? Todas as demos rodam com --provedor simulado para ensaio offline.{C.FIM}\n")
