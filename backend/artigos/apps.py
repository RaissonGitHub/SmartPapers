import os
import sys
import threading

from django.apps import AppConfig


def _preaquecer():
    try:
        from artigos.services.gerar_embedding_service import gerar_embedding

        gerar_embedding("", "")
    except Exception:
        # Falha no pré-aquecimento não deve derrubar o servidor; o modelo
        # continua sendo carregado preguiçosamente no primeiro uso.
        pass


def _deve_preaquecer() -> bool:
    if os.getenv("PREAQUECER_EMBEDDINGS", "1").strip().lower() not in (
        "1",
        "true",
        "yes",
        "on",
    ):
        return False
    if sys.argv[1:2] != ["runserver"]:
        return False
    if os.environ.get("RUN_MAIN") == "true":
        return True
    return "--noreload" in sys.argv


class ArtigosConfig(AppConfig):
    name = "artigos"

    def ready(self):
        if _deve_preaquecer():
            threading.Thread(
                target=_preaquecer,
                name="preaquecimento-specter2",
                daemon=True,
            ).start()