import os
import threading
import time

from django.db.models import Max, Min
from pgvector.django import CosineDistance

from ..models.artigo import Artigo

SIMILARIDADE_MIN = float(os.getenv("SIMILARIDADE_MIN", "0"))
AREAS_CACHE_TTL = int(os.getenv("AREAS_CACHE_TTL", "300"))

_areas_cache: tuple[str, ...] | None = None
_areas_cache_criacao = 0.0
_areas_cache_lock = threading.Lock()


def intervalo_anos_artigos() -> tuple[int, int]:
    """Anos mínimo e máximo de publicação presentes na base.

    Retorna (0, 0) quando não há artigos com ano informado.
    """
    agregado = Artigo.objects.aggregate(
        minimo=Min("ano_publicacao"), maximo=Max("ano_publicacao")
    )
    minimo = agregado["minimo"] or 0
    maximo = agregado["maximo"] or 0
    if not minimo or not maximo:
        return 0, 0
    return minimo, maximo


def _areas_existentes() -> tuple[str, ...]:
    """Devolve as áreas da base, com cache de curta duração (TTL)."""
    global _areas_cache, _areas_cache_criacao
    agora = time.time()
    if _areas_cache is not None and agora - _areas_cache_criacao < AREAS_CACHE_TTL:
        return _areas_cache

    with _areas_cache_lock:
        if (
            _areas_cache is not None
            and agora - _areas_cache_criacao < AREAS_CACHE_TTL
        ):
            return _areas_cache
        areas = tuple(
            Artigo.objects.exclude(area_conhecimento="")
            .values_list("area_conhecimento", flat=True)
            .distinct()
        )
        _areas_cache = areas
        _areas_cache_criacao = time.time()
        return areas


def _normalizar_area_filtro(area: str) -> str | None:
    """
    Valida o filtro de área contra os valores reais existentes na base.

    O LLM às vezes devolve "áreas" que não existem na base (ex.: 'Biomedicine',
    quando a base tem 'Medicine'). Aplicar esse filtro literal zeraria a busca.
    Aqui a área só é mantida se houver correspondência parcial com um valor real.
    """
    if not area or not area.strip():
        return None
    candidata = area.strip().lower()
    areas_existentes = _areas_existentes()
    for existente in areas_existentes:
        ex = existente.lower()
        if candidata in ex or ex in candidata:
            return existente
    return None


def buscar_artigos(
    embedding: list[float],
    top_n: int = 10,
    ano_inicio: int = 0,
    ano_fim: int = 0,
    area: str = "",
) -> list[dict]:
    """
    Executa busca ANN por similaridade de cosseno no pgvector.

    Parâmetros:
        embedding   : vetor da consulta (768 dimensões)
        top_n       : número de resultados a retornar
        ano_inicio  : filtro de ano mínimo (opcional)
        ano_fim     : filtro de ano máximo (opcional)
        area        : filtro de área do conhecimento (opcional)

    Retorna lista de dicts com metadados dos artigos ordenados por similaridade.
    """
    qs = Artigo.objects.exclude(embedding=None)

    if ano_inicio:
        qs = qs.filter(ano_publicacao__gte=ano_inicio)
    if ano_fim:
        qs = qs.filter(ano_publicacao__lte=ano_fim)
    if area:
        area = _normalizar_area_filtro(area)
    if area:
        qs = qs.filter(area_conhecimento__icontains=area)

    resultados = (
        qs.annotate(distancia=CosineDistance("embedding", embedding))
        .filter(distancia__isnull=False)
        .order_by("distancia")
        .prefetch_related("autores")[:top_n]
    )

    artigos = []
    for artigo in resultados:
        similaridade = round((1 - float(artigo.distancia)) * 100, 1)
        if similaridade < SIMILARIDADE_MIN:
            continue
        autores = [a.nome for a in artigo.autores.all()]
        artigos.append(
            {
                "id": artigo.id,
                "openalex_id": artigo.openalex_id,
                "titulo": artigo.titulo,
                "resumo": artigo.resumo,
                "autores": autores,
                "ano_publicacao": artigo.ano_publicacao,
                "area_conhecimento": artigo.area_conhecimento,
                "link_original": artigo.link_original,
                "similaridade": similaridade,
            }
        )

    return artigos
