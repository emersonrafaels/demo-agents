"""
agente/dados.py — dados FICTÍCIOS que simulam os sistemas do banco (clientes, cartões e transações).
"""

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


def buscar_transacao(transacao_id: str) -> dict | None:
    return next((t for lst in TRANSACOES.values() for t in lst if t["id"] == transacao_id), None)


def dono_do_cartao(cartao_final: str) -> str | None:
    return next((cid for cid, c in CLIENTES.items() if c["cartao"] == str(cartao_final)), None)


def dono_da_transacao(transacao_id: str) -> str | None:
    cartao = next((c for c, lst in TRANSACOES.items() if any(t["id"] == transacao_id for t in lst)), None)
    return dono_do_cartao(cartao) if cartao else None


def dono_dos_dados(args: dict) -> str | None:
    """A quem pertencem os dados que uma chamada de ferramenta quer acessar."""
    if args.get("cliente_id"):
        return args["cliente_id"]
    if args.get("cartao_final"):
        return dono_do_cartao(args["cartao_final"])
    if args.get("transacao_id"):
        return dono_da_transacao(args["transacao_id"])
    return None
