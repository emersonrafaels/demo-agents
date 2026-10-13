"""
utils/conexao_anthropic.py — conexão com o Claude (API Messages da Anthropic).

    pip install anthropic
    ANTHROPIC_API_KEY   chave de acesso
    MODELO_CLAUDE       opcional (padrão: claude-sonnet-5-5)
"""

from __future__ import annotations

import os

from .base import Chamada, Provedor, Resposta


class ProvedorClaude(Provedor):
    nome = "Claude"

    def __init__(self, modelo: str | None = None):
        import anthropic
        self.cliente = anthropic.Anthropic()                 # lê ANTHROPIC_API_KEY do ambiente
        self.modelo = modelo or os.getenv("MODELO_CLAUDE", "claude-sonnet-5-5")

    def conversar(self, instrucoes, historico, ferramentas=None, max_tokens=1500) -> Resposta:
        params = dict(model=self.modelo, max_tokens=max_tokens,
                      system=instrucoes,                     # no Claude, instruções vão à parte
                      messages=self._mensagens(historico))
        if ferramentas:
            params["tools"] = [{"name": f.nome, "description": f.descricao,
                                "input_schema": f.parametros} for f in ferramentas]
        r = self.cliente.messages.create(**params)

        texto = "".join(b.text for b in r.content if b.type == "text")
        chamadas = [Chamada(b.id, b.name, dict(b.input)) for b in r.content if b.type == "tool_use"]
        return Resposta(texto.strip(), chamadas, r.content, r.usage.input_tokens, r.usage.output_tokens)

    @staticmethod
    def _mensagens(historico):
        """Histórico neutro → formato de mensagens do Claude."""
        msgs = []

        def adicionar_usuario(bloco):
            # o Claude espera papéis alternados: blocos seguidos do usuário viram uma única mensagem
            if msgs and msgs[-1]["role"] == "user":
                if isinstance(msgs[-1]["content"], str):
                    msgs[-1]["content"] = [{"type": "text", "text": msgs[-1]["content"]}]
                msgs[-1]["content"].append(bloco)
            else:
                msgs.append({"role": "user", "content": [bloco]})

        for h in historico:
            if h["tipo"] == "usuario":
                adicionar_usuario({"type": "text", "text": h["texto"]})
            elif h["tipo"] == "assistente":
                # devolvemos a resposta original do Claude (preserva blocos de raciocínio, se houver)
                conteudo = h.get("bruto") if h.get("provedor") == "Claude" else None
                if conteudo is None:
                    conteudo = ([{"type": "text", "text": h["texto"]}] if h["texto"] else []) + [
                        {"type": "tool_use", "id": c.id, "name": c.nome, "input": c.args} for c in h["chamadas"]]
                if conteudo:
                    msgs.append({"role": "assistant", "content": conteudo})
            elif h["tipo"] == "resultado":
                adicionar_usuario({"type": "tool_result", "tool_use_id": h["id"], "content": h["conteudo"]})
        return msgs
