"""
Camada de abstração para provedores de LLM com tool-calling.

Suporta: Ollama (nativo), Gemini (google-genai).
"""

import inspect
import os
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from ollama import chat as ollama_chat


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


class OllamaProvider(LLMProvider):
    """Provedor usando ollama.chat nativo."""

    _KWARGS_TOPO = {"stream", "think", "logprobs", "top_logprobs", "format"}

    def __init__(self, modelo: str = "qwen3:8b"):
        self.modelo = modelo
        self.num_ctx = int(os.getenv("OLLAMA_NUM_CTX", "8192"))

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
        return ollama_chat(
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
        resposta = ollama_chat(
            model=self.modelo,
            messages=messages,
            options=options or None,
            **topo,
        )
        return resposta.message.content or ""


class GeminiProvider(LLMProvider):
    """Provedor usando google-genai com function calling."""

    def __init__(self, modelo: str = "gemini-3.8-flash"):
        self.modelo = modelo
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client()
        return self._client

    @staticmethod
    def _tipo_json_schema(annotation):
        if annotation is int:
            return "integer"
        if annotation is float:
            return "number"
        if annotation is bool:
            return "boolean"
        if annotation is list:
            return "array"
        if annotation is dict:
            return "object"
        return "string"

    def _funcao_para_declaracao(self, func: Callable) -> dict:
        sig = inspect.signature(func)
        propriedades = {}
        requeridos = []

        for nome, param in sig.parameters.items():
            tipo = self._tipo_json_schema(param.annotation)
            propriedades[nome] = {"type": tipo}
            if param.default is inspect.Parameter.empty:
                requeridos.append(nome)

        return {
            "type": "function",
            "name": func.__name__,
            "description": func.__doc__ or f"Executa {func.__name__}",
            "parameters": {
                "type": "object",
                "properties": propriedades,
                "required": requeridos,
            },
        }

    @staticmethod
    def _texto_final(steps):
        for step in reversed(list(steps)):
            if getattr(step, "type", None) == "function_call":
                continue
            conteudo = getattr(step, "content", None) or []
            for parte in conteudo:
                texto = getattr(parte, "text", None)
                if texto:
                    return texto
        return ""

    @staticmethod
    def _tool_calls_compat(steps):
        tool_calls = []
        for step in steps:
            if getattr(step, "type", None) != "function_call":
                continue

            class _MockCall:
                def __init__(self, name, arguments):
                    self.function = type(
                        "Function", (), {"name": name, "arguments": arguments}
                    )()

            tool_calls.append(_MockCall(step.name, step.arguments))
        return tool_calls or None

    def chat(
        self,
        messages: list[dict],
        tools: list[Callable] | None = None,
        **kwargs,
    ) -> Any:
        """Executa via Interactions API, suportando tool-calling em múltiplas etapas."""
        from google.genai import types

        client = self._get_client()
        ferramentas = [
            {"type": "function", **self._funcao_para_declaracao(t)}
            for t in (tools or [])
        ]

        interacao = client.interactions.create(
            model=self.modelo,
            input=messages[-1]["content"] if messages else "",
            tools=ferramentas,
            generation_config=types.GenerateContentConfig(
                temperature=kwargs.get("temperature", 0.2),
            ),
        )

        steps = list(interacao.steps)
        tool_calls_compat = self._tool_calls_compat(steps)

        while True:
            chamadas = [s for s in steps if getattr(s, "type", None) == "function_call"]
            if not chamadas:
                break

            resultados = []
            for chamada in chamadas:
                funcao = next(
                    (t for t in tools or [] if t.__name__ == chamada.name), None
                )
                if funcao is None:
                    raise ValueError(
                        f"Função {chamada.name} não registrada no provedor."
                    )

                resultado = funcao(**chamada.arguments)
                resultados.append(
                    {
                        "type": "function_result",
                        "name": chamada.name,
                        "call_id": chamada.id,
                        "result": [{"type": "text", "text": str(resultado)}],
                    }
                )

            interacao = client.interactions.create(
                model=self.modelo,
                previous_interaction_id=interacao.id,
                input=resultados,
                tools=ferramentas,
                generation_config=types.GenerateContentConfig(
                    temperature=kwargs.get("temperature", 0.2),
                ),
            )
            steps = list(interacao.steps)
            tool_calls_compat = self._tool_calls_compat(steps)

        class _MockMessage:
            def __init__(self, text: str, tool_calls=None):
                self.content = text
                self.tool_calls = tool_calls

        class _MockResponse:
            def __init__(self, message):
                self.message = message

        return _MockResponse(_MockMessage(self._texto_final(steps), tool_calls_compat))

    def chat_simple(
        self,
        messages: list[dict],
        **kwargs,
    ) -> str:
        """Chamada simples sem ferramentas via Interactions API."""
        from google.genai import types

        client = self._get_client()
        interacao = client.interactions.create(
            model=self.modelo,
            input=messages[-1]["content"] if messages else "",
            tools=None,
            generation_config=types.GenerateContentConfig(
                temperature=kwargs.get("temperature", 0.2),
            ),
        )
        return interacao.output_text or ""


def criar_provedor(nome: str | None = None) -> LLMProvider:
    """Escolhe o provedor conforme `nome` (ollama|gemini) ou a variável LLM_PROVIDER."""
    provider = (nome or os.getenv("LLM_PROVIDER", "ollama")).lower()
    modelo = os.getenv("MODELO_OLLAMA", "qwen3:8b")

    if provider == "gemini":
        return GeminiProvider(modelo=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"))
    return OllamaProvider(modelo=modelo)


provedor_padrao = criar_provedor()
