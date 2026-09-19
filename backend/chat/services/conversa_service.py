"""Persistência de conversas em sessões por usuário."""

import uuid

from chat.enumerations import Papel
from chat.models import Mensagem, Sessao

from .pdf_service import processar_pdf
from .rag import processar_mensagem_usuario, selecionar_pdf


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
    pdf_nome: str = "",
    pdf_id: int | None = None,
) -> Mensagem:
    return Mensagem.objects.create(
        sessao=sessao,
        papel=papel,
        conteudo=conteudo,
        artigos=artigos or [],
        ferramenta_utilizada=ferramenta_utilizada,
        pdf_nome=(pdf_nome or "")[:500],
        pdf_id=pdf_id,
    )


def serializar_mensagem(mensagem: Mensagem) -> dict:
    return {
        "id": mensagem.id,
        "papel": mensagem.papel,
        "conteudo": mensagem.conteudo,
        "artigos": mensagem.artigos,
        "ferramenta_utilizada": mensagem.ferramenta_utilizada,
        "pdf_nome": mensagem.pdf_nome,
        "pdf_id": mensagem.pdf_id,
        "criada_em": mensagem.criada_em.isoformat(),
    }


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
    pdf=None,
) -> dict:
    """Executa a conversa e persiste usuário + modelo na sessão."""
    sessao = obter_ou_criar_sessao(sessao_key, usuario)

    if not sessao.titulo:
        sessao.titulo = mensagem[:500]
        sessao.save(update_fields=["titulo"])

    pdf_nome = (getattr(pdf, "name", "") or "")[:500] if pdf else ""
    pdfs = list(getattr(sessao, "pdfs", None) or [])
    if pdf:
        secoes_pdf = processar_pdf(pdf, [mensagem], provider)
        pdf_id = max((item.get("id", 0) for item in pdfs), default=0) + 1
        descricao = next(
            (
                (secao.get("resumo") or "")[:180]
                for secao in secoes_pdf
                if secao.get("tipo", "conteudo") != "referencia"
            ),
            "",
        )
        pdfs.append(
            {
                "id": pdf_id,
                "nome": pdf_nome,
                "ordem": len(pdfs) + 1,
                "descricao": descricao,
                "secoes": secoes_pdf,
            }
        )
        sessao.pdf_nome = pdf_nome
        sessao.pdf_secoes = secoes_pdf
        sessao.pdfs = pdfs
        sessao.save(update_fields=["pdf_nome", "pdf_secoes", "pdfs"])
    else:
        if not pdfs and (sessao.pdf_nome or sessao.pdf_secoes):
            pdfs = [
                {
                    "id": 1,
                    "nome": sessao.pdf_nome,
                    "ordem": 1,
                    "descricao": "",
                    "secoes": sessao.pdf_secoes or [],
                }
            ]
        pdf_id, secoes_pdf = selecionar_pdf(pdfs, mensagem, provider)
        pdf_selecionado = next(
            (item for item in pdfs if item.get("id") == pdf_id), None
        )
        pdf_nome = (pdf_selecionado or {}).get("nome", "")[:500]

    historico = historico_sessao(sessao)

    mensagem_usuario = salvar_mensagem(
        sessao, Papel.USUARIO, mensagem, pdf_nome=pdf_nome, pdf_id=pdf_id
    )

    resultado = processar_mensagem_usuario(
        mensagem=mensagem,
        requisicao=requisicao,
        provedor=provider,
        historico=historico,
        artigos_contexto=sessao.artigos_contexto,
        pdf_catalogo=pdfs,
        pdf_secoes=secoes_pdf,
        ano_inicio=ano_inicio,
        ano_fim=ano_fim,
        area=area,
    )

    artigos = resultado.get("artigos") or []
    mensagem_modelo = salvar_mensagem(
        sessao,
        Papel.MODELO,
        resultado.get("resposta", ""),
        artigos=artigos,
        ferramenta_utilizada=resultado.get("ferramenta_utilizada", False),
        pdf_id=pdf_id,
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
    resultado["mensagens"] = [
        serializar_mensagem(mensagem_usuario),
        serializar_mensagem(mensagem_modelo),
    ]
    return resultado