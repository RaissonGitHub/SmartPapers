from rest_framework import serializers

from chat.models import Sessao

from .mensagem_serializer import MensagemSerializer


class SessaoListSerializer(serializers.ModelSerializer):
    total_mensagens = serializers.SerializerMethodField()
    ultima_mensagem = serializers.SerializerMethodField()

    class Meta:
        model = Sessao
        fields = (
            "id",
            "sessao_id",
            "titulo",
            "criada_em",
            "total_mensagens",
            "ultima_mensagem",
        )

    def get_total_mensagens(self, obj) -> int:
        return obj.mensagens.count()

    def get_ultima_mensagem(self, obj) -> str:
        ultima = obj.mensagens.order_by("-criada_em", "-id").first()
        return ultima.conteudo if ultima else ""


class SessaoDetailSerializer(serializers.ModelSerializer):
    mensagens = MensagemSerializer(many=True, read_only=True)

    class Meta:
        model = Sessao
        fields = (
            "id",
            "sessao_id",
            "usuario",
            "titulo",
            "criada_em",
            "artigos_contexto",
            "pdf_nome",
            "pdf_secoes",
            "pdfs",
            "mensagens",
        )
        read_only_fields = (
            "id",
            "sessao_id",
            "usuario",
            "criada_em",
            "artigos_contexto",
            "pdf_nome",
            "pdf_secoes",
            "pdfs",
            "mensagens",
        )