from artigos.services.gerar_embedding_service import gerar_embedding
from rest_framework.response import Response
from rest_framework.views import APIView


class GerarEmbedding(APIView):
    def post(self, request):

        embedding = gerar_embedding(request.data.get("mensagem"))

        return Response({"resultado": embedding})
