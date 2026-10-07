"""Publicação de etapas do pipeline durante a resposta em streaming."""

from collections.abc import Callable
from contextvars import ContextVar

_ao_avancar: ContextVar[Callable[[str, str], None] | None] = ContextVar(
    "progresso_ao_avancar", default=None
)


def definir_callback(callback: Callable[[str, str], None] | None) -> None:
    _ao_avancar.set(callback)


def limpar_callback() -> None:
    _ao_avancar.set(None)


def avancar(etapa: str, texto: str) -> None:
    """Publica uma etapa para o consumidor conectado (se houver)."""
    callback = _ao_avancar.get()
    if callback is None:
        return
    try:
        callback(etapa, texto)
    except Exception as exc: 
        print(f"[progresso] Falha ao publicar a etapa '{etapa}': {exc}")