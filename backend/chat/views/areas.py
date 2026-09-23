from rest_framework.response import Response
from rest_framework.views import APIView

from artigos.models.artigo import Artigo
from artigos.services.buscar_artigos_service import intervalo_anos_artigos


class AreasView(APIView):
    """GET /chat/areas/ -> áreas e janela de anos distintas da base."""

    def get(self, request):
        areas = (
            Artigo.objects.exclude(area_conhecimento="")
            .values_list("area_conhecimento", flat=True)
            .distinct()
            .order_by("area_conhecimento")
        )
        ano_minimo, ano_maximo = intervalo_anos_artigos()
        return Response(
            {
                "areas": list(areas),
                "ano_minimo": ano_minimo,
                "ano_maximo": ano_maximo,
            }
        )