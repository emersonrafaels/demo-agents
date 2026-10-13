"""
guardrails.py — proteções que ficam FORA do modelo.

O modelo pode errar ou ser manipulado; por isso as regras críticas são verificadas em código,
antes de qualquer ação, e não dependem de o modelo "se comportar".
"""

import json
import re
from datetime import datetime

from ferramentas import CLIENTES, POLITICA

# 1) Entrada: tentativas de manipular o agente (prompt injection)
PADROES_INJECAO = [
    r"ignore (as|todas as)? ?(regras|instru)", r"desconsidere (as|suas) (regras|instru)",
    r"voc[eê] agora [eé]", r"modo (administrador|desenvolvedor)", r"sem aprova[cç][aã]o",
    r"transfira .* para a conta",
]


def detectar_instrucao_maliciosa(texto: str) -> list:
    return [p for p in PADROES_INJECAO if re.search(p, texto, flags=re.IGNORECASE)]


# 2) Ação: alçada — acima do limite, só com aprovação humana
def exige_aprovacao(nome_ferramenta: str, args: dict) -> bool:
    return nome_ferramenta == "abrir_estorno_provisorio" and float(args.get("valor", 0)) > POLITICA["alcada_agente"]


# 3) Ação: pré-condições — nenhuma ação antes de checar risco e política
PRE_REQUISITOS = {"analisar_risco_fraude", "consultar_politica"}


def pre_condicoes_ok(executadas: set, disponiveis: set) -> bool:
    return (PRE_REQUISITOS & disponiveis) <= executadas


# 4) Privacidade: mascara CPF e nomes completos antes de gravar logs (LGPD)
def mascarar(texto: str) -> str:
    texto = re.sub(r"\d{3}\.\d{3}\.\d{3}-\d{2}", "***.***.***-**", texto)
    for c in CLIENTES.values():
        texto = texto.replace(c["nome"], c["nome"].split()[0] + " ***")
    return texto


# 5) Rastreabilidade: cada decisão, ferramenta e resposta vira uma linha de auditoria
class Auditoria:
    def __init__(self, arquivo: str = "auditoria_agentes.jsonl"):
        self.arquivo = arquivo

    def registrar(self, agente: str, tipo: str, detalhe) -> None:
        evento = {"quando": datetime.now().isoformat(timespec="seconds"), "agente": agente, "tipo": tipo,
                  "detalhe": mascarar(json.dumps(detalhe, ensure_ascii=False, default=str))}
        with open(self.arquivo, "a", encoding="utf-8") as f:
            f.write(json.dumps(evento, ensure_ascii=False) + "\n")
