from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..serializers import AgentChatRequestSerializer
from ..services.conversa_service import processar_e_salvar
from ..services.providers import criar_provedor


def _mensagem_erro_provedor(exc, api_key=None):
    """Converte exceções de provedores LLM em mensagem amigável (ou None).

    Imports do SDK são feitos aqui (preguiçosos) para manter a isolação entre
    os provedores: instalar/rodar apenas Google não exige o pacote do Ollama e
    vice-versa.
    """
    try:
        from google.genai import errors as erros_genai
    except ImportError:
        erros_genai = None

    if erros_genai is not None and isinstance(exc, erros_genai.APIError):
        mensagem = (exc.message or str(exc)).strip()
        if api_key:
            mensagem = mensagem.replace(api_key, "***")
        return f"Erro na chamada ao Gemini: {mensagem}"

    if getattr(type(exc), "__module__", "").startswith("ollama"):
        return f"Erro na chamada ao Ollama: {exc}"

    return None


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
        api_key = (request.data.get("api_key") or "").strip() or None
        modelo = (request.data.get("modelo") or "").strip() or None
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

        try:
            if provider_name:
                provedor = criar_provedor(
                    provider_name, api_key=api_key, modelo=modelo
                )
            elif api_key or modelo:
                provedor = criar_provedor("gemini", api_key=api_key, modelo=modelo)
            else:
                provedor = None
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
        except Exception as exc:
            mensagem_erro = _mensagem_erro_provedor(exc, api_key=api_key)
            if mensagem_erro is None:
                raise
            return Response(
                {"erro": mensagem_erro},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(resultado, status=status.HTTP_200_OK)
