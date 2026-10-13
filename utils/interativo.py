"""
utils/interativo.py — o "palco" das demos: o apresentador digita como cliente e o agente responde ao vivo.

    try:
        while True:
            texto = perguntar("Cliente", SUGESTOES)     # número → usa a sugestão; /sair ou Ctrl+C → Encerrar
            if comando(texto) ...                        # /comandos são tratados pela própria demo
            ao_vivo(agente.conversar, texto)             # erro de rede ou Ctrl+C não derruba a demo
    except Encerrar:
        ...                                              # placar final
"""

from __future__ import annotations

import re
import subprocess
import sys
import time
import traceback
import webbrowser
from pathlib import Path

from .console import C, FLAGS

try:
    sys.stdin.reconfigure(encoding="utf-8")
except Exception:
    pass

SAIR = {"/sair", "/fim", "/q", "sair"}
CLIENTE_ID = re.compile(r"C-\d{4}", re.I)


class Encerrar(Exception):
    """O apresentador pediu para encerrar a demo (/sair, Ctrl+C ou fim da entrada)."""


def perguntar(rotulo: str, sugestoes=(), cor: str = C.AZUL) -> str:
    """Lê uma linha do apresentador. Um número escolhe a sugestão correspondente."""
    while True:
        try:
            texto = input(f"\n{cor}{C.NEGRITO}{rotulo} ›{C.FIM} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            raise Encerrar
        if not texto:
            continue
        if texto.lower() in SAIR:
            raise Encerrar
        if texto.isdigit() and 1 <= int(texto) <= len(sugestoes):
            texto = sugestoes[int(texto) - 1]
            print(f"  {C.CINZA}↳ {texto}{C.FIM}")
        return texto


def confirmar(pergunta: str, padrao: bool = False) -> bool:
    opcoes = "S/n" if padrao else "s/N"
    try:
        r = input(f"  {C.NEGRITO}{pergunta} ({opcoes}): {C.FIM}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return padrao
    return padrao if not r else r.startswith("s")


def mostrar_sugestoes(sugestoes, titulo: str = "Mensagens prontas (digite o número)") -> None:
    print(f"\n  {C.CINZA}{titulo}:{C.FIM}")
    for i, s in enumerate(sugestoes, 1):
        print(f"   {C.LARANJA}{C.NEGRITO}{i}{C.FIM}  {s}")


def mostrar_comandos(comandos: dict) -> None:
    print(f"\n  {C.CINZA}Comandos:{C.FIM}")
    for nome, descricao in comandos.items():
        print(f"   {C.ROXO}{nome:<16}{C.FIM} {C.CINZA}{descricao}{C.FIM}")
    print(f"   {C.ROXO}{'/sair':<16}{C.FIM} {C.CINZA}encerra e mostra o resumo{C.FIM}")


def argumento(texto: str) -> str:
    """'/alcada 5000' → '5000'."""
    return texto.split(maxsplit=1)[1].strip() if " " in texto.strip() else ""


def ler_cliente(texto: str) -> str | None:
    m = CLIENTE_ID.search(texto or "")
    return m.group(0).upper() if m else None


def ao_vivo(funcao, *args, **kwargs):
    """Executa uma chamada ao agente sem derrubar a demo: Ctrl+C interrompe só esta mensagem."""
    try:
        return funcao(*args, **kwargs)
    except KeyboardInterrupt:
        print(f"\n  {C.CINZA}(interrompido — pode mandar outra mensagem){C.FIM}")
    except Encerrar:
        raise
    except Exception as e:
        print(f"\n  {C.VERMELHO}✕ {type(e).__name__}: {str(e)[:300]}{C.FIM}")
        print(f"  {C.CINZA}A demo continua; tente de novo ou use --provedor simulado.{C.FIM}")
        if "--debug" in FLAGS:
            traceback.print_exc()
    return None


def abrir_web(pagina: str = "") -> None:
    """Abre o app web (streamlit_app.py) direto na página da demo e encerra a versão de terminal.

    As opções da linha de comando (ex.: --provedor claude) seguem para o app; a porta sai de --porta (8501).
    """
    from .console import opcao
    porta = opcao("porta", "8501")
    app = Path(__file__).resolve().parent.parent / "streamlit_app.py"
    args = [a for a in sys.argv[1:] if a != "--web"]
    servidor = subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(app), "--server.port", porta,
                                 "--", *args], cwd=app.parent)      # na raiz, para ler .streamlit/config.toml
    time.sleep(3)
    webbrowser.open(f"http://localhost:{porta}/{pagina}")
    print(f"App no navegador: http://localhost:{porta}/{pagina}  (Ctrl+C encerra)")
    try:
        servidor.wait()
    except KeyboardInterrupt:
        servidor.terminate()
    raise SystemExit
