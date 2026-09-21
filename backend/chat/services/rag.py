import json
import os
import re
from concurrent.futures import ThreadPoolExecutor

from artigos.services.buscar_artigos_service import buscar_artigos
from artigos.services.gerar_embedding_service import gerar_embedding

from .providers import LLMProvider, usar_provedor
from .refinamento import (
    classificar_necessidade_busca,
    reformular_busca,
    rerank_por_aderencia,
)

PDF_SECOES_BUSCA_MAX = int(os.getenv("PDF_SECOES_BUSCA_MAX", "4"))
ANO_MINIMO_ARTIGOS = 2020
ANO_MAXIMO_ARTIGOS = 2026

SYSTEM_PROMPT = (
    "Você é um assistente acadêmico e científico.\n"
    "Regras:\n"
    "1. Perguntas conceituais ou de conhecimento geral — como 'por que o céu é "
    "azul?', 'o que é machine learning?', 'como funciona a fotossíntese?' — devem "
    "ser respondidas DIRETAMENTE, SEM chamar a ferramenta de busca.\n"
    "2. Use a ferramenta 'pesquisar_base_artigos' APENAS quando o usuário pedir "
    "explicitamente para buscar, encontrar, listar ou recomendar artigos, papers "
    "ou referências científicas.\n"
    "3. Ao chamar a ferramenta, crie o parâmetro 'search_title_en' obrigatoriamente "
    "em INGLÊS com o título acadêmico equivalente à dúvida do usuário.\n"
    f"4. A base contém artigos somente entre {ANO_MINIMO_ARTIGOS} e "
    f"{ANO_MAXIMO_ARTIGOS}. Não invente outros anos; quando não houver período "
    "pedido pelo usuário, não envie filtros de ano.\n"
    "5. Responda usando apenas os artigos retornados pela ferramenta. Se nenhum "
    "artigo for diretamente relacionado à pergunta, diga isso honestamente em vez "
    "de citar artigos irrelevantes, e responda a pergunta com o seu conhecimento."
)


def _extrair_json_resposta(resposta: str) -> dict | None:
    """Extrai o primeiro objeto JSON válido, ignorando fences/bloco de texto."""
    texto = (resposta or "").replace("```json", "").replace("```", "")
    for trecho in re.findall(r"\{.*?\}", texto, re.DOTALL):
        try:
            return json.loads(trecho)
        except (json.JSONDecodeError, ValueError):
            continue
    return None


