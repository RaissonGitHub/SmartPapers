import os
import time
from contextvars import ContextVar

CHAT_TIMEOUT_SEGUNDOS = float(os.getenv("CHAT_TIMEOUT_SEGUNDOS", "90"))

_prazo: ContextVar[float | None] = ContextVar("orcamento_prazo", default=None)


class TempoEsgotado(Exception):
    """Levantada quando a requisição estoura o orçamento de tempo."""

    def __init__(self, etapa: str = ""):
        self.etapa = etapa
        detalhe = f" durante '{etapa}'" if etapa else ""
        super().__init__(
            f"A pesquisa demorou demais{detalhe} e foi interrompida. "
            "Tente novamente em instantes ou refine a busca (menos filtros)."
        )


def definir_orcamento(segundos: float | None = None) -> None:
    """Abre um orçamento para a requisição atual.

    Sem argumento usa `CHAT_TIMEOUT_SEGUNDOS`. `0` esgota na hora (útil em
    testes). Use `None` explicitamente para desligar o limite.
    """
    limite = CHAT_TIMEOUT_SEGUNDOS if segundos is None else float(segundos)
    if limite <= 0:
        _prazo.set(time.monotonic())
        return
    _prazo.set(time.monotonic() + limite)


def limpar_orcamento() -> None:
    _prazo.set(None)


def tempo_restante() -> float | None:
    """Segundos que ainda restam, ou None quando não há orçamento aberto."""
    prazo = _prazo.get()
    if prazo is None:
        return None
    return max(prazo - time.monotonic(), 0.0)


def orcamento_esgotado() -> bool:
    restante = tempo_restante()
    return restante is not None and restante <= 0


def checar_orcamento(etapa: str = "") -> None:
    """Levanta `TempoEsgotado` quando o orçamento acabou."""
    if orcamento_esgotado():
        raise TempoEsgotado(etapa)