"""
llm.py — o "cérebro" do agente: chamadas REAIS às APIs do Claude (Anthropic) e do GPT (OpenAI).

As duas APIs fazem a mesma coisa (o modelo lê a conversa e pode pedir para chamar ferramentas),
mas com formatos diferentes. Este arquivo esconde essas diferenças atrás de uma interface única:

    provedor.conversar(instrucoes, historico, ferramentas) -> Resposta(texto, chamadas, tokens)

Histórico neutro (o mesmo para qualquer provedor):
    {"tipo": "usuario",    "texto": "..."}
    {"tipo": "assistente", "texto": "...", "chamadas": [Chamada, ...], "bruto": <resposta original>}
    {"tipo": "resultado",  "id": "...", "nome": "...", "conteudo": "<json>"}

Configuração por variáveis de ambiente:
    ANTHROPIC_API_KEY   chave do Claude          MODELO_CLAUDE  (padrão: claude-sonnet-5-5)
    OPENAI_API_KEY      chave do GPT             MODELO_GPT     (padrão: gpt-5.6)
    OPENAI_BASE_URL     opcional, para gateways/proxies compatíveis com a API da OpenAI
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field


@dataclass
class Chamada:
    """Pedido do modelo para executar uma ferramenta."""
    id: str
    nome: str
    args: dict


@dataclass
class Resposta:
    texto: str
    chamadas: list = field(default_factory=list)
    bruto: object = None
    tokens_entrada: int = 0
    tokens_saida: int = 0


# =====================================================================================
# Claude — API Messages da Anthropic
# =====================================================================================
class ProvedorClaude:
    nome = "Claude"

    def __init__(self, modelo: str | None = None):
        import anthropic                                   # pip install anthropic
        self.cliente = anthropic.Anthropic()               # lê ANTHROPIC_API_KEY do ambiente
        self.modelo = modelo or os.getenv("MODELO_CLAUDE", "claude-sonnet-5-5")

    def conversar(self, instrucoes, historico, ferramentas=None, max_tokens=1500) -> Resposta:
        params = dict(model=self.modelo, max_tokens=max_tokens, system=instrucoes,
                      messages=self._mensagens(historico))
        if ferramentas:
            params["tools"] = [{"name": f["nome"], "description": f["descricao"],
                                "input_schema": f["parametros"]} for f in ferramentas]
        r = self.cliente.messages.create(**params)

        texto = "".join(b.text for b in r.content if b.type == "text")
        chamadas = [Chamada(b.id, b.name, dict(b.input)) for b in r.content if b.type == "tool_use"]
        return Resposta(texto.strip(), chamadas, r.content, r.usage.input_tokens, r.usage.output_tokens)

    @staticmethod
    def _mensagens(historico):
        msgs = []
        for h in historico:
            if h["tipo"] == "usuario":
                msgs.append({"role": "user", "content": h["texto"]})
            elif h["tipo"] == "assistente":
                # devolvemos a resposta original do Claude (inclui blocos de raciocínio, se houver)
                conteudo = h.get("bruto") if h.get("provedor") == "Claude" else None
                if conteudo is None:
                    conteudo = ([{"type": "text", "text": h["texto"]}] if h["texto"] else []) + [
                        {"type": "tool_use", "id": c.id, "name": c.nome, "input": c.args} for c in h["chamadas"]]
                msgs.append({"role": "assistant", "content": conteudo})
            elif h["tipo"] == "resultado":
                bloco = {"type": "tool_result", "tool_use_id": h["id"], "content": h["conteudo"]}
                anterior = msgs[-1] if msgs else None
                if anterior and anterior["role"] == "user" and isinstance(anterior["content"], list):
                    anterior["content"].append(bloco)       # vários resultados → uma única mensagem
                else:
                    msgs.append({"role": "user", "content": [bloco]})
        return msgs


# =====================================================================================
# GPT — API Chat Completions da OpenAI
# =====================================================================================
class ProvedorGPT:
    nome = "GPT"

    def __init__(self, modelo: str | None = None):
        import openai                                       # pip install openai
        self.cliente = openai.OpenAI()                      # lê OPENAI_API_KEY (e OPENAI_BASE_URL)
        self.modelo = modelo or os.getenv("MODELO_GPT", "gpt-5.6")

    def conversar(self, instrucoes, historico, ferramentas=None, max_tokens=1500) -> Resposta:
        params = dict(model=self.modelo, messages=self._mensagens(instrucoes, historico))
        if ferramentas:
            params["tools"] = [{"type": "function", "function": {
                "name": f["nome"], "description": f["descricao"], "parameters": f["parametros"]}}
                for f in ferramentas]
        r = self.cliente.chat.completions.create(**params)

        msg = r.choices[0].message
        chamadas = [Chamada(tc.id, tc.function.name, json.loads(tc.function.arguments or "{}"))
                    for tc in (msg.tool_calls or [])]
        uso = r.usage
        return Resposta((msg.content or "").strip(), chamadas, msg,
                        getattr(uso, "prompt_tokens", 0), getattr(uso, "completion_tokens", 0))

    @staticmethod
    def _mensagens(instrucoes, historico):
        msgs = [{"role": "system", "content": instrucoes}]
        for h in historico:
            if h["tipo"] == "usuario":
                msgs.append({"role": "user", "content": h["texto"]})
            elif h["tipo"] == "assistente":
                m = {"role": "assistant", "content": h["texto"] or None}
                if h["chamadas"]:
                    m["tool_calls"] = [{"id": c.id, "type": "function", "function": {
                        "name": c.nome, "arguments": json.dumps(c.args, ensure_ascii=False)}}
                        for c in h["chamadas"]]
                msgs.append(m)
            elif h["tipo"] == "resultado":
                msgs.append({"role": "tool", "tool_call_id": h["id"], "content": h["conteudo"]})
        return msgs


# =====================================================================================
# Simulado — para ENSAIO offline (sem internet e sem custo). Não é um LLM: segue regras.
# =====================================================================================
class ProvedorSimulado:
    nome = "Simulado"
    modelo = "regras locais (ensaio offline)"

    def __init__(self, modelo=None):
        self._n = 0

    def _id(self):
        self._n += 1
        return f"sim_{self._n}"

    def conversar(self, instrucoes, historico, ferramentas=None, max_tokens=None) -> Resposta:
        pedido = next(h["texto"] for h in historico if h["tipo"] == "usuario")
        ultimo = [h for h in historico if h["tipo"] == "usuario"][-1]["texto"]
        res = {h["nome"]: json.loads(h["conteudo"]) for h in historico if h["tipo"] == "resultado"}
        nomes = [f["nome"] for f in ferramentas or []]
        tok = len(instrucoes + json.dumps([h.get("texto") or h.get("conteudo") for h in historico])) // 4

        if "consultar_transacoes" in nomes:
            texto, ch = self._contestacao(pedido, res, nomes)
        elif nomes:
            texto, ch = self._generico(pedido, res, ferramentas)
        else:
            todos = " ".join(h["texto"] for h in historico if h["tipo"] == "usuario")
            texto, ch = self._sem_ferramentas(instrucoes, ultimo, todos), None
        return Resposta(texto, [ch] if ch else [], None, tok, len(texto) // 4 + 20)

    # --- regras do caso de contestação
    def _contestacao(self, pedido, res, nomes):
        cid = _achar(r"C-\d{4}", pedido, "C-0000")
        m = re.search(r"R\$\s?([\d.]+,\d{2})", pedido)
        valor = float(m.group(1).replace(".", "").replace(",", ".")) if m else None
        chama = lambda t, n, **a: (t, Chamada(self._id(), n, a))
        if "buscar_cliente" not in res:
            return chama("Primeiro identifico o cliente e o cartão.", "buscar_cliente", cliente_id=cid)
        cli = res["buscar_cliente"]
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
        if "consultar_politica" not in nomes:
            return (f"Transação {tx['id']} ({tx['loja']}, {tx['valor']:.2f}): score {risco['score']}/100. "
                    f"Sinais: {', '.join(risco['sinais']) or 'nenhum'}."), None
        if "consultar_politica" not in res:
            return chama("Antes de qualquer ação, confiro a política.", "consultar_politica", tema="contestacao")
        pol = res["consultar_politica"]
        alto = risco["score"] >= pol["score_minimo"]
        hist_ok = cli["contestacoes_12m"] <= pol["max_contestacoes_12m"]
        if alto and "bloquear_cartao" in nomes and "bloquear_cartao" not in res:
            return chama(f"Score {risco['score']} indica fraude provável: bloqueio o cartão.",
                         "bloquear_cartao", cartao_final=cli["cartao_final"], motivo="suspeita de fraude")
        if alto and hist_ok and "abrir_estorno_provisorio" not in res:
            return chama("A política permite o estorno provisório.", "abrir_estorno_provisorio",
                         transacao_id=tx["id"], valor=tx["valor"])
        if "registrar_protocolo" not in res:
            est = res.get("abrir_estorno_provisorio", {})
            resumo = f"{tx['id']} score {risco['score']}: " + ("estorno" if "status" in est else "encaminhado")
            return chama("Registro o protocolo.", "registrar_protocolo", cliente_id=cid, resumo=resumo)
        nome, prot = cli["nome"].split()[0], res["registrar_protocolo"]["protocolo"]
        est = res.get("abrir_estorno_provisorio", {})
        if str(est.get("status", "")).startswith("ESTORNO"):
            return (f"{nome}, bloqueei o cartão final {cli['cartao_final']} por segurança e abri um estorno "
                    f"provisório da compra na {tx['loja']}, que aparece na próxima fatura. Protocolo {prot}."), None
        if alto:
            return (f"{nome}, bloqueei o cartão final {cli['cartao_final']} por segurança e encaminhei sua "
                    f"contestação a um especialista, com a análise pronta. Protocolo {prot}."), None
        return (f"{nome}, a compra na {tx['loja']} não apresenta sinais de fraude. Registrei sua contestação "
                f"para análise de um especialista. Protocolo {prot}."), None

    # --- outros agentes com ferramentas: chama cada uma uma vez, na ordem, e resume
    def _generico(self, pedido, res, ferramentas):
        for f in ferramentas:
            if f["nome"] not in res:
                args = {p: (pedido if s.get("type") == "string" else 0)
                        for p, s in f["parametros"]["properties"].items() if p in f["parametros"]["required"]}
                return f"Vou acionar {f['nome']}.", Chamada(self._id(), f["nome"], args)
        for r in res.values():
            if isinstance(r, dict) and "resposta_cliente" in r:
                return r["resposta_cliente"], None
        for r in res.values():
            if isinstance(r, dict) and "regras" in r:
                return "A política diz: " + " ".join(r["regras"]), None
        return "Resumo: " + " | ".join(str(r.get("resposta", r))[:120] if isinstance(r, dict) else str(r)[:120]
                                         for r in res.values()), None

    # --- agentes só de texto (chatbot, atendimento, revisor)
    def _sem_ferramentas(self, instrucoes, ultimo, todos):
        i = instrucoes.lower()
        if "revisor" in i:
            problemas = []
            if re.search(r"\d{3}\.\d{3}\.\d{3}-\d{2}|cpf", ultimo, re.I):
                problemas.append("expõe dado sensível (CPF)")
            if "definitivo" in ultimo.lower():
                problemas.append("promete estorno definitivo; a política só permite estorno provisório")
            if "protocolo" not in ultimo.lower():
                problemas.append("falta o número de protocolo")
            return json.dumps({"aprovado": not problemas, "problemas": problemas}, ensure_ascii=False)
        if "atendimento" in i:
            nome = _achar(r"Cliente: (\w+)", todos, "Cliente", 1)
            cartao = _achar(r"cartão final (\d{4})", todos, "****", 1)
            prot = _achar(r"2026-\d+", todos, "a confirmar")
            return (f"{nome}, bloqueamos seu cartão final {cartao} por segurança e abrimos um estorno "
                    f"provisório da compra, que aparece na próxima fatura. Protocolo {prot}.")
        if "chatbot" in i:
            return ("Para contestar uma compra, acesse o app > Cartões > Fatura, selecione a compra e toque em "
                    "'Não reconheço'. A análise leva até 10 dias úteis.")
        return "Entendido."


def _achar(padrao, texto, padrao_se_vazio, grupo=0):
    m = re.search(padrao, texto)
    return m.group(grupo) if m else padrao_se_vazio


# =====================================================================================
def criar_provedor(nome: str | None = None, modelo: str | None = None):
    """claude | gpt | simulado. Sem nome: usa a chave que estiver configurada no ambiente."""
    nome = (nome or os.getenv("PROVEDOR") or "").lower()
    if not nome:
        nome = "claude" if os.getenv("ANTHROPIC_API_KEY") else "gpt" if os.getenv("OPENAI_API_KEY") else "simulado"
    if nome == "claude":
        _exigir("ANTHROPIC_API_KEY", "anthropic")
        return ProvedorClaude(modelo)
    if nome in ("gpt", "openai"):
        _exigir("OPENAI_API_KEY", "openai")
        return ProvedorGPT(modelo)
    if nome == "simulado":
        return ProvedorSimulado()
    raise SystemExit(f"Provedor desconhecido: {nome}. Use claude, gpt ou simulado.")


def _exigir(variavel, pacote):
    try:
        __import__(pacote)
    except ImportError:
        raise SystemExit(f"Instale o SDK:  pip install {pacote}")
    if not os.getenv(variavel):
        raise SystemExit(f"Defina a variável de ambiente {variavel} (ou rode com --provedor simulado).")