def selecionar_pdf(
    pdfs: list[dict], mensagem: str, provedor: LLMProvider | None = None
) -> tuple[int | None, list[dict]]:
    """Pede ao LLM para escolher um PDF e devolve apenas suas seções."""
    if not pdfs:
        return None, []
    if len(pdfs) == 1:
        pdf = pdfs[0]
        return pdf.get("id"), pdf.get("secoes") or []

    indice = "\n".join(
        f"id={pdf.get('id')} | nome={pdf.get('nome', '')} | "
        f"descricao={pdf.get('descricao', '')}"
        for pdf in pdfs
    )
    prompt = (
        "Escolha qual documento PDF, se houver, deve responder à pergunta. "
        'Responda somente JSON válido no formato {"pdf_id": número ou null}.\n\n'
        f"Documentos disponíveis:\n{indice}\n\nPergunta: {mensagem}"
    )
    resposta = (usar_provedor(provedor)).chat_simple(
        messages=[
            {
                "role": "system",
                "content": "Você seleciona documentos por relevância sem inventar informações.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    escolha = _extrair_json_resposta(resposta)
    pdf_id = escolha.get("pdf_id") if isinstance(escolha, dict) else None

    if isinstance(pdf_id, int) and pdf_id not in [item.get("id") for item in pdfs]:
        pdf = None
    else:
        pdf = next((item for item in pdfs if item.get("id") == pdf_id), None)

    if pdf is None and not isinstance(escolha, dict):
        pdf = pdfs[0]
        pdf_id = pdf.get("id")
    return (pdf_id, pdf.get("secoes") or []) if pdf else (None, [])


def _contexto_artigos_prompt(artigos) -> str:
    """Numera os artigos salvos na sessão para referência direta pelo modelo."""
    if not artigos:
        return ""
    blocos = []
    for indice, artigo in enumerate(artigos, start=1):
        autores = ", ".join(artigo.get("autores") or []) or "Não informados"
        ano = artigo.get("ano_publicacao") or "S/D"
        resumo = (artigo.get("resumo") or "").strip()[:400]
        titulo = artigo.get("titulo") or "Sem título"
        blocos.append(f"[{indice}] {titulo} ({ano}) - {autores}\nResumo: {resumo}")
    return "\n\n".join(blocos)


def _mensagens_artigos_contexto(artigos_contexto) -> list[dict]:
    """Constrói mensagem de sistema com os artigos salvos na sessão."""
    if not artigos_contexto:
        return []
    return [
        {
            "role": "system",
            "content": (
                "Estes são os artigos já encontrados nesta conversa, do mais antigo "
                "ao mais recente. Quando o usuário se referir a 'os artigos', "
                "'os últimos artigos', 'o artigo N' ou pedir detalhes sobre eles, "
                "responda USANDO APENAS as informações desta lista, sem inventar "
                "conteúdo inexistente:\n\n"
                f"{_contexto_artigos_prompt(artigos_contexto)}"
            ),
        }
    ]


def _secoes_pdf_prompt(pdf_secoes) -> str:
    """Formata as seções de conteúdo do PDF para o contexto do modelo.

    Referências bibliográficas participam apenas da recuperação, não da geração,
    para evitar que o modelo trate artigos citados no PDF como recomendados.
    """
    if not pdf_secoes:
        return ""
    blocos = []
    for indice, secao in enumerate(pdf_secoes, start=1):
        if secao.get("tipo", "conteudo") != "conteudo":
            continue
        resumo = (secao.get("resumo") or "").strip()
        texto = (secao.get("texto") or "").strip()
        blocos.append(f"[Seção {indice}] {resumo}\n{texto}")
    return "\n\n".join(blocos)


def _mensagens_pdf_contexto(pdf_secoes) -> list[dict]:
    """Constrói mensagem de sistema com o conteúdo relevante do PDF anexado."""
    prompt = _secoes_pdf_prompt(pdf_secoes)
    if not prompt:
        return []
    return [
        {
            "role": "system",
            "content": (
                "O usuário anexou um documento PDF a esta conversa. Estas são as "
                f"seções relevantes extraídas desse documento:\n\n{prompt}"
            ),
        }
    ]


def _mensagem_pdf_catalogo(pdf_catalogo) -> list[dict]:
    if not pdf_catalogo:
        return []
    indice = "\n".join(
        f"[{pdf.get('id')}] {pdf.get('nome', '')}: {pdf.get('descricao', '')}"
        for pdf in pdf_catalogo
    )
    return [
        {
            "role": "system",
            "content": (
                "Documentos PDF disponíveis nesta sessão. Use este índice para "
                "entender referências a documentos anteriores; o conteúdo detalhado "
                "do documento relevante será fornecido separadamente:\n\n" + indice
            ),
        }
    ]


def _requer_busca(mensagem: str, provedor: LLMProvider | None = None) -> bool:
    """Pergunta ao LLM se a mensagem exige busca de artigos."""
    p = usar_provedor(provedor)
    print(f"[RAG] Verificando se a mensagem precisa de busca: {mensagem[:120]}...")
    decisao = classificar_necessidade_busca(mensagem, provedor=p)
    print(f"[RAG] Decisão de busca: {decisao}")
    return True if decisao is None else decisao


def _mesclar_artigos_por_id(*listas: list[dict]) -> list[dict]:
    """Mantém um único artigo por id, preservando a primeira ocorrência."""
    unicos = {}
    for lista in listas:
        for artigo in lista:
            art_id = artigo.get("id")
            if art_id and art_id not in unicos:
                unicos[art_id] = artigo
    return list(unicos.values())


def _buscar_dupla_artigos(
    search_title_en: str,
    texto_original_usuario: str,
    top_n: int = 5,
    ano_inicio: int = 0,
    ano_fim: int = 0,
    area: str = "",
    provedor: LLMProvider | None = None,
    consultas_pdf: list[str] | None = None,
    retornar_medicao: bool = False,
) -> list[dict] | tuple[list[dict], dict]:
    """Busca nas consultas geradas + seções do PDF e reranke os resultados.

    Com `retornar_medicao=True`, devolve `(artigos_final, medicao)` onde
    `medicao` guarda consultas usadas, candidate set (ids + similaridade
    antes do rerank) e o Top-K final (id + similaridade vetorial original).
    """
    candidatos_por_lote = max(top_n * 3, 30)
    pool_rerank = max(top_n + 5, 15)
    p = usar_provedor(provedor)
    print(f"[RAG] Busca inicial: {search_title_en}")
    texto_reformulado = reformular_busca(texto_original_usuario, provedor=p)
    print(f"[RAG] Texto reformulado para busca: {texto_reformulado}")

    consultas_pdf = [c for c in (consultas_pdf or []) if c and c.strip()][
        :PDF_SECOES_BUSCA_MAX
    ]
    if consultas_pdf:
        print(f"[RAG] Usando {len(consultas_pdf)} seções do PDF como consultas.")

    def executar_busca(texto: str):
        try:
            print(f"[RAG] Executando busca vetorial para: {texto}")
            return buscar_artigos(
                embedding=gerar_embedding(titulo=texto),
                top_n=candidatos_por_lote,
                ano_inicio=ano_inicio,
                ano_fim=ano_fim,
                area=area,
            )
        except Exception as exc:
            print(f"[RAG] Falha na busca para '{texto[:80]}': {exc}")
            return []

    consultas = [search_title_en, texto_reformulado, texto_original_usuario]
    consultas += consultas_pdf
    with ThreadPoolExecutor(max_workers=min(4, len(consultas))) as executor:
        resultados = list(executor.map(executar_busca, consultas))

    print(f"[RAG] Resultados brutos: {len(resultados)} execuções de busca")
    pool = _mesclar_artigos_por_id(*resultados)[:pool_rerank]
    print(
        "[RAG] Medição Candidate Set:",
        ",".join(f"{a.get('id')}({a.get('similaridade')})" for a in pool),
    )
    print(f"[RAG] Pool para rerank: {len(pool)} artigos")
    artigos_final = rerank_por_aderencia(
        texto_original_usuario, pool, top_n, provedor=p
    )
    print(
        "[RAG] Medição Top-K Final:",
        ",".join(f"{a.get('id')}({a.get('similaridade')})" for a in artigos_final),
    )
    print(f"[RAG] Artigos finais retornados: {len(artigos_final)}")

    if retornar_medicao:

        def resumo_artigo(a):
            return {
                "id": a.get("id"),
                "titulo": (a.get("titulo") or "")[:120],
                "similaridade": a.get("similaridade"),
            }

        medicao = {
            "consultas": consultas,
            "candidate_set": [resumo_artigo(a) for a in pool],
            "top_k_final": [resumo_artigo(a) for a in artigos_final],
        }
        return artigos_final, medicao

    return artigos_final


def _extrair_tool_call_manual(conteudo_texto: str) -> dict | None:
    """Extrai argumentos de um tool_call em texto puro."""
    padrao = r"<tool_call>\s*({.*?})\s*</tool_call>"
    match = re.search(padrao, conteudo_texto, re.DOTALL)
    if not match:
        return None

    try:
        dados = json.loads(match.group(1))
        return dados.get("arguments", {})
    except json.JSONDecodeError:
        return None


def _extrair_chamada_ferramenta(resposta) -> tuple[str | None, dict | None]:
    """Lê a ferramenta solicitada pelo modelo, seja da SDK ou no fallback manual."""
    mensagem = getattr(resposta, "message", None)
    tool_calls = getattr(mensagem, "tool_calls", None) or []
    if tool_calls:
        call = tool_calls[0]
        return call.function.name, call.function.arguments

    conteudo = getattr(mensagem, "content", "") or ""
    if "<tool_call>" in conteudo:
        args = _extrair_tool_call_manual(conteudo)
        if args:
            return "pesquisar_base_artigos", args

    return None, None


def _normalizar_anos_tool_call(args: dict) -> None:
    """Mantém anos sugeridos pelo modelo dentro da janela disponível na base."""
    inicio = args.get("ano_inicio") or 0
    fim = args.get("ano_fim") or 0
    inicio_invalido = inicio and not ANO_MINIMO_ARTIGOS <= inicio <= ANO_MAXIMO_ARTIGOS
    fim_invalido = fim and not ANO_MINIMO_ARTIGOS <= fim <= ANO_MAXIMO_ARTIGOS

    if inicio_invalido:
        args["ano_inicio"] = ANO_MINIMO_ARTIGOS
    if fim_invalido:
        args["ano_fim"] = ANO_MAXIMO_ARTIGOS
    if inicio_invalido and fim_invalido:
        print(
            f"[RAG] Intervalo de anos do modelo fora da base; usando "
            f"{ANO_MINIMO_ARTIGOS}-{ANO_MAXIMO_ARTIGOS}."
        )


def _substituir_ancoras_por_titulo(resposta: str, artigos: list[dict]) -> str:
    """Troca o texto visível de links cujo destino é um artigo pelo seu título."""
    por_url = {
        artigo.get("link_original"): artigo.get("titulo", "artigo")
        for artigo in artigos
        if artigo.get("link_original")
    }
    if not por_url or not resposta:
        return resposta

    padrao = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")

    def substituto(match: re.Match[str]) -> str:
        url = match.group(2).strip()
        titulo = por_url.get(url)
        if not titulo:
            return match.group(0)
        anchor = re.sub(r"[\[\]]", "", titulo).strip() or "artigo"
        return f"[{anchor}]({url})"

    return padrao.sub(substituto, resposta)


def _resposta_direta(
    mensagem: str,
    provedor: LLMProvider | None = None,
    historico: list[dict] | None = None,
    artigos_contexto: list[dict] | None = None,
    pdf_catalogo: list[dict] | None = None,
    pdf_secoes: list[dict] | None = None,
) -> dict:
    """Resposta conceitual geral: sem busca no banco."""
    p = usar_provedor(provedor)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(_mensagem_pdf_catalogo(pdf_catalogo))
    messages.extend(_mensagens_pdf_contexto(pdf_secoes))
    messages.extend(_mensagens_artigos_contexto(artigos_contexto))
    if historico:
        messages.extend(historico)
    messages.append({"role": "user", "content": mensagem})
    resposta = p.chat_simple(messages=messages)
    return {"resposta": resposta, "ferramenta_utilizada": False, "artigos": []}


def processar_mensagem_usuario(
    mensagem: str,
    requisicao: str | None = None,
    provedor: LLMProvider | None = None,
    historico: list[dict] | None = None,
    artigos_contexto: list[dict] | None = None,
    pdf_catalogo: list[dict] | None = None,
    pdf_secoes: list[dict] | None = None,
    ano_inicio: int = 0,
    ano_fim: int = 0,
    area: str = "",
) -> dict:
    p = usar_provedor(provedor)
    pdf_secoes = pdf_secoes or []
    print(f"[RAG] Iniciando processamento da mensagem: {mensagem[:120]}...")

    def pesquisar_base_artigos(
        search_title_en: str,
        top_n: int = 5,
        ano_inicio: int = 0,
        ano_fim: int = 0,
        area: str = "",
    ) -> list[dict]:
        """Busca artigos da base disponível, publicada entre 2020 e 2026."""
        print(f"[RAG] Função ferramenta chamada com: {search_title_en} | top_n={top_n}")
        return _buscar_dupla_artigos(
            search_title_en=search_title_en,
            texto_original_usuario=mensagem,
            top_n=top_n,
            ano_inicio=ano_inicio,
            ano_fim=ano_fim,
            area=area,
            provedor=p,
            consultas_pdf=[s.get("texto") or s.get("resumo") or "" for s in pdf_secoes],
        )

    # Override explícito da intenção: sem o campo, o modelo decide.
    if requisicao == "busca":
        requer_busca = True
        print("[RAG] Requisição explícita de busca.")
    elif requisicao == "resposta":
        requer_busca = False
        print("[RAG] Requisição explícita de resposta direta.")
    else:
        requer_busca = _requer_busca(mensagem, provedor=p)

    if not requer_busca:
        print("[RAG] Mensagem resolvida sem busca no banco.")
        return _resposta_direta(
            mensagem,
            provedor=p,
            historico=historico,
            artigos_contexto=artigos_contexto,
            pdf_catalogo=pdf_catalogo,
            pdf_secoes=pdf_secoes,
        )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(_mensagem_pdf_catalogo(pdf_catalogo))
    messages.extend(_mensagens_pdf_contexto(pdf_secoes))
    messages.extend(_mensagens_artigos_contexto(artigos_contexto))
    if historico:
        messages.extend(historico)
    messages.append({"role": "user", "content": mensagem})

    print("[RAG] Enviando mensagem ao modelo para decidir tool-call...")
    resposta = p.chat(messages=messages, tools=[pesquisar_base_artigos])
    func_name, args = _extrair_chamada_ferramenta(resposta)
    print(f"[RAG] Tool call detectada: func_name={func_name}, args={args}")

    if func_name == "pesquisar_base_artigos" and args:
        # Filtros escolhidos na barra lateral têm precedência sobre o que o
        # modelo sugerir no tool call; somente avançam se estiverem definidos.
        args["ano_inicio"] = ano_inicio if ano_inicio else args.get("ano_inicio") or 0
        args["ano_fim"] = ano_fim if ano_fim else args.get("ano_fim") or 0
        args["area"] = area.strip() if area.strip() else args.get("area") or ""
        _normalizar_anos_tool_call(args)

        query_ingles_gerada = args.get("search_title_en", "")
        print(f"[RAG] Query em inglês recebida: {query_ingles_gerada}")
        artigos_encontrados = pesquisar_base_artigos(**args)

        messages.extend(
            [
                {
                    "role": "assistant",
                    "content": f"Chamei a ferramenta pesquisar_base_artigos com: {json.dumps(args)}",
                },
                {
                    "role": "tool",
                    "tool_name": func_name,
                    "content": json.dumps(artigos_encontrados, ensure_ascii=False),
                },
            ]
        )

        print("[RAG] Gerando resposta final com os artigos retornados...")
        resposta_final = p.chat_simple(messages=messages)
        resposta_final = _substituir_ancoras_por_titulo(
            resposta_final, artigos_encontrados
        )
        print("[RAG] Resposta final concluída.")
        return {
            "resposta": resposta_final,
            "ferramenta_utilizada": True,
            "titulo_ingles_gerado": query_ingles_gerada,
            "texto_cru_utilizado": mensagem,
            "total_artigos_mesclados": len(artigos_encontrados),
            "artigos": artigos_encontrados,
        }

    print("[RAG] Nenhuma ferramenta foi chamada; devolvendo resposta direta do modelo.")
    return {
        "resposta": getattr(getattr(resposta, "message", None), "content", ""),
        "ferramenta_utilizada": False,
        "artigos": [],
    }
