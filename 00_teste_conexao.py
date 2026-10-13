"""
DEMO 00 — Teste de conexão (rode antes da apresentação)

Faz uma chamada mínima a cada conexão de utils/ e mostra modelo, tempo e tokens.

Executar:  python 00_teste_conexao.py
"""

import time

from utils import PROVEDORES, criar_provedor
from utils.console import C, titulo

titulo("Teste de conexão com as APIs")
for nome in ["claude", "gpt", "iara"]:
    arquivo = f"utils/{PROVEDORES[nome][0]}.py"
    try:
        p = criar_provedor(nome)
    except SystemExit as e:
        print(f"  {C.CINZA}– {nome:<7} {e}  [{arquivo}]{C.FIM}")
        continue
    try:
        t = time.time()
        r = p.conversar("Responda apenas: OK", [{"tipo": "usuario", "texto": "Teste de conexão."}])
        print(f"  {C.VERDE}✓ {p.nome:<7}{C.FIM} modelo {p.modelo} • {time.time() - t:.1f}s • "
              f"{r.tokens_entrada + r.tokens_saida} tokens • resposta: {r.texto[:40]!r}")
    except Exception as e:
        print(f"  {C.VERMELHO}✕ {p.nome:<7}{C.FIM} {type(e).__name__}: {str(e)[:160]}")
print(f"\n{C.CINZA}Sem chave? Todas as demos rodam com --provedor simulado para ensaio offline.{C.FIM}\n")
