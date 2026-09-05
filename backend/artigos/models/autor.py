from django.contrib import admin
from django.db import models

from .base import Base


class Autor(Base):
    nome = models.CharField(max_length=255)

    openalex_id = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "autor"

    def __str__(self):
        return f"${self.openalex_id} - ${self.nome}"


class AutorAdmin(admin.ModelAdmin):
    list_display = ("nome", "openalex_id")
    search_fields = ("nome",)
