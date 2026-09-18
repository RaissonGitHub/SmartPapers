from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..serializers import AgentChatRequestSerializer
from ..services.conversa_service import processar_e_salvar
from ..services.providers import criar_provedor


class AgentChatView(APIView):
    """
    Endpoint com busca híbrida paralela (Título em Inglês gerado + Texto Cru).
    POST /api/chat/agente/
    Body: { "mensagem": "...", "provider": "ollama" | "gemini", "requisicao": "busca" | "resposta", "sessao_id": "opcional" }

    `requisicao` é opcional e força a intenção (sobrepõe a decisão do modelo):
        - "busca"   -> sempre executa a busca de artigos
        - "resposta"-> responde diretamente, sem tocar na ferramenta
        - ausente   -> o modelo decide (comportamento atual)

    `sessao_id` é opcional. Se ausente, uma nova sessão é criada e a conversa
    é persistida (mensagens do usuário e do modelo + artigos na sessão).
    """

    serializer_class = AgentChatRequestSerializer

    def get_serializer(self, *args, **kwargs):
        kwargs.setdefault("context", {"request": self.request, "view": self})
        return AgentChatRequestSerializer(*args, **kwargs)

    def post(self, request):
        mensagem = request.data.get("mensagem")
        provider_name = request.data.get("provider", "").lower()
        requisicao = request.data.get("requisicao", "").lower()
        sessao_id = request.data.get("sessao_id")
        area = request.data.get("area", "") or ""
        pdf = request.data.get("pdf")

        try:
            ano_inicio = int(request.data.get("ano_inicio") or 0)
            ano_fim = int(request.data.get("ano_fim") or 0)
        except (TypeError, ValueError):
            ano_inicio = 0
            ano_fim = 0

        if not mensagem:
            return Response(
                {"erro": "O campo 'mensagem' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if pdf and not getattr(pdf, "name", "").lower().endswith(".pdf"):
            return Response(
                {"erro": "O anexo enviado deve ser um arquivo PDF."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if requisicao and requisicao not in ("busca", "resposta"):
            return Response(
                {"erro": "O campo 'requisicao' deve ser 'busca', 'resposta' ou ausente."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        provedor = criar_provedor(provider_name) if provider_name else None
        resultado = processar_e_salvar(
            mensagem=mensagem,
            sessao_key=sessao_id,
            usuario=request.user,
            requisicao=requisicao or None,
            provider=provedor,
            ano_inicio=ano_inicio,
            ano_fim=ano_fim,
            area=area,
            pdf=pdf,
        )

        return Response(resultado, status=status.HTTP_200_OK)
