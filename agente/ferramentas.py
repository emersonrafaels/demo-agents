"""
agente/ferramentas.py — as "mãos" do agente: o que ele consegue consultar e fazer.

Cada ferramenta tem:
  • nome e descrição   → o modelo lê isso para decidir QUANDO usar
  • parametros         → JSON Schema: o modelo preenche os argumentos
  • funcao             → o código que roda de verdade (aqui, sobre dados fictícios)
  • acao               → True se muda algo no mundo real (passa pelos guardrails de ação)

Num ambiente real, cada função chamaria a API de um sistema do banco.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from utils.console import brl

from .dados import CLIENTES, LOJAS_COM_ALERTA, TRANSACOES, buscar_transacao


@dataclass
class Ferramenta:
    nome: str
    descricao: str
    parametros: dict
    funcao: Callable
    acao: bool = False
    icone: str = "🔧"


def ferramenta(nome, descricao, propriedades, obrigatorios, funcao, acao=False, icone="🔧") -> Ferramenta:
    return Ferramenta(nome, descricao, {"type": "object", "properties": propriedades, "required": obrigatorios},
                      funcao, acao, icone)


# ------------------------------------------------------------------ funções (o que roda de verdade)
_protocolo = [48213]


def buscar_cliente(cliente_id: str) -> dict:
    c = CLIENTES.get(cliente_id)
    if not c:
        return {"erro": f"cliente {cliente_id} não encontrado"}
    return {"cliente_id": cliente_id, "nome": c["nome"], "segmento": c["segmento"],
            "cliente_desde": c["cliente_desde"], "contestacoes_12m": c["contestacoes_12m"],
            "cartao_final": c["cartao"]}


def consultar_transacoes(cartao_final: str, dias: int = 7) -> list:
    return TRANSACOES.get(str(cartao_final), [])


def analisar_risco_fraude(transacao_id: str) -> dict:
    tx = buscar_transacao(transacao_id)
    if not tx:
        return {"erro": f"transação {transacao_id} não encontrada"}
    sinais, score = [], 20
    if tx["dispositivo_novo"]:
        sinais.append("dispositivo nunca usado pelo cliente"); score += 25
    if int(tx["data"].split()[1][:2]) < 6:
        sinais.append("horário atípico (madrugada)"); score += 15
    if tx["loja"] in LOJAS_COM_ALERTA:
        sinais.append("estabelecimento com alertas recentes"); score += 20
    if tx["cidade"] != "São Paulo":
        sinais.append(f"fora do padrão geográfico ({tx['cidade']})"); score += 7
    return {"transacao_id": transacao_id, "valor": tx["valor"], "score": min(score, 99), "sinais": sinais}


def bloquear_cartao(cartao_final: str, motivo: str) -> dict:
    return {"cartao_final": cartao_final, "status": "BLOQUEADO", "motivo": motivo,
            "novo_cartao": "enviado em até 5 dias úteis"}


def abrir_estorno_provisorio(transacao_id: str, valor: float) -> dict:
    return {"transacao_id": transacao_id, "valor": valor, "status": "ESTORNO PROVISÓRIO CRIADO",
            "credito": "na próxima fatura"}


def registrar_protocolo(cliente_id: str, resumo: str) -> dict:
    _protocolo[0] += 1
    return {"protocolo": f"2026-{_protocolo[0]}", "cliente_id": cliente_id, "resumo": resumo}


# ------------------------------------------------------------------ catálogo entregue ao modelo
CATALOGO = {f.nome: f for f in [
    ferramenta(
        "buscar_cliente",
        "Retorna o perfil do cliente: nome, segmento, ano de início do relacionamento, número de "
        "contestações nos últimos 12 meses e o final do cartão. Use primeiro, para descobrir qual "
        "cartão consultar.",
        {"cliente_id": {"type": "string", "description": "Identificador do cliente, ex.: C-1001"}},
        ["cliente_id"], buscar_cliente, icone="👤"),
    ferramenta(
        "consultar_transacoes",
        "Lista as transações recentes de um cartão (id, data, loja, valor, canal, se o dispositivo é "
        "novo e cidade). Use para localizar a compra contestada pelo valor informado pelo cliente.",
        {"cartao_final": {"type": "string", "description": "Últimos 4 dígitos do cartão"},
         "dias": {"type": "integer", "description": "Janela de busca em dias (padrão 7)"}},
        ["cartao_final"], consultar_transacoes, icone="🔎"),
    ferramenta(
        "analisar_risco_fraude",
        "Calcula um score de risco de fraude de 0 a 100 para uma transação e lista os sinais de "
        "alerta. Score >= 70 indica fraude provável.",
        {"transacao_id": {"type": "string", "description": "Id da transação, ex.: TX-88213"}},
        ["transacao_id"], analisar_risco_fraude, icone="🛡️ "),
    ferramenta(
        "bloquear_cartao",
        "AÇÃO: bloqueia o cartão preventivamente e solicita um novo. Use quando houver fraude provável.",
        {"cartao_final": {"type": "string"}, "motivo": {"type": "string"}},
        ["cartao_final", "motivo"], bloquear_cartao, acao=True, icone="🔒"),
    ferramenta(
        "abrir_estorno_provisorio",
        "AÇÃO: abre um estorno provisório do valor da transação na próxima fatura. Acima da alçada, "
        "chame normalmente: o sistema encaminha para aprovação humana.",
        {"transacao_id": {"type": "string"}, "valor": {"type": "number"}},
        ["transacao_id", "valor"], abrir_estorno_provisorio, acao=True, icone="💸"),
    ferramenta(
        "registrar_protocolo",
        "Registra o protocolo do atendimento com um resumo do que foi feito. Use ao final de uma "
        "contestação, antes de responder ao cliente.",
        {"cliente_id": {"type": "string"}, "resumo": {"type": "string"}},
        ["cliente_id", "resumo"], registrar_protocolo, icone="🗂️ "),
]}

FERRAMENTAS_CARTAO = list(CATALOGO.values())


def selecionar(*nomes) -> list[Ferramenta]:
    """Entrega a um agente apenas as ferramentas de que ele precisa (permissão mínima)."""
    return [CATALOGO[n] for n in nomes]


def resumir(resultado) -> str:
    """Resumo curto de um resultado de ferramenta, para exibir no terminal."""
    if isinstance(resultado, list):
        n = len(resultado)
        return (f"{n} {'transação encontrada' if n == 1 else 'transações encontradas'}: "
                + "; ".join(f"{t['loja']} {brl(t['valor'])}" for t in resultado))
    if not isinstance(resultado, dict):
        return str(resultado)[:160]
    if "erro" in resultado:
        return f"⚠ {resultado['erro']}"
    if "trechos" in resultado:
        return f"{len(resultado['trechos'])} trechos: " + " • ".join(t["fonte"] for t in resultado["trechos"])
    if "score" in resultado:
        return f"score {resultado['score']}/100 • sinais: " + (", ".join(resultado["sinais"]) or "nenhum")
    if "segmento" in resultado:
        return (f"{resultado['nome']} • {resultado['segmento']} • cliente desde {resultado['cliente_desde']} "
                f"• {resultado['contestacoes_12m']} contestações em 12 meses")
    if "protocolo" in resultado:
        return f"protocolo {resultado['protocolo']}"
    if "resposta" in resultado:
        return str(resultado["resposta"])[:200]
    return " • ".join(f"{k}: {brl(v) if k == 'valor' else v}" for k, v in resultado.items())
