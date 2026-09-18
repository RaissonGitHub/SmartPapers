from rest_framework.response import Response
from rest_framework.views import APIView

from artigos.models.artigo import Artigo


class AreasView(APIView):
    """GET /chat/areas/ -> áreas do conhecimento distintas da base."""

    def get(self, request):
        areas = (
            Artigo.objects.exclude(area_conhecimento="")
            .values_list("area_conhecimento", flat=True)
            .distinct()
            .order_by("area_conhecimento")
        )
        return Response({"areas": list(areas)})