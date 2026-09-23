"""Listagem de modelos do Google Gemini com chave provida pelo usuário."""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from autenticacao.seguranca import remover_chave_do_texto, validar_chave_api
from ..services.gemini_provider import mensagem_chave_invalida
from ..services.providers import listar_modelos_gemini

logger = logging.getLogger(__name__)


def _sanitizar_mensagem(erro, api_key: str) -> str:
    """Mensagem amigável, sem expor a chave, para falhas do Gemini."""
    mensagem_chave = mensagem_chave_invalida(erro)
    if mensagem_chave:
        return mensagem_chave
    texto = str(getattr(erro, "body", "") or erro)
    return remover_chave_do_texto(texto.strip(), api_key) or "Falha ao listar os modelos."


class ListarModelosView(APIView):
    """
    Lista os modelos do Gemini que suportam geração de conteúdo.

    POST /api/chat/modelos/
    Body: { "api_key": "..." }

    A chave é usada apenas nesta requisição e não é persistida em nenhum lugar.
    """

    throttle_scope = "modelos"

    def post(self, request):
        api_key = (request.data.get("api_key") or "").strip()
        if not api_key:
            return Response(
                {"erro": "O campo 'api_key' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not validar_chave_api(api_key):
            return Response(
                {"erro": "Chave de API inválida. Verifique e tente novamente."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            modelos = listar_modelos_gemini(api_key)
        except Exception as exc:
            logger.warning(
                "Falha ao listar modelos do Gemini: %s",
                remover_chave_do_texto(str(exc), api_key)[:500],
            )
            return Response(
                {"erro": _sanitizar_mensagem(exc, api_key)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"modelos": modelos}, status=status.HTTP_200_OK)