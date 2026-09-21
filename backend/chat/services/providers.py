"""Fábrica de provedores de LLM.

Ponto único que resolve o provedor pelo nome. Cada provedor vive em um módulo
próprio e carrega seu SDK de forma preguiçosa: Gemini não depende do Ollama e
vice-versa. Não há fallback implícito entre eles — o nome escolhido é atendido
exatamente ou um erro é retornado.
"""

import os

from .base import LLMProvider
from .gemini_provider import GeminiProvider, listar_modelos_gemini
from .ollama_provider import OllamaProvider

__all__ = [
    "LLMProvider",
    "OllamaProvider",
    "GeminiProvider",
    "listar_modelos_gemini",
    "criar_provedor",
    "usar_provedor",
]


def criar_provedor(
    nome: str | None = None,
    api_key: str | None = None,
    modelo: str | None = None,
) -> LLMProvider:
    """Cria o provedor pelo nome ('ollama' | 'gemini').

    Se `nome` for ausente, usa a variável de ambiente LLM_PROVIDER (padrão
    'ollama'). Nomes desconhecidos levantam erro em vez de cair em outro provedor.
    """
    provider = (nome or os.getenv("LLM_PROVIDER", "ollama")).strip().lower()

    if provider == "gemini":
        return GeminiProvider(
            modelo=modelo or os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
            api_key=api_key,
        )

    if provider == "ollama":
        return OllamaProvider(
            modelo=modelo or os.getenv("MODELO_OLLAMA", "qwen3:8b")
        )

    raise ValueError(
        f"Provedor desconhecido: {provider!r}. Use 'gemini' ou 'ollama'."
    )


_padrao: LLMProvider | None = None


def usar_provedor(provider: LLMProvider | None = None) -> LLMProvider:
    """Retorna o provedor informado ou o padrão configurado.

    O padrão só é criado no primeiro uso real (não no import do módulo), para
    que instalar/rodar apenas Google ou apenas Ollama não requeira o outro SDK.
    """
    global _padrao
    if provider is not None:
        return provider
    if _padrao is None:
        _padrao = criar_provedor()
    return _padrao