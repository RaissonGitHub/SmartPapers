"""Persistência de conversas em sessões por usuário."""

import uuid

from chat.enumerations import Papel
from chat.models import Mensagem, Sessao

from .rag import processar_mensagem_usuario


def _usuario_autenticado(usuario):
    """Exige usuário autenticado: devolve o User ou levanta erro."""
    if usuario is None or not getattr(usuario, "is_authenticated", False):
        raise ValueError("Usuário autenticado é obrigatório para sessões de chat.")
    return usuario


def criar_sessao(usuario=None, titulo: str = "") -> Sessao:
    return Sessao.objects.create(
        usuario=_usuario_autenticado(usuario),
        sessao_id=str(uuid.uuid4()),
        titulo=(titulo or "")[:500],
    )


def obter_sessao(sessao_key, usuario=None):
    if not sessao_key:
        return None

    usuario = _usuario_autenticado(usuario)
    qs = Sessao.objects.filter(usuario=usuario)

    chave = str(sessao_key)
    if chave.isdigit():
        return qs.filter(pk=int(chave)).first()
    return qs.filter(sessao_id=chave).first()


def obter_ou_criar_sessao(sessao_key, usuario=None) -> Sessao:
    return obter_sessao(sessao_key, usuario) or criar_sessao(usuario)


def salvar_mensagem(
    sessao: Sessao,
    papel,
    conteudo: str,
    artigos=None,
    ferramenta_utilizada: bool = False,
) -> Mensagem:
    return Mensagem.objects.create(
        sessao=sessao,
        papel=papel,
        conteudo=conteudo,
        artigos=artigos or [],
        ferramenta_utilizada=ferramenta_utilizada,
    )


def historico_sessao(sessao: Sessao, max_mensagens: int = 20) -> list[dict]:
    """Converte mensagens anteriores em lista role/content para o LLM."""
    historico = []
    qs = sessao.mensagens.order_by("-criada_em", "-id")[:max_mensagens]
    for mensagem in reversed(list(qs)):
        role = "user" if mensagem.papel == Papel.USUARIO else "assistant"
        historico.append({"role": role, "content": mensagem.conteudo})
    return historico


def processar_e_salvar(
    mensagem: str,
    sessao_key=None,
    usuario=None,
    provider=None,
    requisicao: str | None = None,
    ano_inicio: int = 0,
    ano_fim: int = 0,
    area: str = "",
) -> dict:
    """Executa a conversa e persiste usuário + modelo na sessão."""
    sessao = obter_ou_criar_sessao(sessao_key, usuario)

    if not sessao.titulo:
        sessao.titulo = mensagem[:500]
        sessao.save(update_fields=["titulo"])

    historico = historico_sessao(sessao)

    salvar_mensagem(sessao, Papel.USUARIO, mensagem)

    resultado = processar_mensagem_usuario(
        mensagem=mensagem,
        requisicao=requisicao,
        provedor=provider,
        historico=historico,
        artigos_contexto=sessao.artigos_contexto,
        ano_inicio=ano_inicio,
        ano_fim=ano_fim,
        area=area,
    )

    artigos = resultado.get("artigos") or []
    salvar_mensagem(
        sessao,
        Papel.MODELO,
        resultado.get("resposta", ""),
        artigos=artigos,
        ferramenta_utilizada=resultado.get("ferramenta_utilizada", False),
    )

    if artigos:
        contexto = sessao.artigos_contexto
        ids_existentes = {a.get("id") for a in contexto}
        novos = [a for a in artigos if a.get("id") not in ids_existentes]
        if novos:
            sessao.artigos_contexto = contexto + novos
            sessao.save(update_fields=["artigos_contexto"])

    resultado["sessao_id"] = sessao.sessao_id
    resultado["sessao"] = sessao.id
    return resultado