from rest_framework.generics import ListAPIView

from artigos.models import Autor
from artigos.serializers import AutorSerializer


class AutorGenericListView(ListAPIView):
    queryset = Autor.objects.all()
    serializer_class = AutorSerializer
