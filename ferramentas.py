"""
ferramentas.py — as "mãos" do agente: o que ele consegue consultar e fazer.

Cada ferramenta tem:
  • nome e descrição   → o modelo lê isso para decidir QUANDO usar
  • parametros         → JSON Schema: o modelo preenche os argumentos
  • funcao             → o código que roda de verdade (aqui, sobre dados FICTÍCIOS)
  • acao               → True se muda algo no mundo real (passa pelos guardrails)

Num ambiente real, cada função chamaria a API de um sistema do banco.
"""

from console import brl

# ------------------------------------------------------------------ dados fictícios
CLIENTES = {
    "C-1001": {"nome": "Mariana Souza", "cpf": "123.456.789-09", "segmento": "Uniclass",
               "cliente_desde": 2014, "contestacoes_12m": 0, "cartao": "4821"},
    "C-1002": {"nome": "Rafael Lima", "cpf": "987.654.321-00", "segmento": "Personnalité",
               "cliente_desde": 2009, "contestacoes_12m": 0, "cartao": "7730"},
    "C-1003": {"nome": "Paula Mendes", "cpf": "321.654.987-11", "segmento": "Uniclass",
               "cliente_desde": 2018, "contestacoes_12m": 0, "cartao": "5512"},
    "C-1004": {"nome": "Jorge Alves", "cpf": "456.789.123-22", "segmento": "Varejo",
               "cliente_desde": 2021, "contestacoes_12m": 0, "cartao": "3307"},
    "C-1005": {"nome": "Lucas Prado", "cpf": "654.321.987-33", "segmento": "Varejo",
               "cliente_desde": 2020, "contestacoes_12m": 3, "cartao": "9184"},
}

TRANSACOES = {
    "4821": [
        {"id": "TX-88190", "data": "08/10 12:41", "loja": "SUPERMERCADO BOM PRECO", "valor": 312.45,
         "canal": "presencial", "dispositivo_novo": False, "cidade": "São Paulo"},
        {"id": "TX-88213", "data": "10/10 03:12", "loja": "ELETRO MAX ONLINE", "valor": 1249.90,
         "canal": "e-commerce", "dispositivo_novo": True, "cidade": "Recife"},
        {"id": "TX-88227", "data": "10/10 19:05", "loja": "POSTO AVENIDA", "valor": 180.00,
         "canal": "presencial", "dispositivo_novo": False, "cidade": "São Paulo"},
    ],
    "7730": [{"id": "TX-90411", "data": "09/10 22:47", "loja": "VIAGENS PRIME ONLINE", "valor": 8900.00,
              "canal": "e-commerce", "dispositivo_novo": True, "cidade": "Lisboa"}],
    "5512": [{"id": "TX-91002", "data": "09/10 14:20", "loja": "FARMACIA SAUDE", "valor": 89.90,
              "canal": "presencial", "dispositivo_novo": False, "cidade": "São Paulo"}],
    "3307": [{"id": "TX-91120", "data": "10/10 02:41", "loja": "GAMES STORE DIGITAL", "valor": 459.00,
              "canal": "e-commerce", "dispositivo_novo": True, "cidade": "Manaus"}],
    "9184": [{"id": "TX-91388", "data": "10/10 04:05", "loja": "ELETRO MAX ONLINE", "valor": 640.00,
              "canal": "e-commerce", "dispositivo_novo": True, "cidade": "Fortaleza"}],
}

LOJAS_COM_ALERTA = {"ELETRO MAX ONLINE", "VIAGENS PRIME ONLINE", "GAMES STORE DIGITAL"}

POLITICA = {
    "nome": "Política de contestação de compras no cartão (fictícia)",
    "alcada_agente": 2000.00,
    "score_minimo": 70,
    "max_contestacoes_12m": 1,
    "regras": [
        "Estorno provisório permitido com score de risco >= 70.",
        "Até R$ 2.000,00 o agente pode abrir o estorno sozinho; acima disso, um analista aprova.",
        "Clientes com mais de 1 contestação nos últimos 12 meses: NÃO abrir estorno; encaminhar para análise humana.",
        "Com score >= 70, bloquear o cartão preventivamente.",
        "Com score < 70, não bloquear nem estornar: registrar protocolo e encaminhar para análise.",
    ],
}


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
    tx = next((t for lst in TRANSACOES.values() for t in lst if t["id"] == transacao_id), None)
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


def consultar_politica(tema: str = "contestacao") -> dict:
    return POLITICA


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
def _f(nome, descricao, propriedades, obrigatorios, funcao, acao=False, icone="🔧"):
    return {"nome": nome, "descricao": descricao, "funcao": funcao, "acao": acao, "icone": icone,
            "parametros": {"type": "object", "properties": propriedades, "required": obrigatorios}}


