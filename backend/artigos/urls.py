from django.urls import path

from .views.artigo_view import ArtigoGenericListView
from .views.autor_view import AutorGenericListView

app_name = "artigos"

urlpatterns = [
    path("listar/", ArtigoGenericListView.as_view(), name="artigos-listar"),
    path("autores/", AutorGenericListView.as_view(), name="autores-listar"),
]
