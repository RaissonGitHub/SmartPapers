import os

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from autenticacao.seguranca import remover_chave_do_texto, validar_chave_api

from ..serializers import AgentChatRequestSerializer
from ..services.cancelamento import (
    RequisicaoCancelada,
    definir_requisicao,
    limpar_requisicao,
    novo_id,
)
from ..services.conversa_service import processar_e_salvar
from ..services.gemini_provider import mensagem_chave_invalida
from ..services.providers import criar_provedor, ollama_habilitado

MAX_MENSAGEM_CHARS = int(os.getenv("MAX_MENSAGEM_CHARS", "50000"))
MAX_PDF_BYTES = int(os.getenv("MAX_PDF_BYTES", str(15 * 1024 * 1024)))
MAX_PDF_MB = MAX_PDF_BYTES // (1024 * 1024)


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
        mensagem_chave = mensagem_chave_invalida(exc)
        if mensagem_chave:
            return mensagem_chave
        mensagem = remover_chave_do_texto(
            (exc.message or str(exc)).strip(), api_key
        )
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
    throttle_scope = "agente"

    def get_serializer(self, *args, **kwargs):
        kwargs.setdefault("context", {"request": self.request, "view": self})
        return AgentChatRequestSerializer(*args, **kwargs)

    def post(self, request):
        mensagem = request.data.get("mensagem")
        preferencias = request.session
        provider_request = (request.data.get("provider") or "").strip().lower()
        pref_provider = (preferencias.get("pref_provider") or "").lower()
        if not provider_request and pref_provider == "ollama" and not ollama_habilitado():
            pref_provider = "gemini"
        provider_name = provider_request or pref_provider or ""
        api_key = (
            (request.data.get("api_key") or "").strip()
            or preferencias.get("pref_api_key")
            or None
        )
        modelo = (
            (request.data.get("modelo") or "").strip()
            or preferencias.get("pref_modelo")
            or None
        )
        requisicao = request.data.get("requisicao", "").lower()
        sessao_id = request.data.get("sessao_id")
        area = request.data.get("area", "") or ""
        pdf = request.data.get("pdf")
        requisicao_id = (request.data.get("requisicao_id") or "").strip() or novo_id()
        editar = str(request.data.get("editar") or "").strip().lower() in (
            "1",
            "true",
            "sim",
            "yes",
        )

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

        if len(mensagem) > MAX_MENSAGEM_CHARS:
            return Response(
                {
                    "erro": f"A mensagem é muito longa "
                    f"(máximo de {MAX_MENSAGEM_CHARS} caracteres)."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if api_key and not validar_chave_api(api_key):
            return Response(
                {"erro": "Chave de API inválida. Verifique e tente novamente."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if pdf:
            nome_pdf = getattr(pdf, "name", "") or ""
            if not nome_pdf.lower().endswith(".pdf"):
                return Response(
                    {"erro": "O anexo enviado deve ser um arquivo PDF."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if getattr(pdf, "size", 0) > MAX_PDF_BYTES:
                return Response(
                    {
                        "erro": f"O anexo PDF é muito grande "
                        f"(máximo de {MAX_PDF_MB} MB)."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            inicio = b""
            if hasattr(pdf, "read"):
                try:
                    inicio = pdf.read(8) or b""
                finally:
                    try:
                        pdf.seek(0)
                    except Exception:
                        pass
            if not inicio.startswith(b"%PDF-"):
                return Response(
                    {"erro": "O arquivo enviado não é um PDF válido."},
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
            definir_requisicao(requisicao_id)
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
                editar=editar,
            )
        except RequisicaoCancelada:
            return Response(
                {"cancelada": True, "requisicao_id": requisicao_id},
                status=status.HTTP_200_OK,
            )
        except ValueError as exc:
            return Response(
                {"erro": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            mensagem_erro = _mensagem_erro_provedor(exc, api_key=api_key)
            if mensagem_erro is None:
                raise
            return Response(
                {"erro": mensagem_erro},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        finally:
            limpar_requisicao()

        return Response(resultado, status=status.HTTP_200_OK)
