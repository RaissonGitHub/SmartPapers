from typing import ClassVar

from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..seguranca import registro_publico, validar_username
from .shared import RegistroSerializer, contexto_do_serializer, resposta_usuario


class _RegistroSerializer(RegistroSerializer):
    def validate_username(self, value):
        valido, motivo = validar_username(value)
        if not valido:
            raise serializers.ValidationError(motivo)
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(
                "Não foi possível criar a conta com esse nome de usuário."
            )
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except ValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value


class RegistrarView(APIView):
    """POST /auth/registrar/ -> cria conta e inicia a sessão."""

    permission_classes: ClassVar[list] = [AllowAny]
    serializer_class = _RegistroSerializer
    throttle_scope = "registro"

    def get_serializer(self, *args, **kwargs):
        kwargs.setdefault("context", contexto_do_serializer(self))
        return _RegistroSerializer(*args, **kwargs)

    def post(self, request):
        if not registro_publico():
            return Response(
                {"erro": "O cadastro está desativado neste servidor."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = _RegistroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.create_user(
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        login(request, user)
        return Response(resposta_usuario(user), status=status.HTTP_201_CREATED)