from artigos.services.buscar_artigos_service import buscar_artigos
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView


class PesquisaComEmbedding(APIView):
    def post(self, request):
        embedding = request.data.get("embedding")
        top_n = request.data.get("top_n")
        ano_inicio = request.data.get("ano_inicio")
        ano_fim = request.data.get("ano_fim")
        area = request.data.get("area")

        resultado = buscar_artigos(
            embedding,
            top_n,
            ano_inicio,
            ano_fim,
            area,
        )

        paginador = PageNumberPagination()
        pagina = paginador.paginate_queryset(
            resultado,
            request,
            view=self,
        )

        return paginador.get_paginated_response(pagina)
