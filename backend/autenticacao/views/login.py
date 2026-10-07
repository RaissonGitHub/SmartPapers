from typing import ClassVar

from django.contrib.auth import authenticate, login
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..seguranca import ip_bloqueado, limpar_falhas, registrar_falha
from .shared import LoginSerializer, contexto_do_serializer, resposta_usuario


class LoginView(APIView):
    """POST /auth/login/ -> inicia a sessão com cookie."""

    permission_classes: ClassVar[list] = [AllowAny]
    serializer_class = LoginSerializer
    throttle_scope = "login"

    def get_serializer(self, *args, **kwargs):
        kwargs.setdefault("context", contexto_do_serializer(self))
        return LoginSerializer(*args, **kwargs)

    def post(self, request):
        if ip_bloqueado(request):
            return Response(
                {"erro": "Muitas tentativas. Tente novamente em alguns minutos."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        username = request.data.get("username", "")
        password = request.data.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is None:
            registrar_falha(request)
            return Response(
                {"erro": "Credenciais inválidas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        limpar_falhas(request)
        login(request, user)
        return Response(resposta_usuario(user), status=status.HTTP_200_OK)