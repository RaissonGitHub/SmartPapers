from django.urls import path

from .views.agent_chat import AgentChatView
from .views.areas import AreasView
from .views.cancelar import CancelarRequisicaoView
from .views.modelos import ListarModelosView
from .views.sessoes import SessaoDetailView, SessaoListCreateView

app_name = "chat"

urlpatterns = [
    path("agente/", AgentChatView.as_view()),
    path("cancelar/", CancelarRequisicaoView.as_view()),
    path("modelos/", ListarModelosView.as_view()),
    path("areas/", AreasView.as_view()),
    path("sessoes/", SessaoListCreateView.as_view()),
    path("sessoes/<int:pk>/", SessaoDetailView.as_view()),
]