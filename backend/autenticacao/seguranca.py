"""Checagens e sanitização de chaves de API.

Centraliza o padrão das chaves aceitas, a máscara exibida ao cliente e a
remoção de chaves de mensagens de erro/logs, para que a chave nunca seja
exposta em texto puro fora do servidor.

Também centraliza o que envolve o cadastro público protegido: regras de nome
de usuário, chave do registro (liga/desliga via env) e bloqueio por IP após
tentativas falhas de login.
"""

import os
import re

from django.core.cache import cache

_PADRAO_CHAVE_API = re.compile(r"^[A-Za-z0-9_\-.]{20,256}$")
_PADRAO_CHAVE_GOOGLE = re.compile(r"(?:AIza|AQ\.)[0-9A-Za-z_\-.]{15,}")

_PADRAO_USERNAME = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")

# Nomes reservados: não podem ser usados como nome de usuário.
_USERNAME_BLOQUEADOS = frozenset(
    {
        "admin",
        "administrador",
        "root",
        "sistema",
        "suporte",
        "contato",
        "info",
        "teste",
        "test",
        "guest",
        "convidado",
        "moderador",
        "moderator",
        "operator",
        "server",
        "servidor",
        "webmaster",
        "postmaster",
        "usuario",
        "user",
        "api",
        "opencode",
        "null",
        "undefined",
        "smtp",
        "ftp",
        "docker",
    }
)


def validar_chave_api(chave: str) -> bool:
    """Valida a forma geral de uma chave de API antes de aceitá-la/salvá-la."""
    return bool(_PADRAO_CHAVE_API.match((chave or "").strip()))


def endereco_ip(request) -> str:
    """Endereço do cliente considerando o proxy (nginx/X-Forwarded-For)."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or "desconhecido"


def registro_publico() -> bool:
    """Liga/desliga o cadastro público (env REGISTRO_PUBLICO, padrão 1)."""
    return os.getenv("REGISTRO_PUBLICO", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def validar_username(nome: str) -> tuple[bool, str]:
    """Valida o nome de usuário: formato, tamanho e blocklist."""
    nome = (nome or "").strip()
    if not nome:
        return False, "Informe um nome de usuário."
    if not _PADRAO_USERNAME.match(nome):
        return (
            False,
            "Use 3 a 30 caracteres: letras, números, ponto, hífen ou sublinhado.",
        )
    if nome.lower() in _USERNAME_BLOQUEADOS or nome.lstrip("_").isdigit():
        return False, "Esse nome de usuário não está disponível."
    return True, ""


# --- Bloqueio por IP após tentativas falhas de login ---
_CHAVE_FALHAS = "smartpapers:auth:falhas:{ip}"
_CHAVE_BLOQUEIO = "smartpapers:auth:bloqueio:{ip}"


def _limites() -> tuple[int, int, int]:
    limite = int(os.getenv("AUTH_FALHAS_LIMITE", "5"))
    janela = int(os.getenv("AUTH_JANELA_SEGUNDOS", "900"))
    bloqueio = int(os.getenv("AUTH_BLOQUEIO_SEGUNDOS", "900"))
    return limite, janela, bloqueio


def ip_bloqueado(request) -> bool:
    """True se o IP do cliente está temporariamente bloqueado."""
    try:
        return bool(cache.get(_CHAVE_BLOQUEIO.format(ip=endereco_ip(request))))
    except Exception:
        return False


def registrar_falha(request) -> None:
    """Conta a falha e bloqueia o IP ao atingir o limite."""
    ip = endereco_ip(request)
    limite, janela, bloqueio = _limites()
    chave_falhas = _CHAVE_FALHAS.format(ip=ip)
    try:
        contagem = int(cache.get(chave_falhas) or 0) + 1
        if contagem >= limite:
            cache.delete(chave_falhas)
            cache.set(_CHAVE_BLOQUEIO.format(ip=ip), True, bloqueio)
        else:
            cache.set(chave_falhas, contagem, janela)
    except Exception:
        # Nunca deixa uma falha de cache derrubar o login.
        pass


def limpar_falhas(request) -> None:
    """Zera o contador de falhas após um login com sucesso."""
    ip = endereco_ip(request)
    try:
        cache.delete(_CHAVE_FALHAS.format(ip=ip))
        cache.delete(_CHAVE_BLOQUEIO.format(ip=ip))
    except Exception:
        pass


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