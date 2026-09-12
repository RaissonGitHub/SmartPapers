from rest_framework import generics

from artigos.models import Autor
from artigos.serializers import AutorSerializer


class AutorGenericListView(generics.ListAPIView):
    queryset = Autor.objects.all()
    serializer_class = AutorSerializer
