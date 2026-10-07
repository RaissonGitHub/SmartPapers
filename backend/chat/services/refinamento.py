"""
Refinamento da busca semântica.
"""

import os
import re

from .providers import LLMProvider, usar_provedor

MARCADOR_ADERENTES = "ARTIGOS_ADERENTES"

RERANK_VAZIO_SIM_MIN = float(os.getenv("RERANK_VAZIO_SIM_MIN", "70"))

_RE_ADERENTES = re.compile(rf"{MARCADOR_ADERENTES}\s*:\s*\[([^\]]*)\]", re.IGNORECASE)

PROMPT_RERANK = f"""Você é um revisor de relevância bibliográfica.

Uma lista numerada de artigos será fornecida, seguida da pergunta do usuário.
Analise aderência REAL de cada artigo à pergunta: não basta o artigo pertencer
à mesma área ampla; ele deve tratar substancialmente da questão específica.

Responda APENAS na última linha com:
{MARCADOR_ADERENTES}: [n, m, o]
na ordem de melhor para pior aderência. Se nenhum artigo for realmente aderente,
escreva {MARCADOR_ADERENTES}: [].
Essa linha é um metadado e NÃO deve aparecer adaptada; escreva-a literalmente na
última linha, sem textos após ela.
"""


def _resolver_provedor(provedor: LLMProvider | None = None) -> LLMProvider:
    return usar_provedor(provedor)


def _limpar_pensamento(texto: str) -> str:
    """Remove o bloco de raciocínio que modelos como qwen3 podem emitir."""
    if not texto:
        return texto
    if texto.lstrip().startswith("thinking"):
        marcador = " response"
        indice = texto.find(marcador)
        if indice != -1:
            texto = texto[indice + len(marcador) :]
    return texto.strip()


def _formatar_artigos(artigos: list[dict]) -> str:
    """Formata os artigos em texto simples para o rerank."""
    linhas = []
    for indice, artigo in enumerate(artigos, start=1):
        autores = ", ".join(artigo.get("autores", []) or []) or "Não informados"
        resumo = (artigo.get("resumo") or "")[:400].strip()
        linhas.append(
            f"[{indice}] {artigo['titulo']}\n"
            f"    Autores: {autores}\n"
            f"    Ano: {artigo.get('ano_publicacao') or 'N/A'} | "
            f"Área: {artigo.get('area_conhecimento') or 'N/A'} | "
            f"Relevância: {artigo.get('similaridade', 0)}%\n"
            f"    Resumo: {resumo}"
        )
    return "\n".join(linhas)


def _marcador_presente(texto: str) -> bool:
    """Indica se o modelo emitiu o marcador de aderência, mesmo que vazio."""
    return bool(_RE_ADERENTES.search(texto or ""))


def _parsear_indices(texto: str) -> list[int]:
    """Extrai os índices do marcador ARTIGOS_ADERENTES."""
    marcador = _RE_ADERENTES.search(texto or "")
    if not marcador:
        return []
    return [
        int(item)
        for item in re.split(r"[^0-9]+", marcador.group(1))
        if item.strip().isdigit()
    ]


def _ordenar_por_indices(artigos: list[dict], indices: list[int]) -> list[dict]:
    """Mantém a ordem do rerank, ignorando índices fora do intervalo."""
    vistos = set()
    reordenados = []
    for indice in indices:
        if 1 <= indice <= len(artigos) and indice not in vistos:
            vistos.add(indice)
            reordenados.append(artigos[indice - 1])
    return reordenados


def _melhor_similaridade(artigos: list[dict]) -> float:
    """Maior similaridade vetorial entre os candidatos da busca."""
    return max((artigo.get("similaridade") or 0.0 for artigo in artigos), default=0.0)


def rerank_por_aderencia(
    pergunta: str,
    artigos: list[dict],
    top_n: int,
    provedor: LLMProvider | None = None,
) -> list[dict]:
    """Reordena e filtra artigos por aderência real à pergunta."""
    p = _resolver_provedor(provedor)
    if len(artigos) <= 1:
        print(f"[REFINAMENTO] Menos de 2 artigos; retornando {len(artigos)} itens.")
        return artigos[:top_n]

    print(
        f"[REFINAMENTO] Reranking de {len(artigos)} artigos para pergunta: {pergunta[:120]}..."
    )
    contexto = _formatar_artigos(artigos)
    prompt = f"{contexto}\n\nPergunta do usuário: {pergunta}"

    try:
        resposta = p.chat_simple(
            messages=[
                {"role": "system", "content": PROMPT_RERANK},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        texto = _limpar_pensamento(resposta or "")
        indices = _parsear_indices(texto)
        print(f"[REFINAMENTO] Indices retornados pelo rerank: {indices}")
        if not indices and not _marcador_presente(texto):
            print("[REFINAMENTO] Marcador ausente; mantendo o ranking vetorial.")
            return artigos[:top_n]
        if not indices:
            if _melhor_similaridade(artigos) >= RERANK_VAZIO_SIM_MIN:
                print(
                    "[REFINAMENTO] Rerank vazio com candidatos fortes; "
                    "mantendo o ranking vetorial."
                )
                return artigos[:top_n]
            print("[REFINAMENTO] Modelo declarou nenhum artigo aderente.")
            return []
        ordenados = (_ordenar_por_indices(artigos, indices) or artigos)[:top_n]
        print(f"[REFINAMENTO] Resultado final do rerank: {len(ordenados)} artigos.")
        return ordenados
    except Exception as exc:
        print(f"[REFINAMENTO] Erro ao rerank: {exc}")
        return artigos[:top_n]
