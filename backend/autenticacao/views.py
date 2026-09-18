from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.middleware.csrf import get_token
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class _RegistroSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=8, write_only=True)

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Nome de usuário já está em uso.")
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

    def get_serializer(self, *args, **kwargs):
        kwargs.setdefault("context", _contexto_do_serializer(self))
        return _LoginSerializer(*args, **kwargs)

    permission_classes = [AllowAny]

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