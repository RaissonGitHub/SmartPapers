"""
Refinamento da busca semântica.

Etapas que elevam a qualidade da recuperação vetorial:

  1. classificar_necessidade_busca : decide via LLM se a mensagem exige busca
     de artigos ou pode ser respondida diretamente.
  2. reformular_busca               : converte o pedido do usuário (PT) em uma
     query acadêmica em INGLÊS estilo 'título de paper'.
  3. rerank_por_aderencia           : reordena/filtra o top-N mergido da busca
     dupla pela aderência REAL à pergunta.
"""

import os
import re

from .providers import LLMProvider, usar_provedor

MODELO_OLLAMA = os.getenv("MODELO_OLLAMA", "qwen3:8b")
MARCADOR_ADERENTES = "ARTIGOS_ADERENTES"

_RE_ADERENTES = re.compile(rf"{MARCADOR_ADERENTES}\s*:\s*\[([^\]]*)\]", re.IGNORECASE)

PROMPT_REFORMULAR = (
    "Converta pedidos de busca do usuário em uma consulta acadêmica em inglês, "
    "preservando o objetivo e os conceitos específicos. Não generalize o tema e "
    "não responda com uma única palavra: expanda expressões vagas com termos de "
    "literatura do domínio, produzindo um título de paper informativo (3 a 8 "
    "palavras). Para ensino, por exemplo, use teaching methods, pedagogical "
    "strategies, lesson planning ou classroom practice conforme o pedido. "
    "Retorne apenas uma linha de consulta, sem explicação.\n"
    "Exemplos:\n"
    "- 'artigos de química industrial e sustentabilidade' -> "
    "'Sustainable Industrial Chemistry: Green Technologies and Environmental Practices'\n"
    "- 'procure sobre smartphones' -> "
    "'Smartphone Use and Its Impact on Health and Daily Life'"
)

PROMPT_DECIDIR_BUSCA = (
    "Você decide se a mensagem de um usuário, enviada a um assistente acadêmico de busca de "
    "artigos científicos, deve disparar uma busca por artigos no banco ou pode ser respondida "
    "diretamente.\n"
    "Responda APENAS com UMA palavra: buscar ou responder.\n\n"
    "- responda 'buscar' quando o usuário: pedir artigos, papers, estudos, referências ou "
    "publicações; perguntar algo que só a literatura científica responde; ou enviar apenas "
    "um tópico solto indicando que quer achar artigos sobre o assunto.\n"
    "- responda 'responder' quando for uma dúvida de conhecimento geral ou conceitual, que dá "
    "para responder sem fontes.\n"
    "Em caso de dúvida, prefira 'responder' a não ser que haja interesse explícito em fontes."
)

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


def _remover_aspas(texto: str) -> str:
    """Remove aspas que circundam a query gerada."""
    texto = texto.strip()
    if len(texto) >= 2 and texto[0] in "\"'“«" and texto[-1] in "\"'”»":
        return texto[1:-1].strip()
    return texto


def reformular_busca(texto: str, provedor: LLMProvider | None = None) -> str:
    """Traduz a busca para inglês em estilo de título acadêmico."""
    p = _resolver_provedor(provedor)
    if not texto or not texto.strip():
        return texto

    print(f"[REFINAMENTO] Reformulando busca: {texto[:120]}...")
    try:
        resposta = p.chat_simple(
            messages=[
                {"role": "system", "content": PROMPT_REFORMULAR},
                {"role": "user", "content": texto},
            ],
            temperature=0,
        )
        query = _remover_aspas(_limpar_pensamento(resposta or ""))
        palavras = query.split()
        if 3 <= len(palavras) <= 12:
            print(f"[REFINAMENTO] Query reformulada: {query}")
            return query
    except Exception as exc:
        print(f"[REFINAMENTO] Erro ao reformular busca: {exc}")
        pass

    print(f"[REFINAMENTO] Mantendo texto original: {texto.strip()}")
    return texto.strip()


def classificar_necessidade_busca(
    texto: str, provedor: LLMProvider | None = None
) -> bool | None:
    """Decide se a mensagem exige busca científica ou resposta direta."""
    p = _resolver_provedor(provedor)
    if not texto or not texto.strip():
        return False

    print(f"[REFINAMENTO] Classificando necessidade de busca: {texto[:120]}...")
    try:
        resposta = p.chat_simple(
            messages=[
                {"role": "system", "content": PROMPT_DECIDIR_BUSCA},
                {"role": "user", "content": texto},
            ],
            temperature=0,
        )
        escolha = _limpar_pensamento(resposta or "").lower()
        primeira = re.sub(r"[^a-zà-ú]", "", escolha.split(" ", 1)[0]) if escolha else ""
        print(f"[REFINAMENTO] Resposta do classificador: {escolha!r}")
        if primeira == "buscar":
            return True
        if primeira in ("responder", "aprofundar"):
            return False
    except Exception as exc:
        print(f"[REFINAMENTO] Erro ao classificar busca: {exc}")
        pass

    return None


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

    print(f"[REFINAMENTO] Reranking de {len(artigos)} artigos para pergunta: {pergunta[:120]}...")
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
        if not indices:
            print("[REFINAMENTO] Nenhum artigo aderente encontrado pelo rerank.")
            return []
        ordenados = (_ordenar_por_indices(artigos, indices) or artigos)[:top_n]
        print(f"[REFINAMENTO] Resultado final do rerank: {len(ordenados)} artigos.")
        return ordenados
    except Exception as exc:
        print(f"[REFINAMENTO] Erro ao rerank: {exc}")
        return artigos[:top_n]
