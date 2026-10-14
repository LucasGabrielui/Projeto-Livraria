import json
import os
import secrets
from datetime import datetime, timedelta

ARQUIVO = "cookies.json"


def ler_cookies():
    if not os.path.exists(ARQUIVO):
        return {"sessao": None, "ultimo_usuario": "", "pesquisas": []}
    try:
        with open(ARQUIVO, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"sessao": None, "ultimo_usuario": "", "pesquisas": []}
    dados.setdefault("sessao", None)
    dados.setdefault("ultimo_usuario", "")
    dados.setdefault("pesquisas", [])
    return dados


def salvar_cookies(dados):
    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)


def criar_sessao(func, usuario):
    dados = ler_cookies()
    dados["sessao"] = {
        "token": secrets.token_hex(16),
        "id": func["id"],
        "nome": func["nome"],
        "cargo": func["cargo"],
        "expira": (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    }
    dados["ultimo_usuario"] = usuario
    salvar_cookies(dados)


def pegar_sessao():
    dados = ler_cookies()
    sessao = dados["sessao"]
    if sessao is None:
        return None
    try:
        expira = datetime.strptime(sessao["expira"], "%Y-%m-%d %H:%M:%S")
    except (KeyError, ValueError):
        return None
    if datetime.now() > expira:
        dados["sessao"] = None
        salvar_cookies(dados)
        return None
    return sessao


# toda vez que usa o sistema joga a expiracao pra mais 2h
def renovar_sessao():
    dados = ler_cookies()
    if dados["sessao"] is not None:
        dados["sessao"]["expira"] = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
        salvar_cookies(dados)


def apagar_sessao():
    dados = ler_cookies()
    dados["sessao"] = None
    salvar_cookies(dados)


def ultimo_usuario():
    return ler_cookies()["ultimo_usuario"]


def guardar_pesquisa(texto):
    dados = ler_cookies()
    pesquisas = dados["pesquisas"]
    if texto in pesquisas:
        pesquisas.remove(texto)
    pesquisas.insert(0, texto)
    dados["pesquisas"] = pesquisas[:5]
    salvar_cookies(dados)


def ultimas_pesquisas():
    return ler_cookies()["pesquisas"]