FERRAMENTAS = {
    "buscar_cliente": _f(
        "buscar_cliente",
        "Retorna o perfil do cliente: nome, segmento, ano de início do relacionamento, número de "
        "contestações nos últimos 12 meses e o final do cartão. Use primeiro, para descobrir qual "
        "cartão consultar.",
        {"cliente_id": {"type": "string", "description": "Identificador do cliente, ex.: C-1001"}},
        ["cliente_id"], buscar_cliente, icone="👤"),
    "consultar_transacoes": _f(
        "consultar_transacoes",
        "Lista as transações recentes de um cartão (id, data, loja, valor, canal, se o dispositivo é "
        "novo e cidade). Use para localizar a compra contestada pelo valor informado pelo cliente.",
        {"cartao_final": {"type": "string", "description": "Últimos 4 dígitos do cartão"},
         "dias": {"type": "integer", "description": "Janela de busca em dias (padrão 7)"}},
        ["cartao_final"], consultar_transacoes, icone="🔎"),
    "analisar_risco_fraude": _f(
        "analisar_risco_fraude",
        "Calcula um score de risco de fraude de 0 a 100 para uma transação e lista os sinais de "
        "alerta. Score >= 70 indica fraude provável.",
        {"transacao_id": {"type": "string", "description": "Id da transação, ex.: TX-88213"}},
        ["transacao_id"], analisar_risco_fraude, icone="🛡️ "),
    "consultar_politica": _f(
        "consultar_politica",
        "Retorna a política vigente de contestação: alçada do agente, score mínimo e regras. "
        "Consulte SEMPRE antes de bloquear cartão ou abrir estorno.",
        {"tema": {"type": "string", "description": "Tema da política; use 'contestacao'"}},
        [], consultar_politica, icone="📜"),
    "bloquear_cartao": _f(
        "bloquear_cartao",
        "AÇÃO: bloqueia o cartão preventivamente e solicita um novo. Use apenas quando o score de "
        "risco indicar fraude provável, conforme a política.",
        {"cartao_final": {"type": "string"}, "motivo": {"type": "string"}},
        ["cartao_final", "motivo"], bloquear_cartao, acao=True, icone="🔒"),
    "abrir_estorno_provisorio": _f(
        "abrir_estorno_provisorio",
        "AÇÃO: abre um estorno provisório do valor da transação na próxima fatura. Sujeito à alçada "
        "da política; acima dela o sistema pede aprovação humana automaticamente.",
        {"transacao_id": {"type": "string"}, "valor": {"type": "number"}},
        ["transacao_id", "valor"], abrir_estorno_provisorio, acao=True, icone="💸"),
    "registrar_protocolo": _f(
        "registrar_protocolo",
        "Registra o protocolo do atendimento com um resumo do que foi feito. Use ao final, antes de "
        "responder ao cliente.",
        {"cliente_id": {"type": "string"}, "resumo": {"type": "string"}},
        ["cliente_id", "resumo"], registrar_protocolo, icone="🗂️ "),
}


def selecionar(*nomes):
    """Entrega a um agente apenas as ferramentas de que ele precisa (permissão mínima)."""
    return [FERRAMENTAS[n] for n in nomes]


TODAS_CONTESTACAO = selecionar(*FERRAMENTAS)


def resumir(resultado) -> str:
    """Resumo curto de um resultado, para exibir no terminal."""
    if isinstance(resultado, list):
        n = len(resultado)
        return (f"{n} {'transação encontrada' if n == 1 else 'transações encontradas'}: "
                + "; ".join(f"{t['loja']} {brl(t['valor'])}" for t in resultado))
    if not isinstance(resultado, dict):
        return str(resultado)[:160]
    if "erro" in resultado:
        return f"⚠ {resultado['erro']}"
    if "score" in resultado:
        return f"score {resultado['score']}/100 • sinais: " + (", ".join(resultado["sinais"]) or "nenhum")
    if "regras" in resultado:
        return f"alçada do agente {brl(resultado['alcada_agente'])} • score mínimo {resultado['score_minimo']}"
    if "segmento" in resultado:
        return (f"{resultado['nome']} • {resultado['segmento']} • cliente desde {resultado['cliente_desde']} "
                f"• {resultado['contestacoes_12m']} contestações em 12 meses")
    if "protocolo" in resultado:
        return f"protocolo {resultado['protocolo']}"
    if "resposta" in resultado:
        return str(resultado["resposta"])[:200]
    return " • ".join(f"{k}: {brl(v) if k == 'valor' else v}" for k, v in resultado.items())
