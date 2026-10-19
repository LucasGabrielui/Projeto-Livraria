import sqlite3
import hashlib
import secrets
import math
from datetime import date, datetime, timedelta

ARQUIVO_BANCO = "livraria.db"
VALOR_SEMANA = 50.00
MAX_ALUGUEIS = 3
MAX_SEMANAS = 4

# velocidade media de cada veiculo em km/h
VEICULOS = {"bicicleta": 12, "moto": 35, "carro": 30, "van": 40, "caminhão": 55}
HORAS_SEPARACAO = 3

# codigo da capa de cada livro na open library
CAPAS = {
    "Dom Casmurro": 647501, "Memórias Póstumas de Brás Cubas": 123152, "Quincas Borba": 123420,
    "O Alienista": 647504, "Iracema": 2664651, "O Guarani": 5271115, "Senhora": 5050225,
    "O Cortiço": 8176059, "Triste Fim de Policarpo Quaresma": 5459319, "Os Sertões": 4921189,
    "Vidas Secas": 12369687, "Capitães da Areia": 4178919, "Grande Sertão: Veredas": 13909068,
    "A Hora da Estrela": 650866, "Orgulho e Preconceito": 14348537, "Frankenstein": 12356249,
    "1984": 9267242, "O Pequeno Príncipe": 10708272, "Dom Quixote": 14428305,
}

# versao digital gratuita no projeto gutenberg (so os que estao em dominio publico)
GUTENBERG = "https://www.gutenberg.org/ebooks/"
EBOOKS = {
    "Dom Casmurro": GUTENBERG + "55752", "Memórias Póstumas de Brás Cubas": GUTENBERG + "54829",
    "Quincas Borba": GUTENBERG + "55682", "O Alienista": GUTENBERG + "57001", "Iracema": GUTENBERG + "67740",
    "O Guarani": GUTENBERG + "67724", "O Cortiço": GUTENBERG + "69187",
    "Orgulho e Preconceito": GUTENBERG + "1342", "Frankenstein": GUTENBERG + "84", "Dom Quixote": GUTENBERG + "2000",
}


def conectar():
    con = sqlite3.connect(ARQUIVO_BANCO)
    con.row_factory = sqlite3.Row
    return con


def gerar_hash(senha, sal):
    return hashlib.pbkdf2_hmac("sha256", senha.encode(), sal.encode(), 100000).hex()


