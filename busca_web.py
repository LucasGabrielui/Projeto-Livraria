import json
import math
import urllib.request
import urllib.parse

URL = "https://openlibrary.org/search.json"

# sede da livraria no centro de sao paulo
SEDE_LAT = -23.5503
SEDE_LON = -46.6340


def pegar_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "TrabalhoLivraria/1.0"})
    resp = urllib.request.urlopen(req, timeout=10)
    return json.loads(resp.read().decode("utf-8"))


def pesquisar_livros(titulo):
    params = urllib.parse.urlencode({"title": titulo, "limit": 10, "fields": "title,author_name,first_publish_year,ebook_access,cover_i"})
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
            "publico": doc.get("ebook_access") == "public",
            "capa": doc.get("cover_i")
        })
    return resultados


def buscar_cep(cep):
    try:
        dados = pegar_json(f"https://viacep.com.br/ws/{cep}/json/")
    except Exception:
        return None
    if dados.get("erro"):
        return {}
    return dados


def achar_coordenadas(endereco):
    tentativas = [
        {"street": endereco.get("logradouro", ""), "city": endereco["localidade"], "state": endereco["uf"]},
        {"city": endereco["localidade"], "state": endereco["uf"]},
    ]
    for t in tentativas:
        t["country"] = "Brasil"
        t["format"] = "json"
        t["limit"] = 1
        try:
            dados = pegar_json("https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(t))
        except Exception:
            return None
        if dados:
            return float(dados[0]["lat"]), float(dados[0]["lon"])
    return None


def distancia_km(lat1, lon1, lat2, lon2):
    r = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


# devolve None sem internet, {} se o cep nao existe
def distancia_ate_sede(cep):
    endereco = buscar_cep(cep)
    if not endereco:
        return endereco
    coords = achar_coordenadas(endereco)
    if coords is None:
        return None
    # linha reta * 1.3 pra chegar perto da distancia pelas ruas
    km = distancia_km(SEDE_LAT, SEDE_LON, coords[0], coords[1]) * 1.3
    partes = [endereco.get("logradouro"), endereco.get("bairro"), endereco["localidade"] + " - " + endereco["uf"]]
    return {"km": round(km, 1), "endereco": ", ".join(p for p in partes if p), "cidade": endereco["localidade"]}
