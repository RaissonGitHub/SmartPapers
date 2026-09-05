from django.contrib import admin
from django.db import models

from .base import Base


class Sessao(Base):
    sessao_id = models.CharField(max_length=100, unique=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    artigos_contexto = models.JSONField(default=list)

    class Meta:
        db_table = "sessao"

    def __str__(self):
        return self.sessao_id


class SessaoAdmin(admin.ModelAdmin):
    list_display = ("sessao_id", "criada_em")
