import os

from autenticacao.seguranca import remover_chave_do_texto, validar_chave_api
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..serializers import AgentChatRequestSerializer
from ..services.cancelamento import (
    RequisicaoCancelada,
    cancelar,
    definir_requisicao,
    limpar_requisicao,
    novo_id,
)
from ..services.conversa_service import processar_e_salvar
from ..services.fluxo import TIPO_NDJSON, Fluxo, linha
from ..services.gemini_provider import mensagem_chave_invalida
from ..services.orcamento import TempoEsgotado, definir_orcamento, limpar_orcamento
from ..services.providers import criar_provedor, ollama_habilitado

MAX_MENSAGEM_CHARS = int(os.getenv("MAX_MENSAGEM_CHARS", "50000"))
MAX_PDF_BYTES = int(os.getenv("MAX_PDF_BYTES", str(15 * 1024 * 1024)))
MAX_PDF_MB = MAX_PDF_BYTES // (1024 * 1024)


class _ErroRequisicao(Exception):
    """Falha com mensagem amigável e status HTTP prontos."""

    def __init__(self, mensagem: str, status_http: int):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status_http = status_http


def _mensagem_erro_provedor(exc, api_key=None):
    """Converte exceções de provedores LLM em mensagem amigável."""

    try:
        from google.genai import errors as erros_genai
    except ImportError:
        erros_genai = None

    if erros_genai is not None and isinstance(exc, erros_genai.APIError):
        mensagem_chave = mensagem_chave_invalida(exc)
        if mensagem_chave:
            return mensagem_chave
        mensagem = remover_chave_do_texto((exc.message or str(exc)).strip(), api_key)
        return f"Erro na chamada ao Gemini: {mensagem}"

    if getattr(type(exc), "__module__", "").startswith("ollama"):
        return f"Erro na chamada ao Ollama: {exc}"

    return None


def _criar_provedor(provider_name, api_key, modelo):
    """Resolve o provedor do pedido; None usa o padrão da camada RAG."""
    if provider_name:
        return criar_provedor(provider_name, api_key=api_key, modelo=modelo)
    if api_key or modelo:
        return criar_provedor("gemini", api_key=api_key, modelo=modelo)
    return None


VERDADEIROS = ("1", "true", "sim", "yes")


def _quer_stream(request) -> bool:
    """Indica se o cliente solicitou streaming via body ou query string."""
    if str(request.query_params.get("stream", "")).strip().lower() in VERDADEIROS:
        return True
    valor = request.data.get("stream") if hasattr(request, "data") else None
    return str(valor or "").strip().lower() in VERDADEIROS


class AgentChatView(APIView):
    """Endpoint de chat do agente com suporte a streaming e persistência."""

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
        if (
            not provider_request
            and pref_provider == "ollama"
            and not ollama_habilitado()
        ):
            pref_provider = "gemini"
        provider_name = provider_request or pref_provider or ""
        chave_enviada_no_corpo = (request.data.get("api_key") or "").strip()
        api_key = chave_enviada_no_corpo or preferencias.get("pref_api_key") or None
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
            if not chave_enviada_no_corpo:
                api_key = None
            else:
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
                {
                    "erro": "O campo 'requisicao' deve ser 'busca', 'resposta' ou ausente."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializador = self.get_serializer(data=request.data)
        if not serializador.is_valid():
            primeiro = next(iter(serializador.errors.values()))
            mensagem_erro = (
                primeiro[0] if isinstance(primeiro, list) and primeiro else str(primeiro)
            )
            return Response(
                {"erro": mensagem_erro},
                status=status.HTTP_400_BAD_REQUEST,
            )
        contexto = {
            "mensagem": mensagem,
            "sessao_key": sessao_id,
            "usuario": request.user,
            "requisicao": requisicao or None,
            "ano_inicio": ano_inicio,
            "ano_fim": ano_fim,
            "area": area,
            "pdf": pdf,
            "editar": editar,
        }
        if _quer_stream(request):
            resposta = StreamingHttpResponse(
                self._eventos(contexto, provider_name, api_key, modelo, requisicao_id),
                content_type=TIPO_NDJSON,
            )
            resposta["Cache-Control"] = "no-cache, no-transform"
            resposta["X-Accel-Buffering"] = "no"

            return resposta

        try:
            dados = self._processar(
                contexto, provider_name, api_key, modelo, requisicao_id
            )

        except _ErroRequisicao as erro:
            return Response({"erro": erro.mensagem}, status=erro.status_http)
        return Response(dados, status=status.HTTP_200_OK)

    def _processar(self, contexto, provider_name, api_key, modelo, requisicao_id):
        """Executa o pipeline com orçamento de tempo e cancelamento cooperativo."""

        try:
            definir_orcamento()
            definir_requisicao(requisicao_id)
            provedor = _criar_provedor(provider_name, api_key, modelo)
            return processar_e_salvar(provider=provedor, **contexto)

        except RequisicaoCancelada:
            return {"cancelada": True, "requisicao_id": requisicao_id}

        except TempoEsgotado as exc:
            raise _ErroRequisicao(str(exc), status.HTTP_504_GATEWAY_TIMEOUT) from exc

        except ValueError as exc:
            raise _ErroRequisicao(str(exc), status.HTTP_400_BAD_REQUEST) from exc

        except Exception as exc:
            mensagem = _mensagem_erro_provedor(exc, api_key=api_key)
            if mensagem is None:
                raise
            raise _ErroRequisicao(mensagem, status.HTTP_502_BAD_GATEWAY) from exc
        finally:
            limpar_requisicao()
            limpar_orcamento()

    def _eventos(self, contexto, provider_name, api_key, modelo, requisicao_id):
        """Gera as linhas NDJSON conforme o pipeline avança."""

        fluxo = Fluxo()
        fluxo.iniciar(
            lambda: self._processar(
                contexto, provider_name, api_key, modelo, requisicao_id
            )
        )

        concluido = False

        try:
            for evento in fluxo.eventos():
                if evento["tipo"] == "fim":
                    concluido = True
                    dados = evento["dados"]

                    if isinstance(dados, dict) and dados.get("cancelada"):
                        yield linha(
                            {
                                "tipo": "cancelada",
                                "requisicao_id": dados.get(
                                    "requisicao_id", requisicao_id
                                ),
                            }
                        )

                    else:
                        yield linha({"tipo": "resultado", "dados": dados})
                    return

                if evento["tipo"] == "falha":
                    concluido = True
                    yield linha(self._evento_erro(evento["erro"], api_key))
                    return
                yield linha(evento)

        finally:
            if not concluido and fluxo.rodando:
                cancelar(requisicao_id)

    @staticmethod
    def _evento_erro(exc, api_key) -> dict:

        if isinstance(exc, _ErroRequisicao):
            return {"tipo": "erro", "erro": exc.mensagem, "status": exc.status_http}

        mensagem = _mensagem_erro_provedor(exc, api_key=api_key)

        if mensagem is None:
            print(f"[chat/agente] Erro inesperado no pipeline: {exc!r}")

            return {
                "tipo": "erro",
                "erro": "Ocorreu um erro inesperado. Tente novamente em alguns instantes.",
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
            }
        return {
            "tipo": "erro",
            "erro": mensagem,
            "status": status.HTTP_502_BAD_GATEWAY,
        }
