"""Checagens e sanitização de chaves de API.

Centraliza o padrão das chaves aceitas, a máscara exibida ao cliente e a
remoção de chaves de mensagens de erro/logs, para que a chave nunca seja
exposta em texto puro fora do servidor.
"""

import re

_PADRAO_CHAVE_API = re.compile(r"^[A-Za-z0-9_\-]{20,256}$")
_PADRAO_CHAVE_GOOGLE = re.compile(r"AIza[0-9A-Za-z_\-]+")


def validar_chave_api(chave: str) -> bool:
    """Valida a forma geral de uma chave de API antes de aceitá-la/salvá-la."""
    return bool(_PADRAO_CHAVE_API.match((chave or "").strip()))


def mascarar_chave(chave: str) -> str:
    """Mascara a chave mantendo apenas prefixo e sufixo pequenos.

    Vazio retorna vazio; chaves curtas viram apenas pontos.
    """
    if not chave:
        return ""
    chave = chave.strip()
    if len(chave) <= 8:
        return "••••••••"
    return f"{chave[:4]}••••••••{chave[-4:]}"


def remover_chave_do_texto(texto: str, api_key: str | None = None) -> str:
    """Troca por '***' a chave exata e qualquer chave no padrão Google."""
    if not texto:
        return texto
    if api_key:
        texto = texto.replace(api_key, "***")
    return _PADRAO_CHAVE_GOOGLE.sub("***", texto)