def criar_tabelas():
    con = conectar()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS livros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            autor TEXT NOT NULL,
            ano INTEGER,
            preco REAL,
            estoque INTEGER,
            capa INTEGER,
            fornecedor_id INTEGER REFERENCES fornecedores(id),
            ebook TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT UNIQUE NOT NULL,
            email TEXT,
            telefone TEXT,
            cidade TEXT,
            senha TEXT,
            sal TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS funcionarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT UNIQUE NOT NULL,
            cargo TEXT NOT NULL,
            usuario TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            sal TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS alugueis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL REFERENCES clientes(id),
            livro_id INTEGER NOT NULL REFERENCES livros(id),
            data_inicio TEXT NOT NULL,
            data_prevista TEXT NOT NULL,
            data_devolucao TEXT,
            semanas INTEGER NOT NULL,
            valor REAL NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'loja'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cnpj TEXT UNIQUE NOT NULL,
            telefone TEXT,
            cep TEXT,
            cidade TEXT,
            distancia_km REAL NOT NULL,
            veiculo TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS entregadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT UNIQUE NOT NULL,
            telefone TEXT,
            veiculo TEXT NOT NULL,
            placa TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL REFERENCES clientes(id),
            livro_id INTEGER NOT NULL REFERENCES livros(id),
            entregador_id INTEGER REFERENCES entregadores(id),
            fornecedor_id INTEGER REFERENCES fornecedores(id),
            data_pedido TEXT NOT NULL,
            cep TEXT NOT NULL,
            endereco TEXT NOT NULL,
            distancia_km REAL,
            horas_previstas REAL,
            valor REAL NOT NULL,
            status TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS parcerias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            nome TEXT NOT NULL,
            email TEXT NOT NULL,
            telefone TEXT,
            cidade TEXT,
            proposta TEXT NOT NULL,
            data TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)

    # o banco da primeira versao nao tinha senha pros clientes
    colunas = [c["name"] for c in cur.execute("PRAGMA table_info(clientes)").fetchall()]
    if "senha" not in colunas:
        cur.execute("ALTER TABLE clientes ADD COLUMN senha TEXT")
        cur.execute("ALTER TABLE clientes ADD COLUMN sal TEXT")

    # bancos antigos nao tinham capa nem fornecedor nos livros
    colunas = [c["name"] for c in cur.execute("PRAGMA table_info(livros)").fetchall()]
    if "capa" not in colunas:
        cur.execute("ALTER TABLE livros ADD COLUMN capa INTEGER")
        cur.execute("ALTER TABLE livros ADD COLUMN fornecedor_id INTEGER REFERENCES fornecedores(id)")
        for titulo, capa in CAPAS.items():
            cur.execute("UPDATE livros SET capa = ? WHERE titulo = ?", (capa, titulo))

    # e-book e tipo de aluguel entraram depois
    colunas = [c["name"] for c in cur.execute("PRAGMA table_info(livros)").fetchall()]
    if "ebook" not in colunas:
        cur.execute("ALTER TABLE livros ADD COLUMN ebook TEXT")
        for titulo, link in EBOOKS.items():
            cur.execute("UPDATE livros SET ebook = ? WHERE titulo = ?", (link, titulo))
    colunas = [c["name"] for c in cur.execute("PRAGMA table_info(alugueis)").fetchall()]
    if "tipo" not in colunas:
        cur.execute("ALTER TABLE alugueis ADD COLUMN tipo TEXT NOT NULL DEFAULT 'loja'")

    # fornecedores e entregadores de exemplo
    cur.execute("SELECT COUNT(*) FROM fornecedores")
    if cur.fetchone()[0] == 0:
        cur.executemany("INSERT INTO fornecedores (nome, cnpj, telefone, cep, cidade, distancia_km, veiculo) VALUES (?, ?, ?, ?, ?, ?, ?)", [
            ("Distribuidora Paulista de Livros", "11222333000144", "1140028922", "06454000", "Barueri", 32.0, "van"),
            ("Editora Guanabara Distribuição", "55666777000188", "2132107000", "20040002", "Rio de Janeiro", 470.0, "caminhão"),
        ])
    cur.execute("SELECT COUNT(*) FROM entregadores")
    if cur.fetchone()[0] == 0:
        cur.executemany("INSERT INTO entregadores (nome, cpf, telefone, veiculo, placa) VALUES (?, ?, ?, ?, ?)", [
            ("Rafael Souza", "22233344455", "11988887777", "moto", "FGH1A23"),
            ("Juliana Lima", "33344455566", "11977776666", "carro", "BRA2E19"),
        ])

    cur.execute("SELECT COUNT(*) FROM livros")
    if cur.fetchone()[0] == 0:
        livros = [
            # precos de edicoes comuns novas, pesquisados em lojas online em out/2026
            ("Dom Casmurro", "Machado de Assis", 1899, 24.90, 10),
            ("Memórias Póstumas de Brás Cubas", "Machado de Assis", 1881, 24.90, 8),
            ("Quincas Borba", "Machado de Assis", 1891, 27.90, 5),
            ("O Alienista", "Machado de Assis", 1882, 19.90, 12),
            ("Iracema", "José de Alencar", 1865, 24.90, 7),
            ("O Guarani", "José de Alencar", 1857, 26.90, 6),
            ("Senhora", "José de Alencar", 1875, 29.90, 9),
            ("O Cortiço", "Aluísio Azevedo", 1890, 27.90, 10),
            ("Triste Fim de Policarpo Quaresma", "Lima Barreto", 1915, 24.90, 4),
            ("Os Sertões", "Euclides da Cunha", 1902, 44.90, 3),
            ("Vidas Secas", "Graciliano Ramos", 1938, 24.90, 6),
            ("Capitães da Areia", "Jorge Amado", 1937, 52.90, 5),
            ("Grande Sertão: Veredas", "João Guimarães Rosa", 1956, 59.90, 3),
            ("A Hora da Estrela", "Clarice Lispector", 1977, 24.90, 6),
            ("Orgulho e Preconceito", "Jane Austen", 1813, 34.90, 8),
            ("Frankenstein", "Mary Shelley", 1818, 19.90, 6),
            ("1984", "George Orwell", 1949, 35.90, 7),
            ("O Pequeno Príncipe", "Antoine de Saint-Exupéry", 1943, 17.90, 9),
            ("Dom Quixote", "Miguel de Cervantes", 1605, 59.90, 2),
        ]
        # metade dos livros vem de cada distribuidora
        livros = [l + (CAPAS.get(l[0]), 1 + i % 2, EBOOKS.get(l[0])) for i, l in enumerate(livros)]
        cur.executemany("INSERT INTO livros (titulo, autor, ano, preco, estoque, capa, fornecedor_id, ebook) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", livros)

    # nao existe mais usuario padrao (admin/admin): o primeiro gerente
    # e criado pela tela de primeiro acesso em /admin/primeiro-acesso
    con.commit()
    con.close()


