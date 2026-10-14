import json
import urllib.request
import urllib.parse

URL = "https://openlibrary.org/search.json"


def pesquisar_livros(titulo):
    params = urllib.parse.urlencode({"title": titulo, "limit": 10, "fields": "title,author_name,first_publish_year,ebook_access"})
    try:
        req = urllib.request.Request(URL + "?" + params, headers={"User-Agent": "TrabalhoLivraria/1.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        dados = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    resultados = []
    for doc in dados.get("docs", []):
        autores = doc.get("author_name", ["Desconhecido"])
        resultados.append({
            "titulo": doc.get("title", "Sem título"),
            "autor": autores[0],
            "ano": doc.get("first_publish_year"),
            "publico": doc.get("ebook_access") == "public"
        })
    return resultados
