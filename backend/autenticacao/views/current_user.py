from typing import ClassVar

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .shared import resposta_usuario


class CurrentUserView(APIView):
    permission_classes: ClassVar[list] = [IsAuthenticated]

    def get(self, request):
        return Response(resposta_usuario(request.user), status=status.HTTP_200_OK)