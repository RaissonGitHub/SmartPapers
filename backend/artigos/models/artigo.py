from typing import ClassVar

from django.contrib import admin
from django.db import models
from pgvector.django import HnswIndex, VectorField

from .autor import Autor
from .base import Base


class Artigo(Base):
    openalex_id = models.CharField(max_length=100, unique=True)
    titulo = models.CharField(max_length=500)
    resumo = models.TextField(blank=True)
    ano_publicacao = models.IntegerField(null=True, blank=True)
    area_conhecimento = models.CharField(max_length=255, blank=True)
    link_original = models.URLField(max_length=500, blank=True)
    fonte = models.CharField(max_length=100, default="openalex")
    embedding = VectorField(dimensions=768, null=True, blank=True)
    autores = models.ManyToManyField(
        Autor,
        through="ArtigoAutor",
        related_name="artigos",
    )

    class Meta:
        db_table = "artigo"
        indexes: ClassVar[list[models.Index]] = [
            HnswIndex(
                name="artigo_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            )
        ]

    def __str__(self):
        return self.titulo


class ArtigoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "ano_publicacao", "area_conhecimento", "fonte")
    search_fields = ("titulo", "resumo")
    list_filter = ("ano_publicacao", "area_conhecimento")
