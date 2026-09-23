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
    if sys.argv[1:2] == ["runserver"]:
        return os.environ.get("RUN_MAIN") == "true" or "--noreload" in sys.argv
    if os.path.basename(sys.argv[0] or "").startswith("gunicorn"):
        return True
    return False


class ArtigosConfig(AppConfig):
    name = "artigos"

    def ready(self):
        if not _deve_preaquecer():
            return
        # No gunicorn (com --preload) o ready() roda só no master, uma vez:
        # carregar o SPECTER2 de forma síncrona garante o modelo pronto antes
        # do fork dos workers (sem thread/fork concorrente).
        if os.path.basename(sys.argv[0] or "").startswith("gunicorn"):
            _preaquecer()
            return
        threading.Thread(
            target=_preaquecer,
            name="preaquecimento-specter2",
            daemon=True,
        ).start()