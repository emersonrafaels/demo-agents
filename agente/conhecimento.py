"""
agente/conhecimento.py — busca de conhecimento: políticas, normas e manuais consultados na hora.

O agente não "decora" as regras do banco: a cada pergunta, busca os trechos relevantes nos
documentos oficiais e responde com base neles, citando a fonte (o que se costuma chamar de RAG).

Aqui a busca é por palavras-chave (BM25), em Python puro, sobre os arquivos .md da pasta
base_conhecimento/. Em produção, o mesmo papel é feito por busca semântica (embeddings) sobre o
acervo oficial, com controle de versão e de acesso dos documentos.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

from .ferramentas import Ferramenta

_STOP = set("a o as os um uma de do da dos das e em no na nos nas por para com que se ao aos ou "
            "é ser foi meu minha seu sua eu voce você ate até mais como qual quais".split())


def _tokens(texto: str) -> list[str]:
    t = unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()
    palavras = re.findall(r"[a-z0-9]+", t)
    return [p[:-1] if len(p) > 4 and p.endswith("s") else p for p in palavras if p not in _STOP]


class BaseConhecimento:
    def __init__(self, pasta: str | Path = None, k: int = 3):
        self.pasta = Path(pasta or Path(__file__).resolve().parent.parent / "base_conhecimento")
        self.k = k
        self.trechos = self._carregar()
        self._indexar()

    # ------------------------------------------------------------------ preparação
    def _carregar(self) -> list[dict]:
        """Quebra cada documento em trechos, um por seção (## Título)."""
        trechos = []
        for arq in sorted(self.pasta.glob("*.md")):
            for bloco in re.split(r"\n(?=## )", arq.read_text(encoding="utf-8")):
                if not bloco.startswith("## "):
                    continue
                titulo, _, corpo = bloco.partition("\n")
                trechos.append({"fonte": f"{arq.name} § {titulo[3:].strip()}",
                                "texto": " ".join(corpo.split())})
        return trechos

    def _indexar(self) -> None:
        self._docs = [_tokens(t["fonte"] + " " + t["texto"]) for t in self.trechos]
        self._tf = [Counter(d) for d in self._docs]
        self._media = sum(map(len, self._docs)) / max(1, len(self._docs))
        n = len(self._docs)
        df = Counter(p for d in self._docs for p in set(d))
        self._idf = {p: math.log(1 + (n - f + .5) / (f + .5)) for p, f in df.items()}

    # ------------------------------------------------------------------ busca (BM25)
    def buscar(self, pergunta: str, k: int | None = None) -> list[dict]:
        consulta = _tokens(pergunta)
        notas = []
        for i, tf in enumerate(self._tf):
            nota = sum(self._idf.get(p, 0) * tf[p] * 2.5 / (tf[p] + 1.5 * (.25 + .75 * len(self._docs[i]) / self._media))
                       for p in consulta if p in tf)
            if nota > 0:
                notas.append((nota, i))
        notas.sort(reverse=True)
        return [{**self.trechos[i], "relevancia": round(n, 2)} for n, i in notas[: k or self.k]]

    def como_ferramenta(self) -> Ferramenta:
        return Ferramenta(
            nome="buscar_conhecimento",
            descricao=("Busca trechos das políticas, normas e manuais internos (contestação, alçadas, prazos, "
                       "segurança do cartão, comunicação com o cliente). Use sempre que precisar de uma regra, "
                       "prazo ou procedimento, e cite a fonte retornada."),
            parametros={"type": "object", "required": ["pergunta"],
                        "properties": {"pergunta": {"type": "string",
                                                    "description": "O que você precisa saber, em linguagem natural"}}},
            funcao=lambda pergunta: {"pergunta": pergunta, "trechos": self.buscar(pergunta)},
            icone="📚",
        )
