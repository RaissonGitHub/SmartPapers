"""
Management command para coletar artigos do OpenAlex e gerar embeddings.

Uso:
    python manage.py coletar_openalex
    python manage.py coletar_openalex --total 10000
    python manage.py coletar_openalex --query "machine learning" --total 5000
    python manage.py coletar_openalex --ano-inicio 2020 --ano-fim 2026
    python manage.py coletar_openalex --apenas-embeddings  # só gera embeddings dos que faltam

Requer a variável de ambiente OPENALEX_API_KEY (chave gratuita em
https://openalex.org/settings/api). Desde fev/2026 a OpenAlex exige API key
em todas as requisições — o antigo parâmetro `mailto` foi descontinuado.
"""

import os
import time

import requests
from artigos.models import Artigo, ArtigoAutor, Autor
from django.core.management.base import BaseCommand

OPENALEX_URL = "https://api.openalex.org/works"
BATCH_SIZE = 100  # máximo atual permitido pelo OpenAlex por página (era 200)
EMBED_BATCH = 32  # artigos por lote de embedding (limitado pela RAM)


def carregar_modelo():
    """
    Wrapper do método oficial de embedding do SPECTER2 (adapter `proximity`,
    embedding CLS, com `[SEP]`, sem token_type_ids) — o MESMO usado pelas
    queries em runtime (`gerar_embedding_service`).

    Mantém a interface `.encode(textos, ...)` usada pelo fluxo de coleta.
    """
    from ...services.gerar_embedding_service import (
        _texto_embedding,
        gerar_embedding_lote,
    )

    class Specter2Wrapper:
        def encode(self, textos, show_progress_bar=False, batch_size=32):
            return gerar_embedding_lote(list(textos))

    return Specter2Wrapper()


