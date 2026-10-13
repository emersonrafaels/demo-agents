"""utils/console.py — cores, efeito de digitação e opções de linha de comando das demos."""

import os
import sys
import time

if os.name == "nt":  # habilita cores ANSI no terminal do Windows
    os.system("")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def opcao(nome: str, padrao: str | None = None) -> str | None:
    """Lê --nome valor ou --nome=valor da linha de comando."""
    for i, a in enumerate(sys.argv):
        if a == f"--{nome}" and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        if a.startswith(f"--{nome}="):
            return a.split("=", 1)[1]
    return padrao


FLAGS = set(sys.argv[1:])
RAPIDO = "--rapido" in FLAGS        # sem efeito de digitação
PASSO = "--passo" in FLAGS          # ENTER a cada etapa (modo apresentador)
SEM_COR = "--sem-cor" in FLAGS or not sys.stdout.isatty()


class C:
    AZUL = "" if SEM_COR else "\033[38;5;33m"
    LARANJA = "" if SEM_COR else "\033[38;5;208m"
    VERDE = "" if SEM_COR else "\033[38;5;35m"
    VERMELHO = "" if SEM_COR else "\033[38;5;203m"
    ROXO = "" if SEM_COR else "\033[38;5;141m"
    CINZA = "" if SEM_COR else "\033[38;5;246m"
    NEGRITO = "" if SEM_COR else "\033[1m"
    FIM = "" if SEM_COR else "\033[0m"


def digitar(texto: str, cor: str = "", velocidade: float = 0.006) -> None:
    if RAPIDO:
        print(f"{cor}{texto}{C.FIM}")
        return
    sys.stdout.write(cor)
    for ch in texto:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(velocidade)
    sys.stdout.write(C.FIM + "\n")


def pausa(segundos: float = 0.4) -> None:
    if PASSO:
        input(f"{C.CINZA}   [ENTER para continuar]{C.FIM}")
    elif not RAPIDO:
        time.sleep(segundos)


def titulo(texto: str) -> None:
    linha = "═" * (len(texto) + 4)
    print(f"\n{C.AZUL}{C.NEGRITO}╔{linha}╗\n║  {texto}  ║\n╚{linha}╝{C.FIM}")


def secao(texto: str) -> None:
    print(f"\n{C.LARANJA}{C.NEGRITO}── {texto} {'─' * max(4, 62 - len(texto))}{C.FIM}")


def etapa(etiqueta: str, cor: str, texto: str, recuo: str = "  ") -> None:
    digitar(f"{recuo}{cor}{C.NEGRITO}{etiqueta:<11}{C.FIM} {texto}")


def brl(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
