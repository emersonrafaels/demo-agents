"""
utils/conexao_openai.py — conexão com o GPT (API Chat Completions da OpenAI).

    pip install openai
    OPENAI_API_KEY      chave de acesso
    MODELO_GPT          opcional (padrão: gpt-5.6)
    OPENAI_BASE_URL     opcional, para gateways compatíveis com a API da OpenAI
"""

from __future__ import annotations

import json
import os

from .base import Chamada, Provedor, Resposta


class ProvedorGPT(Provedor):
    nome = "GPT"

    def __init__(self, modelo: str | None = None):
        import openai
        self.cliente = openai.OpenAI()                       # lê OPENAI_API_KEY e OPENAI_BASE_URL
        self.modelo = modelo or os.getenv("MODELO_GPT", "gpt-5.6")

    def conversar(self, instrucoes, historico, ferramentas=None, max_tokens=1500) -> Resposta:
        params = dict(model=self.modelo, messages=self._mensagens(instrucoes, historico))
        if ferramentas:
            params["tools"] = [{"type": "function", "function": {
                "name": f.nome, "description": f.descricao, "parameters": f.parametros}}
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
        """Histórico neutro → formato de mensagens do GPT."""
        msgs = [{"role": "system", "content": instrucoes}]     # no GPT, instruções = 1ª mensagem
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
