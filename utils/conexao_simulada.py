"""
utils/conexao_simulada.py — provedor para ENSAIO offline (sem internet, sem chave e sem custo).

NÃO é um modelo de linguagem: segue regras fixas para que a apresentação possa ser ensaiada.
Ele imita, de propósito, o comportamento de um modelo "ingênuo": usa o que lhe é dado (memória,
ferramentas, conhecimento) e, quando não tem uma informação, responde com o que parece plausível.
Use --provedor claude ou gpt para ver um modelo de verdade decidindo.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .base import Chamada, Provedor, Resposta
from .console import brl


@dataclass
class _Politica:
    score_min: int = 70
    alcada: float | None = None          # None = não conhece a alçada
    max_contestacoes: int | None = None  # None = não conhece a regra de histórico


_CONSULTA_POLITICA = ("regras da política de contestação: bloqueio, estorno provisório, alçada e histórico "
                      "de contestações do cliente")


def _achar(padrao, texto, se_vazio=None, grupo=0):
    m = re.search(padrao, texto or "", flags=re.IGNORECASE)
    return m.group(grupo) if m else se_vazio


def _intencao(texto: str) -> str:
    t = texto.lower()
    if re.search(r"r\$\s?[\d.]+,\d{2}", t) and re.search(r"reconhe|contest|estorn|n[aã]o fi[zs]|n[aã]o fez", t):
        return "contestacao"
    if re.search(r"prazo|quanto tempo|quando|at[eé] quando|em quantos? dias", t):
        return "prazo"
    if re.search(r"\b(oi|ol[aá]|bom dia|boa tarde|boa noite)\b|sou (a|o) ", t):
        return "saudacao"
    return "outro"


class ProvedorSimulado(Provedor):
    nome = "Simulado"
    modelo = "regras locais (ensaio offline)"

    def __init__(self, modelo=None):
        self._n = 0

    # ------------------------------------------------------------------ entrada
    def conversar(self, instrucoes, historico, ferramentas=None, max_tokens=None) -> Resposta:
        nomes = [f.nome for f in ferramentas or []]
        i = max(k for k, h in enumerate(historico) if h["tipo"] == "usuario")
        pedido = historico[i]["texto"]
        res = {h["nome"]: json.loads(h["conteudo"]) for h in historico[i + 1:] if h["tipo"] == "resultado"}
        conversa = " ".join(h["texto"] for h in historico if h["tipo"] == "usuario")
        intencao = _intencao(pedido)

        if "Agente Revisor" in instrucoes:
            texto, ch = self._revisor(pedido), None
        elif "Agente de Atendimento" in instrucoes:
            texto, ch = self._atendimento(conversa), None
        elif any(n.startswith("agente_") for n in nomes):
            texto, ch = self._orquestrador(pedido, res, ferramentas)
        elif intencao == "contestacao" and "consultar_transacoes" in nomes:
            texto, ch = self._contestacao(pedido, conversa, res, nomes)
        elif "buscar_conhecimento" in nomes and intencao != "saudacao":
            texto, ch = self._conhecimento(pedido, conversa, res, intencao)
        else:
            texto, ch = self._conversa(pedido, conversa, intencao), None

        tok_in = len(instrucoes + json.dumps([h.get("texto") or h.get("conteudo") for h in historico])) // 4
        return Resposta(texto, [ch] if ch else [], None, tok_in, len(texto) // 4 + 20)

    def _chamar(self, texto, nome, **args):
        self._n += 1
        return texto, Chamada(f"sim_{self._n}", nome, args)

    @staticmethod
    def _nome_na_conversa(conversa):
        return _achar(r"sou (?:a |o )?([A-ZÁÉÍÓÚ][a-záéíóúãõç]+)", conversa, None, 1)

    @staticmethod
    def _com_nome(nome, frase):
        return f"{nome}, {frase[0].lower()}{frase[1:]}" if nome else frase

    # ------------------------------------------------------------------ só conversa (sem ferramentas)
    def _conversa(self, pedido, conversa, intencao):
        nome = self._nome_na_conversa(conversa)
        if intencao == "saudacao":
            return f"Olá{', ' + nome if nome else ''}! Sou o assistente de cartões. Como posso ajudar?"
        if intencao == "contestacao":
            return self._com_nome(nome, "Sinto muito pelo transtorno. Não tenho acesso a contas nem a sistemas, mas "
                                        "a contestação pode ser feita pelo app: Cartões > Fatura > selecione a compra > "
                                        "'Não reconheço'.")
        if intencao == "prazo":   # sem base de conhecimento: responde o que "parece" certo
            return self._com_nome(nome, "O valor costuma voltar em até 5 dias úteis, e você pode contestar compras "
                                        "em até 30 dias.")
        return "Entendido. Como posso ajudar?"

    # ------------------------------------------------------------------ busca de conhecimento
    @staticmethod
    def _ler_politica(r) -> _Politica:
        if not r:
            return _Politica()
        texto = " ".join(t["texto"] for t in r.get("trechos", []))
        alcada = _achar(r"at[eé] R\$ ?([\d.]+,\d{2})", texto, None, 1)
        return _Politica(
            score_min=int(_achar(r"igual ou superior a (\d+)", texto, 70, 1)),
            alcada=float(alcada.replace(".", "").replace(",", ".")) if alcada else None,
            max_contestacoes=int(_achar(r"mais de (\d+) contesta", texto, None, 1) or 0) or None,
        )

    def _conhecimento(self, pedido, conversa, res, intencao):
        if "buscar_conhecimento" not in res:
            consulta = (_CONSULTA_POLITICA
                        if intencao == "contestacao" else pedido)
            return self._chamar("Consulto a base de conhecimento antes de responder.", "buscar_conhecimento",
                                pergunta=consulta)
        trechos = res["buscar_conhecimento"].get("trechos", [])[: 3 if intencao == "contestacao" else 2]
        if not trechos:
            return "Não encontrei essa informação na base; vou verificar com a área responsável.", None
        frases = [t["texto"].split(". ")[0].rstrip(".") + "." for t in trechos]
        fontes = sorted({t["fonte"].split(" §")[0] for t in trechos})
        nome = self._nome_na_conversa(conversa)
        corpo = " ".join(frases)
        if intencao == "contestacao":
            corpo = "A política diz: " + corpo
        elif nome:
            corpo = f"{nome}, {corpo[0].lower()}{corpo[1:]}"
        return f"{corpo} (fonte: {', '.join(fontes)})", None

    # ------------------------------------------------------------------ contestação com ferramentas
    def _contestacao(self, pedido, conversa, res, nomes):
        chama = self._chamar
        nome_conversa = self._nome_na_conversa(conversa)
        for r in res.values():   # um guardrail negou acesso: não insiste
            if isinstance(r, dict) and "autenticado" in str(r.get("erro", "")):
                return ((f"{nome_conversa}, p" if nome_conversa else "P") + "or segurança, só consigo consultar e agir "
                        "sobre a conta do titular desta conversa. O titular pode contestar pelo app ou pela central."), None

        citados = re.findall(r"C-\d{4}", pedido)          # o último cliente citado na mensagem
        cid = citados[-1] if citados else _achar(r"C-\d{4}", conversa)
        if not cid:
            return "Para localizar a compra, preciso do seu código de cliente. Pode me informar?", None
        valor_txt = _achar(r"R\$\s?([\d.]+,\d{2})", pedido, None, 1)
        valor = float(valor_txt.replace(".", "").replace(",", ".")) if valor_txt else None

        if "buscar_cliente" not in res:
            return chama(f"Identifico o cliente {cid} e o cartão.", "buscar_cliente", cliente_id=cid)
        cli = res["buscar_cliente"]
        if "erro" in cli:
            return "Não localizei esse cliente. Pode confirmar o código?", None
        if "consultar_transacoes" not in res:
            return chama(f"Localizo a compra nas transações do cartão final {cli['cartao_final']}.",
                         "consultar_transacoes", cartao_final=cli["cartao_final"], dias=7)
        tx = next((t for t in res["consultar_transacoes"] if valor and abs(t["valor"] - valor) < .01), None)
        if not tx:
            return "Não localizei essa compra nos últimos 7 dias. Pode informar a data e a loja?", None
        if "analisar_risco_fraude" not in res:
            return chama(f"Encontrei {tx['loja']} em {tx['data']}. Avalio o risco de fraude.",
                         "analisar_risco_fraude", transacao_id=tx["id"])
        risco = res["analisar_risco_fraude"]
        if "buscar_conhecimento" in nomes and "buscar_conhecimento" not in res:
            return chama("Antes de agir, consulto a política na base de conhecimento.", "buscar_conhecimento",
                         pergunta=_CONSULTA_POLITICA)
        if "bloquear_cartao" not in nomes:      # especialista só de análise
            return (f"Transação {tx['id']} ({tx['loja']}, {brl(tx['valor'])}): score {risco['score']}/100. "
                    f"Sinais: {', '.join(risco['sinais']) or 'nenhum'}."), None

        pol = self._ler_politica(res.get("buscar_conhecimento"))
        alto = risco["score"] >= pol.score_min
        historico_ok = pol.max_contestacoes is None or cli["contestacoes_12m"] <= pol.max_contestacoes
        if alto and "bloquear_cartao" not in res:
            return chama(f"Score {risco['score']} indica fraude provável: bloqueio o cartão.",
                         "bloquear_cartao", cartao_final=cli["cartao_final"], motivo="suspeita de fraude")
        if alto and historico_ok and "abrir_estorno_provisorio" not in res:
            obs = (" (acima da alçada: o sistema deve pedir aprovação)" if pol.alcada and tx["valor"] > pol.alcada else "")
            return chama(f"Abro o estorno provisório{obs}.", "abrir_estorno_provisorio",
                         transacao_id=tx["id"], valor=tx["valor"])
        est = res.get("abrir_estorno_provisorio", {})
        if "registrar_protocolo" not in res:
            situacao = ("estorno provisório" if str(est.get("status", "")).startswith("ESTORNO")
                        else "proposta registrada" if "PROPOSTA" in str(est.get("status", ""))
                        else "encaminhado para análise")
            return chama("Registro o protocolo.", "registrar_protocolo", cliente_id=cid,
                         resumo=f"{tx['id']} score {risco['score']}: {situacao}")

        prot = res["registrar_protocolo"]["protocolo"]
        nome = nome_conversa or cli["nome"].split()[0]
        cartao, v = cli["cartao_final"], brl(tx["valor"])
        if str(est.get("status", "")).startswith("ESTORNO"):
            return (f"{nome}, bloqueei o cartão final {cartao} por segurança e abri um estorno provisório de {v}, "
                    f"que aparece na próxima fatura. Protocolo {prot}."), None
        if "PROPOSTA" in str(est.get("status", "")):
            return f"Análise concluída: proposta de estorno de {v} registrada para validação. Protocolo {prot}.", None
        if alto and "erro" in est:
            return (f"{nome}, bloqueei o cartão final {cartao} por segurança e encaminhei o estorno de {v} para "
                    f"aprovação de um especialista. Protocolo {prot}."), None
        if alto:
            return (f"{nome}, bloqueei o cartão final {cartao} por segurança e encaminhei sua contestação a um "
                    f"especialista, com a análise pronta. Protocolo {prot}."), None
        return (f"{nome}, a compra na {tx['loja']} não apresenta sinais de fraude. Registrei sua contestação "
                f"para análise de um especialista. Protocolo {prot}."), None

    # ------------------------------------------------------------------ multiagentes
    def _orquestrador(self, pedido, res, ferramentas):
        for f in ferramentas:
            if f.nome not in res:
                return self._chamar(f"Aciono {f.nome}.", f.nome, pedido=pedido)
        for r in res.values():
            if isinstance(r, dict) and r.get("resposta_cliente"):
                return r["resposta_cliente"], None
        return "Caso analisado pelos especialistas.", None

    @staticmethod
    def _atendimento(conversa):
        nome = _achar(r"Cliente: (\w+)", conversa, "Cliente", 1)
        cartao = _achar(r"cartão final (\d{4})", conversa, "****", 1)
        prot = _achar(r"2026-\d+", conversa, "a confirmar")
        return (f"{nome}, bloqueamos seu cartão final {cartao} por segurança e abrimos um estorno provisório da "
                f"compra, que aparece na próxima fatura. Protocolo {prot}.")

    @staticmethod
    def _revisor(texto):
        problemas = []
        if re.search(r"\d{3}\.\d{3}\.\d{3}-\d{2}|\bcpf\b", texto, re.I):
            problemas.append("expõe dado sensível (CPF)")
        if "definitivo" in texto.lower():
            problemas.append("promete estorno definitivo; a política só permite estorno provisório")
        if "protocolo" not in texto.lower():
            problemas.append("falta o número de protocolo")
        return json.dumps({"aprovado": not problemas, "problemas": problemas}, ensure_ascii=False)
