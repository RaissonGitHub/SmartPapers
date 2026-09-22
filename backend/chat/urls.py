from django.urls import path

from .views.agent_chat import AgentChatView
from .views.areas import AreasView
from .views.cancelar import CancelarRequisicaoView
from .views.gerar_embedding import GerarEmbedding
from .views.modelos import ListarModelosView
from .views.pesquisa_com_embedding import PesquisaComEmbedding
from .views.pesquisa_sem_embedding import PesquisaSemEmbedding
from .views.sessoes import SessaoDetailView, SessaoListCreateView

app_name = "chat"

urlpatterns = [
    path("gerarembedding/", GerarEmbedding.as_view()),
    path("pesquisacomembbending/", PesquisaComEmbedding.as_view()),
    path("pesquisasemembbending/", PesquisaSemEmbedding.as_view()),
    path("agente/", AgentChatView.as_view()),
    path("cancelar/", CancelarRequisicaoView.as_view()),
    path("modelos/", ListarModelosView.as_view()),
    path("areas/", AreasView.as_view()),
    path("sessoes/", SessaoListCreateView.as_view()),
    path("sessoes/<int:pk>/", SessaoDetailView.as_view()),
]
