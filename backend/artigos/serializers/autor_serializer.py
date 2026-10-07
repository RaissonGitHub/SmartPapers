from rest_framework import serializers
from ..models.autor import Autor

class AutorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Autor
        fields = ("nome", "openalex_id")