from django.conf import settings
from django.contrib import admin
from django.db import models

from .base import Base


class Sessao(Base):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sessoes",
    )
    sessao_id = models.CharField(max_length=100, unique=True)
    titulo = models.CharField(max_length=500, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    artigos_contexto = models.JSONField(default=list)
    pdf_nome = models.CharField(max_length=500, blank=True, default="")
    pdf_secoes = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "sessao"

    def __str__(self):
        return self.sessao_id


class SessaoAdmin(admin.ModelAdmin):
    list_display = ("sessao_id", "titulo", "usuario", "criada_em")
