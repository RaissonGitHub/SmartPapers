from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class LLMProvider(ABC):
    """Interface comum para chamadas de LLM com e sem ferramentas."""

    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        tools: list[Callable] | None = None,
        **kwargs,
    ) -> Any:
        """Chama o modelo com ou sem tool-calling."""

    @abstractmethod
    def chat_simple(
        self,
        messages: list[dict],
        **kwargs,
    ) -> str:
        """Chamada simples sem ferramentas."""