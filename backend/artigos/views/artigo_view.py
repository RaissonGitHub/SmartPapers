from rest_framework.generics import ListAPIView

from artigos.models import Artigo
from artigos.serializers import ArtigoSerializer


class ArtigoGenericListView(ListAPIView):
    queryset = Artigo.objects.all()
    serializer_class = ArtigoSerializer