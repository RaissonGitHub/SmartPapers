"""Mede a recuperação do RAG com PDF para um conjunto fixo de consultas.

Uso:
    python manage.py medir_retrieval <caminho_do_pdf> [--saida JSON]

O mesmo PDF é processado uma vez e, para cada consulta, são registrados:
    - consultas usadas no merge;
    - candidate set (id + similaridade vetorial, antes do rerank);
    - Top-K final (depois do rerank).

O resultado é salvo em JSON para montar as tabelas de comparação do TCC.
"""

import json
import os
from datetime import datetime

from django.core.management.base import BaseCommand

from chat.services.pdf_service import extrair_texto_pdf, secoes_processadas, secoes_relevantes
from chat.services.rag import PDF_SECOES_BUSCA_MAX, _buscar_dupla_artigos
from chat.services.refinamento import reformular_busca

QUERIES = [
    {
        "rotulo": "A_ampla",
        "pergunta": "Quero artigos sobre sistemas de recomendação.",
    },
    {
        "rotulo": "B_metodologica",
        "pergunta": (
            "Quero artigos que utilizem relações entre autores para melhorar "
            "a recomendação de artigos científicos."
        ),
    },
    {
        "rotulo": "C_especifica",
        "pergunta": (
            "Quero artigos sobre recomendação de artigos científicos que "
            "utilizem informações sobre as preferências ou histórico dos "
            "pesquisadores."
        ),
    },
]


class Command(BaseCommand):
    help = "Mede candidate set e Top-K do RAG com PDF para consultas fixas."

    def add_arguments(self, parser):
        parser.add_argument("pdf_path", type=str)
        parser.add_argument(
            "--saida",
            type=str,
            default="/code/experimentos/resultado_retrieval.json",
        )

    def handle(self, *args, **options):
        pdf_path = options["pdf_path"]
        saida = options["saida"]

        if not os.path.isfile(pdf_path):
            self.stderr.write(f"Arquivo não encontrado: {pdf_path}")
            return

        with open(pdf_path, "rb") as arquivo:
            texto = extrair_texto_pdf(arquivo)
        if not texto.strip():
            self.stderr.write("Nenhum texto extraído do PDF.")
            return

        self.stdout.write("Processando seções do PDF (1x)...")
        secoes = secoes_processadas(texto)
        self.stdout.write(f"Total de seções: {len(secoes)}")

        resultado = {
            "pdf": os.path.basename(pdf_path),
            "gerado_em": datetime.now().isoformat(timespec="seconds"),
            "limite_consultas_pdf": PDF_SECOES_BUSCA_MAX,
            "consultas": [],
        }

        for item in QUERIES:
            rotulo = item["rotulo"]
            pergunta = item["pergunta"]
            self.stdout.write(f"\n--- Consulta {rotulo}: {pergunta}")

            relevantes = secoes_relevantes(secoes, [pergunta])
            consultas_pdf = [
                s.get("texto") or s.get("resumo") or "" for s in relevantes
            ]
            self.stdout.write(
                f"Seções relevantes para a consulta: {len(consultas_pdf)}"
            )

            titulo_en = reformular_busca(pergunta)
            self.stdout.write(f"Título EN: {titulo_en}")

            artigos, medicao = _buscar_dupla_artigos(
                search_title_en=titulo_en,
                texto_original_usuario=pergunta,
                provedor=None,
                consultas_pdf=consultas_pdf,
                retornar_medicao=True,
            )

            registro = {
                "rotulo": rotulo,
                "pergunta": pergunta,
                "candidate_set": medicao["candidate_set"],
                "top_k_final": medicao["top_k_final"],
                "top_k_ids": [a["id"] for a in medicao["top_k_final"]],
            }
            resultado["consultas"].append(registro)
            self.stdout.write(
                f"Top-K: {[a['id'] for a in medicao['top_k_final']]}"
            )

        os.makedirs(os.path.dirname(saida), exist_ok=True)
        with open(saida, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)
        self.stdout.write(self.style.SUCCESS(f"Salvo em {saida}"))