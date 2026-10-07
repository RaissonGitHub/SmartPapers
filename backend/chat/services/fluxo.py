import json
from collections.abc import Iterator
from contextvars import copy_context
from queue import Empty, Queue
from threading import Thread

from django.db import connections

TIPO_NDJSON = "application/x-ndjson"
INTERVALO_PING = 15.0

FIM = "fim"
FALHA = "falha"


def linha(dados: dict) -> bytes:
    """Serializa um evento como linha NDJSON."""
    return (json.dumps(dados, ensure_ascii=False) + "\n").encode("utf-8")


class Fluxo:
    """Executa o pipeline numa thread e publica os eventos conforme ocorrem."""

    def __init__(self):
        self._fila: Queue = Queue()
        self._thread: Thread | None = None

    def avancar(self, etapa: str, texto: str) -> None:
        self._fila.put({"tipo": "etapa", "etapa": etapa, "texto": texto})

    def _executar(self, alvo) -> None:
        from . import progresso

        progresso.definir_callback(self.avancar)
        try:
            self._fila.put({"tipo": FIM, "dados": alvo()})
        except BaseException as exc: 
            self._fila.put({"tipo": FALHA, "erro": exc})
        finally:
            progresso.limpar_callback()
            connections.close_all()

    def iniciar(self, alvo) -> None:
        """Dispara `alvo` na thread do pipeline."""
        contexto = copy_context()
        self._thread = Thread(
            target=lambda: contexto.run(self._executar, alvo),
            daemon=True,
            name="chat-agente",
        )
        self._thread.start()

    def eventos(self) -> Iterator[dict]:
        """Entrega os eventos até o fim (ou a falha) do pipeline."""
        while True:
            try:
                evento = self._fila.get(timeout=INTERVALO_PING)
            except Empty:
                yield {"tipo": "ping"}
                continue
            yield evento
            if evento["tipo"] in (FIM, FALHA):
                return

    @property
    def rodando(self) -> bool:
        """True enquanto o pipeline não terminou (cliente pode ter desistido)."""
        return self._thread is not None and self._thread.is_alive()