# livros

def listar_livros():
    con = conectar()
    livros = con.execute("SELECT * FROM livros ORDER BY titulo").fetchall()
    con.close()
    return livros


def procurar_livros(texto):
    con = conectar()
    livros = con.execute("SELECT * FROM livros WHERE titulo LIKE ? OR autor LIKE ? ORDER BY titulo",
                         ("%" + texto + "%", "%" + texto + "%")).fetchall()
    con.close()
    return livros


def buscar_livro_id(id_livro):
    con = conectar()
    livro = con.execute("SELECT * FROM livros WHERE id = ?", (id_livro,)).fetchone()
    con.close()
    return livro


def livro_existe(titulo, autor):
    con = conectar()
    achou = con.execute("SELECT id FROM livros WHERE lower(titulo) = lower(?) AND lower(autor) = lower(?)",
                        (titulo.strip(), autor.strip())).fetchone()
    con.close()
    return achou is not None


def adicionar_livro(titulo, autor, ano, preco, estoque, capa=None, fornecedor_id=None, ebook=None):
    if livro_existe(titulo, autor):
        return False
    con = conectar()
    con.execute("INSERT INTO livros (titulo, autor, ano, preco, estoque, capa, fornecedor_id, ebook) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (titulo.strip(), autor.strip(), ano, preco, estoque, capa, fornecedor_id, ebook))
    con.commit()
    con.close()
    return True


def editar_livro(id_livro, preco, estoque, fornecedor_id, ebook):
    con = conectar()
    cur = con.execute("UPDATE livros SET preco = ?, estoque = ?, fornecedor_id = ?, ebook = ? WHERE id = ?",
                      (preco, estoque, fornecedor_id, ebook, id_livro))
    con.commit()
    ok = cur.rowcount > 0
    con.close()
    return ok


def remover_livro(id_livro):
    con = conectar()
    alugado = con.execute("SELECT COUNT(*) FROM alugueis WHERE livro_id = ? AND data_devolucao IS NULL",
                          (id_livro,)).fetchone()[0]
    if alugado > 0:
        con.close()
        return False
    con.execute("DELETE FROM livros WHERE id = ?", (id_livro,))
    con.commit()
    con.close()
    return True


# clientes

def cliente_existe(cpf, email):
    con = conectar()
    achou = con.execute("SELECT id FROM clientes WHERE cpf = ? OR lower(email) = lower(?)", (cpf, email)).fetchone()
    con.close()
    return achou is not None


def cadastrar_cliente(nome, cpf, email, telefone, cidade, senha):
    if cliente_existe(cpf, email):
        return False
    sal = secrets.token_hex(16)
    con = conectar()
    con.execute("INSERT INTO clientes (nome, cpf, email, telefone, cidade, senha, sal) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (nome, cpf, email, telefone, cidade, gerar_hash(senha, sal), sal))
    con.commit()
    con.close()
    return True


def listar_clientes(texto=""):
    con = conectar()
    clientes = con.execute("""
        SELECT c.*,
               (SELECT COUNT(*) FROM alugueis a WHERE a.cliente_id = c.id AND a.data_devolucao IS NULL) AS ativos
        FROM clientes c
        WHERE c.nome LIKE ? OR c.cpf LIKE ? OR c.email LIKE ?
        ORDER BY c.nome
    """, ("%" + texto + "%", "%" + texto + "%", "%" + texto + "%")).fetchall()
    con.close()
    return clientes


def buscar_cliente_id(id_cliente):
    con = conectar()
    cliente = con.execute("SELECT * FROM clientes WHERE id = ?", (id_cliente,)).fetchone()
    con.close()
    return cliente


def login_cliente(email, senha):
    con = conectar()
    c = con.execute("SELECT id, nome, senha, sal FROM clientes WHERE lower(email) = lower(?)", (email,)).fetchone()
    con.close()
    if c is None or c["senha"] is None:
        return None
    if gerar_hash(senha, c["sal"]) != c["senha"]:
        return None
    return {"id": c["id"], "nome": c["nome"]}


# funcionarios

def cadastrar_funcionario(nome, cpf, cargo, usuario, senha):
    sal = secrets.token_hex(16)
    con = conectar()
    try:
        con.execute("INSERT INTO funcionarios (nome, cpf, cargo, usuario, senha, sal) VALUES (?, ?, ?, ?, ?, ?)",
                    (nome, cpf, cargo, usuario, gerar_hash(senha, sal), sal))
        con.commit()
        ok = True
    except sqlite3.IntegrityError:
        ok = False
    con.close()
    return ok


def existe_funcionario():
    con = conectar()
    total = con.execute("SELECT COUNT(*) FROM funcionarios").fetchone()[0]
    con.close()
    return total > 0


def listar_funcionarios():
    con = conectar()
    funcs = con.execute("SELECT id, nome, cpf, cargo, usuario FROM funcionarios ORDER BY nome").fetchall()
    con.close()
    return funcs


def login_funcionario(usuario, senha):
    con = conectar()
    f = con.execute("SELECT id, nome, cargo, senha, sal FROM funcionarios WHERE usuario = ?", (usuario,)).fetchone()
    con.close()
    if f is None:
        return None
    if gerar_hash(senha, f["sal"]) != f["senha"]:
        return None
    return {"id": f["id"], "nome": f["nome"], "cargo": f["cargo"]}


# alugueis

def calcular_multa(data_prevista, data_ref):
    atraso = (data_ref - date.fromisoformat(data_prevista)).days
    if atraso <= 0:
        return 0
    # cada semana de atraso (mesmo incompleta) cobra mais uma semana de aluguel
    return math.ceil(atraso / 7) * VALOR_SEMANA


# e-book vencido nao tem o que devolver, entao encerra sozinho no fim do prazo
def encerrar_ebooks_vencidos():
    con = conectar()
    con.execute("""UPDATE alugueis SET data_devolucao = data_prevista
                   WHERE tipo = 'online' AND data_devolucao IS NULL AND data_prevista < ?""",
                (date.today().isoformat(),))
    con.commit()
    con.close()


def alugar_livro(id_cliente, id_livro, semanas, tipo):
    if semanas < 1 or semanas > MAX_SEMANAS:
        return "Quantidade de semanas inválida."
    if tipo not in ["loja", "online"]:
        return "Escolha retirar na loja ou ler online."

    encerrar_ebooks_vencidos()
    con = conectar()
    livro = con.execute("SELECT estoque, ebook FROM livros WHERE id = ?", (id_livro,)).fetchone()
    if livro is None:
        con.close()
        return "Livro não encontrado."
    if tipo == "online" and not livro["ebook"]:
        con.close()
        return "Esse livro não tem versão digital, só retirada na loja."
    if tipo == "loja" and livro["estoque"] <= 0:
        con.close()
        return "Esse livro não está disponível na loja no momento."

    ativos = con.execute("SELECT COUNT(*) FROM alugueis WHERE cliente_id = ? AND data_devolucao IS NULL",
                         (id_cliente,)).fetchone()[0]
    if ativos >= MAX_ALUGUEIS:
        con.close()
        return f"Você já está com {MAX_ALUGUEIS} livros. Devolva algum antes de alugar outro."

    repetido = con.execute("SELECT id FROM alugueis WHERE cliente_id = ? AND livro_id = ? AND data_devolucao IS NULL",
                           (id_cliente, id_livro)).fetchone()
    if repetido is not None:
        con.close()
        return "Você já está com esse livro alugado."

    hoje = date.today()
    prevista = hoje + timedelta(weeks=semanas)
    con.execute("""INSERT INTO alugueis (cliente_id, livro_id, data_inicio, data_prevista, semanas, valor, tipo)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (id_cliente, id_livro, hoje.isoformat(), prevista.isoformat(), semanas, semanas * VALOR_SEMANA, tipo))
    if tipo == "loja":
        con.execute("UPDATE livros SET estoque = estoque - 1 WHERE id = ?", (id_livro,))
    con.commit()
    con.close()
    return None


def devolver_livro(id_aluguel):
    con = conectar()
    a = con.execute("SELECT * FROM alugueis WHERE id = ? AND data_devolucao IS NULL", (id_aluguel,)).fetchone()
    if a is None:
        con.close()
        return None
    hoje = date.today()
    multa = 0
    if a["tipo"] == "loja":
        multa = calcular_multa(a["data_prevista"], hoje)
        con.execute("UPDATE livros SET estoque = estoque + 1 WHERE id = ?", (a["livro_id"],))
    con.execute("UPDATE alugueis SET data_devolucao = ?, valor = valor + ? WHERE id = ?",
                (hoje.isoformat(), multa, id_aluguel))
    con.commit()
    con.close()
    return multa


def montar_aluguel(linha):
    a = dict(linha)
    if a["titulo"] is None:
        a["titulo"] = "(livro removido)"
        a["autor"] = ""
    if a["data_devolucao"] is None and a["tipo"] == "loja":
        a["multa"] = calcular_multa(a["data_prevista"], date.today())
        a["atrasado"] = a["multa"] > 0
    else:
        a["multa"] = 0
        a["atrasado"] = False
    return a


def listar_alugueis(id_cliente=None, so_ativos=False):
    sql = """
        SELECT a.*, l.titulo, l.autor, l.capa, l.ebook, c.nome AS cliente
        FROM alugueis a
        LEFT JOIN livros l ON l.id = a.livro_id
        LEFT JOIN clientes c ON c.id = a.cliente_id
        WHERE 1 = 1
    """
    params = []
    if id_cliente is not None:
        sql += " AND a.cliente_id = ?"
        params.append(id_cliente)
    if so_ativos:
        sql += " AND a.data_devolucao IS NULL"
    sql += " ORDER BY a.data_devolucao IS NOT NULL, a.data_prevista"

    encerrar_ebooks_vencidos()
    con = conectar()
    linhas = con.execute(sql, params).fetchall()
    con.close()
    return [montar_aluguel(l) for l in linhas]


def resumo():
    encerrar_ebooks_vencidos()
    con = conectar()
    dados = {
        "titulos": con.execute("SELECT COUNT(*) FROM livros").fetchone()[0],
        "exemplares": con.execute("SELECT COALESCE(SUM(estoque), 0) FROM livros").fetchone()[0],
        "clientes": con.execute("SELECT COUNT(*) FROM clientes").fetchone()[0],
        "ativos": con.execute("SELECT COUNT(*) FROM alugueis WHERE data_devolucao IS NULL").fetchone()[0],
        "faturamento": con.execute("SELECT COALESCE(SUM(valor), 0) FROM alugueis").fetchone()[0],
        "entregas": con.execute("SELECT COUNT(*) FROM pedidos WHERE status != 'entregue'").fetchone()[0],
        "vendas": con.execute("SELECT COALESCE(SUM(valor), 0) FROM pedidos").fetchone()[0],
        "parcerias": con.execute("SELECT COUNT(*) FROM parcerias WHERE status = 'pendente'").fetchone()[0],
    }
    con.close()
    return dados


# fornecedores e entregadores

def cadastrar_fornecedor(nome, cnpj, telefone, cep, cidade, distancia, veiculo):
    con = conectar()
    try:
        con.execute("INSERT INTO fornecedores (nome, cnpj, telefone, cep, cidade, distancia_km, veiculo) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (nome, cnpj, telefone, cep, cidade, distancia, veiculo))
        con.commit()
        ok = True
    except sqlite3.IntegrityError:
        ok = False
    con.close()
    return ok


def listar_fornecedores():
    con = conectar()
    fornecedores = con.execute("""
        SELECT f.*, (SELECT COUNT(*) FROM livros l WHERE l.fornecedor_id = f.id) AS livros
        FROM fornecedores f ORDER BY f.nome
    """).fetchall()
    con.close()
    return fornecedores


def cadastrar_entregador(nome, cpf, telefone, veiculo, placa):
    con = conectar()
    try:
        con.execute("INSERT INTO entregadores (nome, cpf, telefone, veiculo, placa) VALUES (?, ?, ?, ?, ?)",
                    (nome, cpf, telefone, veiculo, placa))
        con.commit()
        ok = True
    except sqlite3.IntegrityError:
        ok = False
    con.close()
    return ok


def listar_entregadores():
    con = conectar()
    entregadores = con.execute("""
        SELECT e.*, (SELECT COUNT(*) FROM pedidos p WHERE p.entregador_id = e.id AND p.status != 'entregue') AS abertos
        FROM entregadores e ORDER BY e.nome
    """).fetchall()
    con.close()
    return entregadores


# compras e entregas

STATUS_PEDIDO = ["aguardando fornecedor", "separando", "em rota", "entregue"]


def calcular_prazo(id_livro, km_cliente):
    con = conectar()
    livro = con.execute("SELECT * FROM livros WHERE id = ?", (id_livro,)).fetchone()
    if livro is None:
        con.close()
        return {"erro": "Livro não encontrado."}

    fornecedor = None
    if livro["estoque"] <= 0:
        fornecedor = con.execute("SELECT * FROM fornecedores WHERE id = ?", (livro["fornecedor_id"],)).fetchone()
        if fornecedor is None:
            con.close()
            return {"erro": "Esse livro está sem estoque e não tem fornecedor cadastrado."}

    # pega o entregador com menos entregas em aberto
    entregador = con.execute("""
        SELECT e.*, (SELECT COUNT(*) FROM pedidos p WHERE p.entregador_id = e.id AND p.status != 'entregue') AS abertos
        FROM entregadores e ORDER BY abertos, e.id LIMIT 1
    """).fetchone()
    con.close()
    if entregador is None:
        return {"erro": "Nenhum entregador disponível no momento."}

    horas = None
    if km_cliente is not None:
        horas = HORAS_SEPARACAO + km_cliente / VEICULOS[entregador["veiculo"]]
        if fornecedor is not None:
            horas += fornecedor["distancia_km"] / VEICULOS[fornecedor["veiculo"]]
    return {"erro": None, "livro": livro, "fornecedor": fornecedor, "entregador": entregador, "horas": horas}


def registrar_pedido(id_cliente, id_livro, cep, endereco, km_cliente):
    prazo = calcular_prazo(id_livro, km_cliente)
    if prazo["erro"]:
        return prazo["erro"]
    livro = prazo["livro"]
    fornecedor = prazo["fornecedor"]
    status = "aguardando fornecedor" if fornecedor else "separando"

    con = conectar()
    con.execute("""INSERT INTO pedidos (cliente_id, livro_id, entregador_id, fornecedor_id, data_pedido, cep, endereco,
                                        distancia_km, horas_previstas, valor, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (id_cliente, id_livro, prazo["entregador"]["id"], fornecedor["id"] if fornecedor else None,
                 datetime.now().strftime("%Y-%m-%d %H:%M"), cep, endereco, km_cliente, prazo["horas"],
                 livro["preco"], status))
    if fornecedor is None:
        con.execute("UPDATE livros SET estoque = estoque - 1 WHERE id = ?", (id_livro,))
    con.commit()
    con.close()
    return None


def montar_pedido(linha):
    p = dict(linha)
    if p["titulo"] is None:
        p["titulo"] = "(livro removido)"
    p["previsao"] = None
    if p["horas_previstas"] is not None:
        feito = datetime.strptime(p["data_pedido"], "%Y-%m-%d %H:%M")
        p["previsao"] = (feito + timedelta(hours=p["horas_previstas"])).strftime("%d/%m/%Y %H:%M")
    return p


def listar_pedidos(id_cliente=None):
    sql = """
        SELECT p.*, l.titulo, l.autor, l.capa, c.nome AS cliente, e.nome AS entregador, e.veiculo,
               f.nome AS fornecedor
        FROM pedidos p
        LEFT JOIN livros l ON l.id = p.livro_id
        LEFT JOIN clientes c ON c.id = p.cliente_id
        LEFT JOIN entregadores e ON e.id = p.entregador_id
        LEFT JOIN fornecedores f ON f.id = p.fornecedor_id
    """
    params = []
    if id_cliente is not None:
        sql += " WHERE p.cliente_id = ?"
        params.append(id_cliente)
    sql += " ORDER BY p.status = 'entregue', p.id DESC"

    con = conectar()
    linhas = con.execute(sql, params).fetchall()
    con.close()
    return [montar_pedido(l) for l in linhas]


def mudar_status_pedido(id_pedido, status):
    con = conectar()
    cur = con.execute("UPDATE pedidos SET status = ? WHERE id = ?", (status, id_pedido))
    con.commit()
    ok = cur.rowcount > 0
    con.close()
    return ok


# parcerias

def cadastrar_parceria(tipo, nome, email, telefone, cidade, proposta):
    con = conectar()
    con.execute("INSERT INTO parcerias (tipo, nome, email, telefone, cidade, proposta, data, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (tipo, nome, email, telefone, cidade, proposta, date.today().isoformat(), "pendente"))
    con.commit()
    con.close()


def listar_parcerias():
    con = conectar()
    parcerias = con.execute("SELECT * FROM parcerias ORDER BY status != 'pendente', id DESC").fetchall()
    con.close()
    return parcerias


def mudar_status_parceria(id_parceria, status):
    con = conectar()
    con.execute("UPDATE parcerias SET status = ? WHERE id = ?", (status, id_parceria))
    con.commit()
    con.close()
