"""
agente/memoria.py — memória de curto prazo: o histórico da conversa entre uma mensagem e outra.

Sem memória, cada mensagem chega ao modelo isolada (ele não sabe o que foi dito antes).
Com memória, o agente reenvia ao modelo o histórico relevante a cada nova mensagem.

Para não crescer sem limite (custo e tamanho de contexto), guardamos só os últimos N turnos.
Em produção, somam-se a isso memórias de longo prazo (perfil e histórico do cliente), buscadas
quando necessário.
"""


class Memoria:
    def __init__(self, max_turnos: int = 20):
        self.max_turnos = max_turnos
        self.itens: list[dict] = []

    def mensagens(self) -> list[dict]:
        return list(self.itens)

    def registrar(self, novos: list[dict]) -> None:
        self.itens.extend(novos)
        self._podar()

    def limpar(self) -> None:
        self.itens.clear()

    def turnos(self) -> int:
        return sum(1 for h in self.itens if h["tipo"] == "usuario")

    def _podar(self) -> None:
        """Mantém os últimos N turnos, sempre cortando no início de um turno do usuário."""
        inicios = [i for i, h in enumerate(self.itens) if h["tipo"] == "usuario"]
        if len(inicios) > self.max_turnos:
            self.itens = self.itens[inicios[-self.max_turnos]:]
