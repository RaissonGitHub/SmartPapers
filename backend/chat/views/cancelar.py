from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..services.cancelamento import cancelar


class CancelarRequisicaoView(APIView):
    """Marca uma requisição em andamento para ser interrompida.

    POST /api/chat/cancelar/
    Body: { "requisicao_id": "..." }

    Responde sempre no mesmo formato de cancelamento da resposta JSON do
    chat: {"cancelada": true, "requisicao_id": "..."}. No streaming, o mesmo
    payload vem embrulhado em {"tipo": "cancelada", ...}.
    """

    def post(self, request):
        requisicao_id = (request.data.get("requisicao_id") or "").strip()
        if not requisicao_id:
            return Response(
                {"erro": "O campo 'requisicao_id' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cancelar(requisicao_id)
        return Response(
            {"cancelada": True, "requisicao_id": requisicao_id},
            status=status.HTTP_200_OK,
        )
