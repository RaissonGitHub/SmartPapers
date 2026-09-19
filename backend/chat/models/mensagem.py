from django.contrib import admin
from django.db import models

from ..enumerations.papel import Papel
from .base import Base
from .sessao import Sessao


class Mensagem(Base):
    sessao = models.ForeignKey(
        Sessao,
        on_delete=models.CASCADE,
        related_name="mensagens",
    )
    papel = models.CharField(max_length=10, choices=Papel)
    conteudo = models.TextField()
    artigos = models.JSONField(default=list, blank=True)
    ferramenta_utilizada = models.BooleanField(default=False)
    pdf_nome = models.CharField(max_length=500, blank=True, default="")
    pdf_id = models.IntegerField(null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mensagem"
        ordering = ["criada_em", "id"]

    def __str__(self):
        return f"[{self.papel}] {self.conteudo[:60]}"


class MensagemAdmin(admin.ModelAdmin):
    list_display = ("sessao", "papel", "criada_em")
    list_filter = ("papel",)
