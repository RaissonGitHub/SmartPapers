import uuid

from rest_framework import generics

from chat.models import Sessao
from chat.serializers import SessaoDetailSerializer, SessaoListSerializer


class SessaoListCreateView(generics.ListCreateAPIView):
    """
    GET  /chat/sessoes/       -> lista sessões do usuário logado (mais recentes primeiro)
    POST /chat/sessoes/       -> cria uma nova sessão
        Body: { "titulo": "opcional" }
    """

    def get_queryset(self):
        return Sessao.objects.filter(usuario=self.request.user).order_by(
            "-criada_em"
        )

    def get_serializer_class(self):
        if self.request.method == "GET":
            return SessaoListSerializer
        return SessaoDetailSerializer

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user, sessao_id=str(uuid.uuid4()))


class SessaoDetailView(generics.RetrieveDestroyAPIView):
    """
    GET    /chat/sessoes/<pk>/ -> sessão com todas as mensagens
    DELETE /chat/sessoes/<pk>/ -> remove sessão e mensagens
    """

    serializer_class = SessaoDetailSerializer

    def get_queryset(self):
        return Sessao.objects.filter(usuario=self.request.user)