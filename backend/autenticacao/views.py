from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.middleware.csrf import get_token
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .seguranca import mascarar_chave, validar_chave_api


class _RegistroSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=8, write_only=True)

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(
                "Não foi possível criar a conta com esse nome de usuário."
            )
        return value


class _LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


def _contexto_do_serializer(view):
    return {"request": view.request, "view": view}


def _resposta_usuario(user):
    return {"id": user.id, "username": user.username}


class RegistrarView(APIView):
    """POST /auth/registrar/  Body: { "username", "password" } -> cria conta e loga."""

    permission_classes = [AllowAny]
    serializer_class = _RegistroSerializer
    throttle_scope = "login"

    def get_serializer(self, *args, **kwargs):
        kwargs.setdefault("context", _contexto_do_serializer(self))
        return _RegistroSerializer(*args, **kwargs)

    def post(self, request):
        serializer = _RegistroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.create_user(
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        login(request, user)
        return Response(_resposta_usuario(user), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """POST /auth/login/  Body: { "username", "password" } -> loga (cookie de sessão)."""

    permission_classes = [AllowAny]
    serializer_class = _LoginSerializer
    throttle_scope = "login"

    def get_serializer(self, *args, **kwargs):
        kwargs.setdefault("context", _contexto_do_serializer(self))
        return _LoginSerializer(*args, **kwargs)

    def post(self, request):
        username = request.data.get("username", "")
        password = request.data.get("password", "")

        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response(
                {"erro": "Credenciais inválidas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        login(request, user)
        return Response(_resposta_usuario(user), status=status.HTTP_200_OK)


class LogoutView(APIView):
    """POST /auth/logout/ -> encerra a sessão (apaga o cookie)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserView(APIView):
    """GET /auth/me/ -> dados do usuário logado (401 se não autenticado)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            _resposta_usuario(request.user),
            status=status.HTTP_200_OK,
        )


class CsrfView(APIView):
    """GET /auth/csrf/ -> devolve token CSRF e define o cookie correspondente."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)}, status=status.HTTP_200_OK)


class PreferenciasView(APIView):
    """Preferências do chat (provedor/modelo/chave) persistidas por sessão de login.

    GET /auth/preferencias/  -> devolve as preferências salvas na sessão
    PUT /auth/preferencias/  -> salva as preferências na sessão (Body: { provider, api_key, modelo })
    """

    permission_classes = [IsAuthenticated]

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
            return Response(
                {"erro": "Provedor inválido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
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