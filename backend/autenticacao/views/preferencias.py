from typing import ClassVar

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..seguranca import mascarar_chave, validar_chave_api


class PreferenciasView(APIView):
    permission_classes: ClassVar[list] = [IsAuthenticated]

    def _ler(self, request):
        sessao = request.session
        ollama_on = bool(settings.OLLAMA_ENABLED)
        provider = sessao.get("pref_provider") or "gemini"
        if provider == "ollama" and not ollama_on:
            provider = "gemini"
        api_key = sessao.get("pref_api_key") or ""
        modelo = sessao.get("pref_modelo") or ""
        if api_key and not validar_chave_api(api_key):
            api_key = ""
            sessao["pref_api_key"] = ""
        if provider == "ollama":
            api_key = ""
            modelo = ""
        elif not api_key:
            modelo = ""
        return {
            "provider": provider,
            "api_key": mascarar_chave(api_key) if api_key else "",
            "api_key_definida": bool(api_key),
            "modelo": modelo,
            "ollama_enabled": ollama_on,
        }

    def get(self, request):
        return Response(self._ler(request), status=status.HTTP_200_OK)

    def put(self, request):
        provider = (request.data.get("provider") or "").strip().lower() or "gemini"
        if provider not in ("gemini", "ollama"):
            return Response({"erro": "Provedor inválido."}, status=status.HTTP_400_BAD_REQUEST)
        if provider == "ollama" and not settings.OLLAMA_ENABLED:
            return Response(
                {"erro": "O provedor Ollama está desativado neste servidor."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sessao = request.session
        sessao["pref_provider"] = provider
        if provider == "ollama":
            sessao["pref_api_key"] = ""
            sessao["pref_modelo"] = ""
        else:
            if "api_key" in request.data:
                api_key = (request.data.get("api_key") or "").strip()
                if api_key and not validar_chave_api(api_key):
                    return Response(
                        {"erro": "Chave de API inválida. Verifique e tente novamente."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                sessao["pref_api_key"] = api_key
                if not api_key:
                    sessao["pref_modelo"] = ""
            if "modelo" in request.data:
                sessao["pref_modelo"] = (request.data.get("modelo") or "").strip()

        return Response(self._ler(request), status=status.HTTP_200_OK)