def buscar_pagina(query, filtros, cursor, api_key, por_pagina):
    """Busca uma página de resultados no OpenAlex."""
    params = {
        "filter": filtros,
        "per-page": por_pagina,
        "cursor": cursor,
        "select": "id,title,abstract_inverted_index,publication_year,primary_location,authorships,primary_topic",
        "api_key": api_key,
    }
    if query:
        params["search"] = query

    resp = requests.get(OPENALEX_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def reconstruir_resumo(abstract_inverted_index):
    """
    O OpenAlex armazena o resumo como índice invertido.
    Esta função reconstrói o texto original.
    """
    if not abstract_inverted_index:
        return ""
    posicoes = []
    for palavra, indices in abstract_inverted_index.items():
        for i in indices:
            posicoes.append((i, palavra))
    posicoes.sort(key=lambda x: x[0])
    return " ".join(p[1] for p in posicoes)


def extrair_area(work):
    """
    Extrai a área do conhecimento principal do artigo via `primary_topic`.

    O campo `concepts` foi depreciado pela OpenAlex em favor de `topics`
    (hierarquia: domain -> field -> subfield -> topic). Usamos `field`
    como equivalente aproximado ao nível de granularidade que os
    `concepts` de level<=1 davam antes.
    """
    topic = work.get("primary_topic")
    if not topic:
        return ""
    campo = topic.get("field") or {}
    return campo.get("display_name", "") or topic.get("display_name", "")


def extrair_link(primary_location):
    """Extrai a URL do artigo original."""
    if not primary_location:
        return ""
    return primary_location.get("landing_page_url") or ""


def salvar_artigo(work):
    """Salva ou atualiza um artigo e seus autores no banco."""
    openalex_id = work.get("id", "").replace("https://openalex.org/", "")
    if not openalex_id:
        return None

    titulo = work.get("title") or ""
    if not titulo:
        return None

    resumo = reconstruir_resumo(work.get("abstract_inverted_index"))
    ano = work.get("publication_year")
    area = extrair_area(work)
    link = extrair_link(work.get("primary_location"))

    artigo, _ = Artigo.objects.update_or_create(
        openalex_id=openalex_id,
        defaults={
            "titulo": titulo[:500],
            "resumo": resumo,
            "ano_publicacao": ano,
            "area_conhecimento": area[:255],
            "link_original": link[:500],
            "fonte": "openalex",
        },
    )

    # Salvar autores
    for authorship in work.get("authorships", []):
        autor_data = authorship.get("author", {})
        autor_id = (autor_data.get("id") or "").replace("https://openalex.org/", "")
        autor_nome = autor_data.get("display_name", "")
        if autor_id and autor_nome:
            autor, _ = Autor.objects.get_or_create(
                openalex_id=autor_id,
                defaults={"nome": autor_nome[:255]},
            )
            ArtigoAutor.objects.get_or_create(artigo=artigo, autor=autor)

    return artigo


def gerar_embeddings(modelo, artigos):
    """Gera e salva embeddings para uma lista de artigos."""
    from ...services.gerar_embedding_service import _texto_embedding

    textos = [_texto_embedding(a.titulo, a.resumo) for a in artigos]
    vetores = modelo.encode(textos, show_progress_bar=False, batch_size=EMBED_BATCH)
    for artigo, vetor in zip(artigos, vetores):
        artigo.embedding = vetor.tolist()
        artigo.save(update_fields=["embedding"])


class Command(BaseCommand):
    help = "Coleta artigos do OpenAlex e gera embeddings com allenai/specter2"

    def add_arguments(self, parser):
        parser.add_argument(
            "--total",
            type=int,
            default=50000,
            help="Total de artigos a coletar (padrão: 50000)",
        )
        parser.add_argument(
            "--query",
            type=str,
            default="",
            help="Termo de busca (padrão: sem filtro, coleta geral)",
        )
        parser.add_argument(
            "--ano-inicio",
            type=int,
            default=2015,
            help="Ano de publicação mínimo (padrão: 2015)",
        )
        parser.add_argument(
            "--ano-fim",
            type=int,
            default=2026,
            help="Ano de publicação máximo (padrão: 2026)",
        )
        parser.add_argument(
            "--apenas-embeddings",
            action="store_true",
            help="Pula a coleta e só gera embeddings dos artigos que ainda não têm",
        )

    def handle(self, *args, **options):
        total_alvo = options["total"]
        query = options["query"]
        ano_inicio = options["ano_inicio"]
        ano_fim = options["ano_fim"]
        apenas_embeddings = options["apenas_embeddings"]
        api_key = os.getenv("OPENALEX_API_KEY", "")

        if not apenas_embeddings and not api_key:
            self.stderr.write(
                "⚠️  OPENALEX_API_KEY não definida. Desde fev/2026 a OpenAlex exige "
                "API key em todas as requisições (chave gratuita em "
                "https://openalex.org/settings/api). Requisições sem key podem "
                "falhar ou cair em limites muito mais restritos."
            )

        modelo = carregar_modelo()

        # ── Modo: apenas gerar embeddings pendentes ──────────────────────────
        if apenas_embeddings:
            self.stdout.write("🔍 Buscando artigos sem embedding...")
            pendentes = list(Artigo.objects.filter(embedding=None))
            self.stdout.write(f"📄 {len(pendentes)} artigos sem embedding.")
            self._processar_embeddings(modelo, pendentes)
            self.stdout.write(self.style.SUCCESS("✅ Embeddings concluídos."))
            return

        # ── Modo: coletar + embeddings ────────────────────────────────────────
        filtros = (
            f"publication_year:{ano_inicio}-{ano_fim},has_abstract:true,type:article"
        )

        self.stdout.write(
            f"🚀 Iniciando coleta: alvo={total_alvo} | "
            f"anos={ano_inicio}-{ano_fim} | query='{query or 'geral'}'"
        )

        cursor = "*"
        coletados = 0
        erros = 0
        sem_embedding = []

        while coletados < total_alvo:
            por_pagina = min(BATCH_SIZE, total_alvo - coletados)

            try:
                dados = buscar_pagina(query, filtros, cursor, api_key, por_pagina)
            except Exception as e:
                self.stderr.write(
                    f"⚠️  Erro na requisição: {e}. Tentando novamente em 10s..."
                )
                time.sleep(10)
                erros += 1
                if erros > 5:
                    self.stderr.write("❌ Muitos erros consecutivos. Abortando coleta.")
                    break
                continue

            erros = 0
            works = dados.get("results", [])
            if not works:
                self.stdout.write("📭 Sem mais resultados.")
                break

            # Salvar lote no banco
            lote_artigos = []
            for work in works:
                artigo = salvar_artigo(work)
                if artigo:
                    lote_artigos.append(artigo)

            coletados += len(lote_artigos)
            sem_embedding.extend(lote_artigos)

            self.stdout.write(
                f"📥 {coletados}/{total_alvo} artigos salvos "
                f"({len(lote_artigos)} neste lote)"
            )

            # Gerar embeddings em lotes para não acumular na RAM
            if len(sem_embedding) >= EMBED_BATCH * 4:
                self._processar_embeddings(modelo, sem_embedding)
                sem_embedding = []

            # Paginação via cursor
            cursor = dados.get("meta", {}).get("next_cursor")
            if not cursor:
                self.stdout.write("📭 Fim dos resultados disponíveis.")
                break

            time.sleep(0.1)  # respeitar rate limit do OpenAlex

        # Processar embeddings restantes
        if sem_embedding:
            self._processar_embeddings(modelo, sem_embedding)

        total_banco = Artigo.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Coleta concluída! "
                f"{coletados} artigos coletados | "
                f"{total_banco} total no banco."
            )
        )

    def _processar_embeddings(self, modelo, artigos):
        """Gera embeddings em sublotes e exibe progresso."""
        total = len(artigos)
        self.stdout.write(f"🧠 Gerando embeddings para {total} artigos...")
        for i in range(0, total, EMBED_BATCH):
            lote = artigos[i : i + EMBED_BATCH]
            gerar_embeddings(modelo, lote)
            self.stdout.write(f"   embedding {min(i + EMBED_BATCH, total)}/{total}")
        self.stdout.write("✅ Embeddings salvos.")
