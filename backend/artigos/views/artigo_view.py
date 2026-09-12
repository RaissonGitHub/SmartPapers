from rest_framework import generics

from artigos.models import Artigo
from artigos.serializers import ArtigoSerializer


class ArtigoGenericListView(generics.ListAPIView):
    queryset = Artigo.objects.all()
    serializer_class = ArtigoSerializer