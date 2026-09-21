from rest_framework import serializers


class AgentChatRequestSerializer(serializers.Serializer):
    """Campos aceitos pelo POST /chat/agente/ (exibidos no formulário do DRF)."""

    mensagem = serializers.CharField(
        help_text="Pergunta ou comando enviado ao agente (obrigatório)."
    )
    provider = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="'ollama' ou 'gemini'. Ausente = provedor padrão (LLM_PROVIDER).",
    )
    api_key = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
        help_text="Chave da API do Google (Gemini). Usada apenas nesta requisição.",
    )
    modelo = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
        help_text="Nome do modelo do Gemini selecionado pelo usuário.",
    )
    requisicao = serializers.ChoiceField(
        choices=("", "busca", "resposta"),
        required=False,
        allow_blank=True,
        help_text="Força a intenção: 'busca', 'resposta' ou ausente (modelo decide).",
    )
    sessao_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="UUID da sessão existente. Ausente = cria nova sessão.",
    )
    ano_inicio = serializers.IntegerField(
        required=False,
        min_value=0,
        allow_null=True,
        help_text="Filtro: ano mínimo dos artigos (0 = sem limite).",
    )
    ano_fim = serializers.IntegerField(
        required=False,
        min_value=0,
        allow_null=True,
        help_text="Filtro: ano máximo dos artigos (0 = sem limite).",
    )
    area = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Filtro: área do conhecimento dos artigos (vazio = todas).",
    )
    pdf = serializers.FileField(
        required=False,
        allow_null=True,
        help_text="Arquivo PDF anexado (opcional). Sem mensagem, o envio é rejeitado.",
    )