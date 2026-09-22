"""Provedor Google Gemini (API oficial google-genai), totalmente isolado.

Importa o pacote `google-genai` apenas quando necessário (instanciação e
chamadas), para que quem usa apenas Ollama não precise tê-lo instalado.
"""

import inspect
from collections.abc import Callable
from typing import Any

from .base import LLMProvider
from .cancelamento import checar_cancelamento


class GeminiProvider(LLMProvider):
    """Provedor usando google-genai com function calling (generate_content)."""

    def __init__(self, modelo: str = "gemini-3.8-flash", api_key: str | None = None):
        self.modelo = modelo
        self.api_key = api_key
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai

            if self.api_key:
                self._client = genai.Client(api_key=self.api_key)
            else:
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

    @staticmethod
    def _system_instruction(messages: list[dict]) -> str | None:
        blocos = [
            m.get("content", "") for m in messages if m.get("role") == "system"
        ]
        return "\n\n".join(blocos).strip() or None

    @staticmethod
    def _montar_contents(messages: list[dict]):
        """Converte mensagens role/content em `Content` do Gemini.

        A role "tool" é tratada como texto de usuário para manter compatibilidade
        com o histórico usado na geração final da resposta.
        """
        from google.genai import types

        conteudos = []
        for mensagem in messages:
            role = mensagem.get("role")
            if role == "system":
                continue
            conteudo = mensagem.get("content", "")
            if not conteudo:
                continue
            role_gemini = "model" if role == "assistant" else "user"
            conteudos.append(
                types.Content(
                    role=role_gemini,
                    parts=[types.Part(text=str(conteudo))],
                )
            )
        return conteudos

    def _ferramentas_api(self, funcs: list[Callable] | None):
        """Converte funções Python em `Tool` de function_declarations do Gemini."""
        from google.genai import types

        declaracoes = []
        for func in funcs or []:
            sig = inspect.signature(func)
            propriedades = {}
            requeridos = []
            for nome, param in sig.parameters.items():
                propriedades[nome] = {"type": self._tipo_json_schema(param.annotation)}
                if param.default is inspect.Parameter.empty:
                    requeridos.append(nome)

            declaracoes.append(
                types.FunctionDeclaration(
                    name=func.__name__,
                    description=func.__doc__ or f"Executa {func.__name__}",
                    parameters_json_schema={
                        "type": "object",
                        "properties": propriedades,
                        "required": requeridos,
                    },
                )
            )
        return (
            [types.Tool(function_declarations=declaracoes)] if declaracoes else None
        )

    @staticmethod
    def _resposta_para_mock(response):
        """Converte a resposta do Gemini no formato esperado pela camada RAG."""
        from google.genai import types

        texto = ""
        tool_calls = []

        class _MockCall:
            def __init__(self, name, arguments):
                self.function = type(
                    "Function", (), {"name": name, "arguments": arguments}
                )()

        for candidate in getattr(response, "candidates", None) or []:
            for parte in (candidate.content.parts or []):
                chamada = getattr(parte, "function_call", None)
                texto_parte = getattr(parte, "text", None)
                if chamada:
                    tool_calls.append(_MockCall(chamada.name, chamada.args))
                elif texto_parte:
                    texto += texto_parte

        class _MockMessage:
            def __init__(self, text: str, tool_calls=None):
                self.content = text
                self.tool_calls = tool_calls

        class _MockResponse:
            def __init__(self, message):
                self.message = message

        return _MockResponse(_MockMessage(texto.strip(), tool_calls or None))

    @staticmethod
    def _e_multiturn_nao_suportado(exc) -> bool:
        """True quando o modelo rejeita conversa com histórico (multiturn)."""
        try:
            from google.genai import errors as erros_genai
        except ImportError:
            return False
        if isinstance(exc, erros_genai.APIError) and exc.code == 400:
            return "multiturn" in str(exc).lower()
        return False

    @staticmethod
    def _ultimo_turno(messages: list[dict]) -> list[dict]:
        """Mantém apenas o turno mais recente para modelos single-turn."""
        for mensagem in reversed(messages):
            if mensagem.get("role") in ("user", "tool"):
                return [mensagem]
        return messages[-1:] if messages else []

    def _gerar(
        self,
        client,
        messages: list[dict],
        config,
    ):
        """generate_content com degradação para modelos que só aceitam 1 turno."""
        checar_cancelamento()
        try:
            return client.models.generate_content(
                model=self.modelo,
                contents=self._montar_contents(messages),
                config=config,
            )
        except Exception as exc:
            if not self._e_multiturn_nao_suportado(exc):
                raise
            return client.models.generate_content(
                model=self.modelo,
                contents=self._montar_contents(self._ultimo_turno(messages)),
                config=config,
            )

    def chat(
        self,
        messages: list[dict],
        tools: list[Callable] | None = None,
        **kwargs,
    ) -> Any:
        """Chama o modelo com tool-calling sem executar as ferramentas.

        Retorna resposta com `.message.tool_calls` (mesmo contrato do Ollama);
        a execução das ferramentas fica a cargo da camada RAG.
        """
        from google.genai import types

        client = self._get_client()
        config = types.GenerateContentConfig(
            temperature=kwargs.get("temperature", 0.2),
            system_instruction=self._system_instruction(messages),
            tools=self._ferramentas_api(tools),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        )
        response = self._gerar(client, messages, config)
        return self._resposta_para_mock(response)

    def chat_simple(
        self,
        messages: list[dict],
        **kwargs,
    ) -> str:
        """Chamada simples sem ferramentas."""
        from google.genai import types

        client = self._get_client()
        config = types.GenerateContentConfig(
            temperature=kwargs.get("temperature", 0.2),
            system_instruction=self._system_instruction(messages),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        )
        response = self._gerar(client, messages, config)
        return self._resposta_para_mock(response).message.content


def listar_modelos_gemini(api_key: str) -> list[dict]:
    """Lista modelos geradores do Gemini usando a chave fornecida pelo usuário.

    A chave nunca é persistida: o cliente é criado apenas para esta chamada.

    Filtra modelos não utilizáveis para conversas:
    - "preview" (single-turn apenas, sem multiturn);
    - gerações aposentadas para contas novas (ex.: gemini-1.x / gemini-2.x).
    """
    from google import genai

    client = genai.Client(api_key=api_key)
    modelos = []
    for modelo in client.models.list():
        acoes = [str(a) for a in (getattr(modelo, "supported_actions", None) or [])]
        if "generatecontent" not in {a.lower() for a in acoes}:
            continue
        nome = (getattr(modelo, "name", "") or "").removeprefix("models/")
        nome_lower = nome.lower()
        if "preview" in nome_lower:
            continue
        if any(
            nome_lower.startswith(prefixo)
            for prefixo in ("gemini-1.", "gemini-2.")
        ):
            continue
        modelos.append(
            {
                "name": nome,
                "display_name": getattr(modelo, "display_name", "") or nome,
                "supported_actions": acoes,
            }
        )
    modelos.sort(key=lambda item: item.get("display_name") or "")
    return modelos