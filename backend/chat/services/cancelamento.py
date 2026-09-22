"""Cancelamento cooperativo de requisições longas (pipeline RAG)."""

import secrets
from contextvars import ContextVar

from django.core.cache import cache

_requisicao_atual: ContextVar[str] = ContextVar("requisicao_atual", default="")

CHAVE_PREFIXO = "smartpapers:cancelar:"
TEMPO_VALIDADE_CANCELAMENTO = 900


class RequisicaoCancelada(Exception):
    """Levantada quando o usuário cancela o processamento em andamento."""


def novo_id() -> str:
    return secrets.token_hex(16)


def definir_requisicao(requisicao_id: str) -> None:
    _requisicao_atual.set(requisicao_id)


def limpar_requisicao() -> None:
    _requisicao_atual.set("")


def checar_cancelamento() -> None:
    requisicao_id = _requisicao_atual.get()
    if not requisicao_id:
        return
    if cache.get(CHAVE_PREFIXO + requisicao_id):
        raise RequisicaoCancelada()


def cancelar(requisicao_id: str) -> None:
    cache.set(CHAVE_PREFIXO + requisicao_id, True, TEMPO_VALIDADE_CANCELAMENTO)