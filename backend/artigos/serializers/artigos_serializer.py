from rest_framework import serializers

from artigos.models import Artigo


class ArtigoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artigo
        fields = (
            "openalex_id",
            "titulo",
            "resumo",
            "ano_publicacao",
            "area_conhecimento",
            "link_original",
            "fonte",
        )
