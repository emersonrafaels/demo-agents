"""
utils/conexao_iara.py — conexão com a Iara.

EM BRANCO DE PROPÓSITO: será implementada dentro do ambiente do banco.

Para funcionar com todas as demos, basta implementar a classe abaixo seguindo o mesmo contrato
das outras conexões (veja utils/base.py, conexao_anthropic.py e conexao_openai.py):

    entrada:  instrucoes (str), historico (formato neutro), ferramentas (lista com .nome, .descricao, .parametros)
    saída:    Resposta(texto, chamadas=[Chamada(id, nome, args)], bruto, tokens_entrada, tokens_saida)

Uso, depois de implementada:
    python 01_chatbot_vs_agente.py --provedor iara
"""

from __future__ import annotations

from .base import Provedor, Resposta


class ProvedorIara(Provedor):
    nome = "Iara"

    def __init__(self, modelo: str | None = None):
        # TODO: criar o cliente de acesso à Iara e definir o modelo
        raise NotImplementedError("A conexão com a Iara ainda não foi implementada (utils/conexao_iara.py).")

    def conversar(self, instrucoes, historico, ferramentas=None, max_tokens=1500) -> Resposta:
        # TODO: enviar instruções, histórico e ferramentas à Iara e devolver uma Resposta
        raise NotImplementedError
