"""Extração, seccionamento e relevância de PDFs anexados às conversas."""

import os
import re

import fitz
import numpy as np

from artigos.services.gerar_embedding_service import gerar_embedding_lote

from .providers import LLMProvider, provedor_padrao
from .refinamento import _limpar_pensamento

TAM_MAX_SECAO = int(os.getenv("PDF_TAM_SECAO", "2000"))
MAX_SECOES = int(os.getenv("PDF_MAX_SECOES", "40"))
TAMANHO_LOTE = int(os.getenv("PDF_LOTE_SECOES", "12"))
SECOES_TOP_K = int(os.getenv("PDF_SECOES_MAX", "6"))
SECOES_SIM_MIN = float(os.getenv("PDF_SECOES_SIM_MIN", "0.3"))

PROMPT_SECOES = (
    "Você organiza o conteúdo de um documento científico em seções.\n"
    "Para cada seção numerada abaixo, escreva UMA linha no formato exato:\n"
    "SECAO <n>|<conteudo|referencia>|<resumo de até 40 palavras>\n"
    "- use 'conteudo' se a seção traz ideias, métodos ou resultados do documento;\n"
    "- use 'referencia' se for bibliografia, agradecimentos, epígrafe, cabeçalho, "
    "rodapé ou texto de preenchimento;\n"
    "- o resumo será usado como consulta de busca acadêmica; quando a seção tiver "
    "conteúdo técnico, escreva-o em INGLÊS.\n"
    "Escreva uma linha por seção, na ordem, sem explicações."
)

_RE_SECAO = re.compile(
    r"SECAO\s+(\d+)\s*\|\s*(conteudo|referencia)\s*\|\s*(.+)",
    re.IGNORECASE,
)

# Texto editorial/rodapé que não deve virar consulta de busca nem contexto.
_PADROES_LIXO = [
    re.compile(r"copyright", re.IGNORECASE),
    re.compile(r"licensed use limited", re.IGNORECASE),
    re.compile(r"authorized licensed use", re.IGNORECASE),
    re.compile(r"downloaded on", re.IGNORECASE),
    re.compile(r"restrictions apply", re.IGNORECASE),
    re.compile(r"senior member of the (ieee|institute)", re.IGNORECASE),
    re.compile(r"\d{4} ieee", re.IGNORECASE),
    re.compile(r"©\s*\d{4}"),
    re.compile(
        r"received\s+(january|february|march|april|may|june|july|august|"
        r"september|october|november|december)\s+\d{1,2},\s+\d{4}",
        re.IGNORECASE,
    ),
]


def _juntar_hifenizacao(texto: str) -> str:
    """Une palavras quebradas por hífen no fim da linha extraída do PDF."""
    return re.sub(r"(\w)[\u002d\u2010\u2011]\r?\n(\w)", r"\1\2", texto or "")


def _cortar_por_frases(texto: str, limite: int) -> list[str]:
    """Corta um texto longo em limites de palavra, sem quebrar no meio."""
    partes = []
    restante = texto.strip()
    while len(restante) > limite:
        corte = restante.rfind(" ", 0, limite)
        if corte < 1:
            corte = limite
        trecho = restante[:corte].strip()
        if trecho:
            partes.append(trecho)
        restante = restante[corte:].lstrip()
    if restante:
        partes.append(restante)
    return partes


def _eh_lixo(texto: str) -> bool:
    """True se o trecho parece rodapé editorial (copyright, licença etc.)."""
    return any(p.search(texto or "") for p in _PADROES_LIXO)


def _limpar_lixo(texto: str) -> str:
    """Remove apenas as linhas que parecem rodapé editorial do PDF."""
    mantidas = [l for l in (texto or "").splitlines() if not _eh_lixo(l)]
    return "\n".join(mantidas).strip()


def extrair_texto_pdf(arquivo) -> str:
    """Extrai o texto de um arquivo PDF (UploadedFile ou binário)."""
    dados = arquivo.read()
    if arquivo.seekable():
        arquivo.seek(0)
    if not dados:
        return ""
    with fitz.open(stream=dados, filetype="pdf") as doc:
        paginas = []
        for pagina in doc:
            try:
                texto = pagina.get_text("text") or ""
            except Exception:
                texto = ""
            if texto.strip():
                paginas.append(texto)
    return "\n\n".join(paginas)


def dividir_em_secoes(texto: str, tam_max: int | None = None) -> list[str]:
    """Divide o texto em blocos de até `tam_max`, cortando em limites de palavra."""
    limite = tam_max or TAM_MAX_SECAO
    texto_normalizado = _juntar_hifenizacao(texto)
    paragrafos = [
        p.strip() for p in re.split(r"\n\s*\n", texto_normalizado) if p.strip()
    ]
    secoes = []
    atual = []
    tamanho = 0

    for paragrafo in paragrafos:
        if len(paragrafo) > limite:
            if atual:
                secoes.append("\n".join(atual))
                atual = []
                tamanho = 0
            secoes.extend(_cortar_por_frases(paragrafo, limite))
            continue
        if tamanho + len(paragrafo) > limite and atual:
            secoes.append("\n".join(atual))
            atual = []
            tamanho = 0
        atual.append(paragrafo)
        tamanho += len(paragrafo) + 1

    if atual:
        secoes.append("\n".join(atual))

    return secoes[:MAX_SECOES]


