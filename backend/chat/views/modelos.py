"""Listagem de modelos do Google Gemini com chave provida pelo usuário."""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..services.providers import listar_modelos_gemini

logger = logging.getLogger(__name__)


def _sanitizar_mensagem(erro, api_key: str) -> str:
    """Remove qualquer ocorrência da chave do texto do erro antes de expô-lo."""
    texto = str(getattr(erro, "body", "") or erro)
    if api_key:
        texto = texto.replace(api_key, "***")
    return texto.strip() or "Falha ao listar os modelos."


class ListarModelosView(APIView):
    """
    Lista os modelos do Gemini que suportam geração de conteúdo.

    POST /api/chat/modelos/
    Body: { "api_key": "..." }

    A chave é usada apenas nesta requisição e não é persistida em nenhum lugar.
    """

    def post(self, request):
        api_key = (request.data.get("api_key") or "").strip()
        if not api_key:
            return Response(
                {"erro": "O campo 'api_key' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            modelos = listar_modelos_gemini(api_key)
        except Exception as exc:
            logger.warning("Falha ao listar modelos do Gemini: %s", exc)
            return Response(
                {"erro": _sanitizar_mensagem(exc, api_key)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"modelos": modelos}, status=status.HTTP_200_OK)