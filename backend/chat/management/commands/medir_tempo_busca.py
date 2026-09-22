"""Mede o tempo da etapa de busca vetorial (RNF01: <= 2s).

Uso:
    python manage.py medir_tempo_busca [--iteracoes 15] [--saida JSON]

Para cada consulta mede, separadamente:
    - geração do embedding (SPECTER2, em lote);
    - consulta ANN no pgvector (query pura, forçando a avaliação);
    - busca completa `buscar_artigos` (ANN + desserialização dos resultados),

Métricas por fase: mínimo, média, p95 e máximo, além do veredito em relação
à meta de 2 segundos. O resultado é salvo em JSON para o TCC.
"""

import json
import os
import statistics
import time
from datetime import datetime

from django.core.management.base import BaseCommand

from artigos.models import Artigo
from artigos.services.buscar_artigos_service import buscar_artigos
from artigos.services.gerar_embedding_service import gerar_embedding_lote
from pgvector.django import CosineDistance

QUERIES = [
    "Machine Learning for Personalized Recommendation of Scientific Papers",
    "Graph Based Approaches for Scientific Article Recommendation",
    "Large Language Models in Information Retrieval",
    "Collaborative Filtering Techniques in Recommender Systems",
    "Detection and Prevention of Face Spoofing Attacks in Biometric Systems",
]

META_SEGUNDOS = 2.0


def _p95(valores):
    if not valores:
        return 0.0
    if len(valores) < 2:
        return valores[0]
    return statistics.quantiles(valores, n=100, method="inclusive")[94]


def _resumo(valores):
    return {
        "min": round(min(valores), 4),
        "media": round(statistics.mean(valores), 4),
        "p95": round(_p95(valores), 4),
        "max": round(max(valores), 4),
    }


class Command(BaseCommand):
    help = "Mede a latência da etapa de busca vetorial."

    def add_arguments(self, parser):
        parser.add_argument(
            "--iteracoes",
            type=int,
            default=15,
            help="Número de execuções medidas por consulta (padrão: 15).",
        )
        parser.add_argument(
            "--saida",
            type=str,
            default="/code/experimentos/resultado_tempo.json",
            help="Caminho do JSON com o resultado.",
        )

    def _busca_pura(self, embedding, top_n):
        start = time.perf_counter()
        resultados = (
            Artigo.objects.exclude(embedding=None)
            .annotate(distancia=CosineDistance("embedding", embedding))
            .order_by("distancia")[:top_n]
        )
        list(resultados)
        return time.perf_counter() - start

    def handle(self, *args, **options):
        iteracoes = options["iteracoes"]
        saida = options["saida"]
        top_n = 5

        total = Artigo.objects.filter(embedding__isnull=False).count()
        self.stdout.write(
            self.style.WARNING(
                f"Base: {total} artigos com embedding | meta RNF01: <= {META_SEGUNDOS}s"
            )
        )

        self.stdout.write("Gerando embeddings das consultas (carrega o SPECTER2)…")
        t0 = time.perf_counter()
        embeddings = gerar_embedding_lote(QUERIES)
        t_emb_batch = time.perf_counter() - t0
        t_emb_por_consulta = t_emb_batch / len(QUERIES)
        self.stdout.write(
            f"  lote: {t_emb_batch:.2f}s | por consulta: {t_emb_por_consulta * 1000:.0f}ms"
        )

        self.stdout.write("Aquecendo (primeira busca)…")
        buscar_artigos(embedding=embeddings[0], top_n=top_n)
        self._busca_pura(embeddings[0], top_n)

        resultados = []
        linhas = []
        for consulta, embedding in zip(QUERIES, embeddings):
            tempos_db = []
            tempos_full = []
            for _ in range(iteracoes):
                tempos_db.append(self._busca_pura(embedding, top_n))
                t = time.perf_counter()
                buscar_artigos(embedding=embedding, top_n=top_n)
                tempos_full.append(time.perf_counter() - t)

            q_db = _resumo(tempos_db)
            q_full = _resumo(tempos_full)
            q_full["dentro_meta"] = q_full["p95"] <= META_SEGUNDOS
            registro = {
                "consulta": consulta,
                "iteracoes": iteracoes,
                "tempo_embedding_por_consulta": round(t_emb_por_consulta, 4),
                "tempo_db_segundos": q_db,
                "tempo_busca_completa_segundos": q_full,
            }
            resultados.append(registro)

            linha = (
                f"{consulta[:62]:<62} db(méd) {q_db['media'] * 1000:6.1f}ms | "
                f"completa {q_full['media'] * 1000:6.1f}ms | "
                f"p95 {q_full['p95'] * 1000:6.1f}ms | "
                f"{'OK' if q_full['dentro_meta'] else 'ACIMA DA META'}"
            )
            linhas.append(linha)
            self.stdout.write(linha)

        p95s = [r["tempo_busca_completa_segundos"]["p95"] for r in resultados]
        medias = [r["tempo_busca_completa_segundos"]["media"] for r in resultados]
        veredito = max(p95s) <= META_SEGUNDOS
        resumo_geral = {
            "meta_segundos": META_SEGUNDOS,
            "base_com_embedding": total,
            "iteracoes_por_consulta": iteracoes,
            "tempo_embedding_por_consulta_segundos": round(t_emb_por_consulta, 4),
            "busca_completa": {
                "media_geral": round(statistics.mean(medias), 4),
                "p95_maximo": round(max(p95s), 4),
                "dentro_da_meta": veredito,
            },
            "consultas": resultados,
            "gerado_em": datetime.now().isoformat(timespec="seconds"),
        }

        os.makedirs(os.path.dirname(saida), exist_ok=True)
        with open(saida, "w", encoding="utf-8") as f:
            json.dump(resumo_geral, f, ensure_ascii=False, indent=2)

        self.stdout.write(
            self.style.SUCCESS(
                f"\nVeredito RNF01: "
                f"{'CUMPRIDO (p95 <= 2s)' if veredito else 'NÃO CUMPRIDO'} "
                f"| p95 máximo: {max(p95s) * 1000:.1f}ms"
            )
        )
        self.stdout.write(f"Salvo em {saida}")