def _parsear_resumo_secoes(resposta: str) -> dict[int, tuple[str, str]]:
    """Converte a resposta do LLM em {indice: (tipo, resumo)}."""
    resultado = {}
    for linha in (resposta or "").splitlines():
        compativel = _RE_SECAO.search(linha)
        if not compativel:
            continue
        indice = int(compativel.group(1))
        tipo = compativel.group(2).lower()
        resumo = compativel.group(3).strip()
        if resumo:
            resultado[indice] = (tipo, resumo)
    return resultado


def _resumir_lote(
    secoes: list[str],
    provedor: LLMProvider | None = None,
) -> dict[int, tuple[str, str]]:
    p = provedor or provedor_padrao
    blocos = "\n\n".join(
        f"SECAO {indice + 1}\n{texto}" for indice, texto in enumerate(secoes)
    )
    resposta = p.chat_simple(
        messages=[
            {"role": "system", "content": PROMPT_SECOES},
            {"role": "user", "content": blocos},
        ],
        temperature=0,
    )
    return _parsear_resumo_secoes(_limpar_pensamento(resposta or ""))


def secoes_processadas(
    texto: str,
    provedor: LLMProvider | None = None,
) -> list[dict]:
    """Extrai e resume as seções, mantendo apenas as de conteúdo real."""
    partes = dividir_em_secoes(texto)
    if not partes:
        return []

    secoes_final = []
    for inicio in range(0, len(partes), TAMANHO_LOTE):
        lote = partes[inicio : inicio + TAMANHO_LOTE]
        resumos = _resumir_lote(lote, provedor)
        for indice_rel, texto_secao in enumerate(lote):
            indice_global = inicio + indice_rel + 1
            tipo, resumo = resumos.get(indice_global, ("conteudo", ""))
            if tipo not in ("conteudo", "referencia"):
                continue
            texto_secao_limpo = _limpar_lixo(texto_secao)
            if not texto_secao_limpo:
                continue
            secoes_final.append(
                {
                    "indice": indice_global,
                    "tipo": tipo,
                    "resumo": resumo or texto_secao_limpo[:300],
                    "texto": texto_secao_limpo[:2000],
                }
            )

    return secoes_final


def secoes_relevantes(
    secoes: list[dict],
    consultas: list[str],
    limite: int | None = None,
    piso: float | None = None,
) -> list[dict]:
    """Retorna as seções mais similares (cosseno) ao conjunto de consultas."""
    limite = limite or SECOES_TOP_K
    piso = SECOES_SIM_MIN if piso is None else piso

    consultas_limpas = [c for c in consultas if c and c.strip()]
    if not secoes or not consultas_limpas:
        return []

    try:
        vetores_secoes = np.asarray(
            gerar_embedding_lote(
                [s.get("texto") or s.get("resumo") or "" for s in secoes]
            )
        )
        vetores_consultas = np.asarray(gerar_embedding_lote(consultas_limpas))
        if vetores_secoes.size == 0 or vetores_consultas.size == 0:
            return []
    except Exception as exc:
        print(f"[PDF] Falha ao embeddar seções/consultas: {exc}")
        return secoes[:limite]

    norm_secoes = vetores_secoes / np.linalg.norm(
        vetores_secoes, axis=1, keepdims=True
    )
    norm_consultas = vetores_consultas / np.linalg.norm(
        vetores_consultas, axis=1, keepdims=True
    )

    similaridade = norm_secoes @ norm_consultas.T
    melhor = similaridade.max(axis=1)
    ordem = np.argsort(-melhor)

    escolhidas = []
    for posicao in ordem:
        if melhor[posicao] < piso:
            break
        escolhidas.append(secoes[int(posicao)])
        if len(escolhidas) >= limite:
            break

    print(f"[PDF] {len(escolhidas)} seções relevantes de {len(secoes)}.")
    return escolhidas


def processar_pdf(
    arquivo,
    consultas: list[str],
    provedor: LLMProvider | None = None,
) -> list[dict]:
    """Extrai, secciona e filtra as seções relevantes de um PDF anexado."""
    texto = extrair_texto_pdf(arquivo)
    if not texto.strip():
        print("[PDF] Nenhum texto extraído do anexo.")
        return []

    secoes = secoes_processadas(texto, provedor)
    consultas_limpas = [c for c in consultas if c and c.strip()]
    relevantes = (
        secoes_relevantes(secoes, consultas_limpas)
        if consultas_limpas
        else []
    )
    if not relevantes and secoes:
        relevantes = secoes[:SECOES_TOP_K]

    print(f"[PDF] {len(relevantes)} seções relevantes mantidas.")
    return relevantes