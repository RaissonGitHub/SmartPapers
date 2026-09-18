from rest_framework import serializers

from chat.models import Mensagem


class MensagemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mensagem
        fields = (
            "id",
            "papel",
            "conteudo",
            "artigos",
            "ferramenta_utilizada",
            "criada_em",
        )