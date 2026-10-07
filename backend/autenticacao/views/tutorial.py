from typing import ClassVar

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import perfil_de


def _booleano(valor, padrao):
    if valor is None:
        return padrao
    if isinstance(valor, str):
        return valor.strip().lower() in ("1", "true", "yes", "sim")
    return bool(valor)


class TutorialView(APIView):
    permission_classes: ClassVar[list] = [IsAuthenticated]

    def get(self, request):
        return Response(
            {"visto": perfil_de(request.user).tutorial_visto},
            status=status.HTTP_200_OK,
        )

    def put(self, request):
        perfil = perfil_de(request.user)
        perfil.tutorial_visto = _booleano(request.data.get("visto"), True)
        perfil.save(update_fields=["tutorial_visto"])
        return Response({"visto": perfil.tutorial_visto}, status=status.HTTP_200_OK)