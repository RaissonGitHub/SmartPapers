import threading

import torch
from adapters import AutoAdapterModel, Stack
from transformers import AutoTokenizer

_modelo = None
_tokenizer = None
_carregar_lock = threading.Lock()


def _carregar():
    global _modelo, _tokenizer
    if _modelo is not None:
        return

    with _carregar_lock:
        if _modelo is not None:
            return

        dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[specter2] Carregando modelo base + adapter em '{dispositivo}'...")
        _tokenizer = AutoTokenizer.from_pretrained("allenai/specter2_base")
        _modelo = AutoAdapterModel.from_pretrained(
            "allenai/specter2_base",
            low_cpu_mem_usage=False,
        )
        _modelo.load_adapter(
            "allenai/specter2",
            source="hf",
            load_as="proximity",
            set_active=True,
        )
        _modelo.set_active_adapters(Stack("proximity"))
        _modelo.eval()
        _modelo.to(dispositivo)
        print("[specter2] Modelo pronto.")


def _texto_embedding(titulo: str, resumo: str | None = None) -> str:
    _carregar()
    return titulo + _tokenizer.sep_token + (resumo or "")


def gerar_embedding_lote(textos: list[str]) -> list[list[float]]:
    """
    Gera embeddings (método oficial do SPECTER2: adapter `proximity`,
    embedding CLS, com [SEP], sem token_type_ids) para uma lista de textos.

    Usada tanto pela query (indexação em runtime) quanto pela reindexação
    offline, garantindo que base e consulta fiquem no MESMO espaço vetorial.
    """
    if not textos:
        return []
    _carregar()
    inputs = _tokenizer(
        textos,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt",
        return_token_type_ids=False,
    )
    with torch.no_grad():
        outputs = _modelo(**inputs)
    embeddings = outputs.last_hidden_state[:, 0, :]
    return embeddings.cpu().numpy().tolist()


def gerar_embedding(titulo: str, resumo: str | None = None) -> list[float]:

    _carregar()

    texto = _texto_embedding(titulo, resumo)

    inputs = _tokenizer(
        texto,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt",
        return_token_type_ids=False,
    )

    with torch.no_grad():
        outputs = _modelo(**inputs)

    embedding = outputs.last_hidden_state[:, 0, :]

    return embedding.squeeze(0).cpu().numpy().tolist()
