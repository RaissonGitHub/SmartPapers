"""Provedor Ollama (modelo local), totalmente isolado.

Importa o pacote `ollama` somente na instanciação, para que quem usa apenas
Gemini não precise tê-lo instalado.
"""

import os
from collections.abc import Callable
from typing import Any

from .base import LLMProvider


class OllamaProvider(LLMProvider):
    """Provedor usando ollama.chat nativo."""

    _KWARGS_TOPO = {"stream", "think", "logprobs", "top_logprobs", "format"}

    def __init__(self, modelo: str = "qwen3:8b"):
        self.modelo = modelo
        self.num_ctx = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
        self.timeout = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
        from ollama import Client

        self._cliente = Client(
            host=os.getenv("OLLAMA_HOST"),
            timeout=self.timeout,
        )

    @staticmethod
    def _split_kwargs(kwargs: dict) -> tuple[dict, dict]:
        topo = {k: v for k, v in kwargs.items() if k in OllamaProvider._KWARGS_TOPO}
        options = {
            k: v for k, v in kwargs.items() if k not in OllamaProvider._KWARGS_TOPO
        }
        return topo, options

    def chat(
        self,
        messages: list[dict],
        tools: list[Callable] | None = None,
        **kwargs,
    ) -> Any:
        topo, options = self._split_kwargs(kwargs)
        options.setdefault("num_ctx", self.num_ctx)
        return self._cliente.chat(
            model=self.modelo,
            messages=messages,
            tools=tools,
            options=options or None,
            **topo,
        )

    def chat_simple(
        self,
        messages: list[dict],
        **kwargs,
    ) -> str:
        topo, options = self._split_kwargs(kwargs)
        options.setdefault("num_ctx", self.num_ctx)
        resposta = self._cliente.chat(
            model=self.modelo,
            messages=messages,
            options=options or None,
            **topo,
        )
        return resposta.message.content or ""