import sqlite3
import hashlib
import secrets
import math
from datetime import date, timedelta

ARQUIVO_BANCO = "livraria.db"
VALOR_SEMANA = 50.00
MAX_ALUGUEIS = 3
MAX_SEMANAS = 4


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
            estoque INTEGER
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
            valor REAL NOT NULL
        )
    """)

    # o banco da primeira versao nao tinha senha pros clientes
    colunas = [c["name"] for c in cur.execute("PRAGMA table_info(clientes)").fetchall()]
    if "senha" not in colunas:
        cur.execute("ALTER TABLE clientes ADD COLUMN senha TEXT")
        cur.execute("ALTER TABLE clientes ADD COLUMN sal TEXT")

    cur.execute("SELECT COUNT(*) FROM livros")
    if cur.fetchone()[0] == 0:
        livros = [
            ("Dom Casmurro", "Machado de Assis", 1899, 39.90, 10),
            ("Memórias Póstumas de Brás Cubas", "Machado de Assis", 1881, 44.90, 8),
            ("Quincas Borba", "Machado de Assis", 1891, 42.90, 5),
            ("O Alienista", "Machado de Assis", 1882, 24.90, 12),
            ("Iracema", "José de Alencar", 1865, 29.90, 7),
            ("O Guarani", "José de Alencar", 1857, 49.90, 6),
            ("Senhora", "José de Alencar", 1875, 34.90, 9),
            ("O Cortiço", "Aluísio Azevedo", 1890, 37.90, 10),
            ("Triste Fim de Policarpo Quaresma", "Lima Barreto", 1915, 39.90, 4),
            ("Os Sertões", "Euclides da Cunha", 1902, 89.90, 3),
            ("Vidas Secas", "Graciliano Ramos", 1938, 49.90, 6),
            ("Capitães da Areia", "Jorge Amado", 1937, 59.90, 5),
            ("Grande Sertão: Veredas", "João Guimarães Rosa", 1956, 99.90, 3),
            ("A Hora da Estrela", "Clarice Lispector", 1977, 54.90, 6),
            ("Orgulho e Preconceito", "Jane Austen", 1813, 54.90, 8),
            ("Frankenstein", "Mary Shelley", 1818, 49.90, 6),
            ("1984", "George Orwell", 1949, 59.90, 7),
            ("O Pequeno Príncipe", "Antoine de Saint-Exupéry", 1943, 34.90, 9),
            ("Dom Quixote", "Miguel de Cervantes", 1605, 129.90, 2),
        ]
        cur.executemany("INSERT INTO livros (titulo, autor, ano, preco, estoque) VALUES (?, ?, ?, ?, ?)", livros)

    # usuario padrao pra conseguir entrar a primeira vez
    cur.execute("SELECT COUNT(*) FROM funcionarios")
    if cur.fetchone()[0] == 0:
        sal = secrets.token_hex(16)
        cur.execute("INSERT INTO funcionarios (nome, cpf, cargo, usuario, senha, sal) VALUES (?, ?, ?, ?, ?, ?)",
                    ("Administrador", "00000000000", "gerente", "admin", gerar_hash("admin", sal), sal))

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


def adicionar_livro(titulo, autor, ano, preco, estoque):
    if livro_existe(titulo, autor):
        return False
    con = conectar()
    con.execute("INSERT INTO livros (titulo, autor, ano, preco, estoque) VALUES (?, ?, ?, ?, ?)",
                (titulo.strip(), autor.strip(), ano, preco, estoque))
    con.commit()
    con.close()
    return True


def editar_livro(id_livro, preco, estoque):
    con = conectar()
    cur = con.execute("UPDATE livros SET preco = ?, estoque = ? WHERE id = ?", (preco, estoque, id_livro))
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


def alugar_livro(id_cliente, id_livro, semanas):
    if semanas < 1 or semanas > MAX_SEMANAS:
        return "Quantidade de semanas inválida."

    con = conectar()
    livro = con.execute("SELECT estoque FROM livros WHERE id = ?", (id_livro,)).fetchone()
    if livro is None or livro["estoque"] <= 0:
        con.close()
        return "Esse livro não está disponível no momento."

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
    con.execute("""INSERT INTO alugueis (cliente_id, livro_id, data_inicio, data_prevista, semanas, valor)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (id_cliente, id_livro, hoje.isoformat(), prevista.isoformat(), semanas, semanas * VALOR_SEMANA))
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
    multa = calcular_multa(a["data_prevista"], hoje)
    con.execute("UPDATE alugueis SET data_devolucao = ?, valor = valor + ? WHERE id = ?",
                (hoje.isoformat(), multa, id_aluguel))
    con.execute("UPDATE livros SET estoque = estoque + 1 WHERE id = ?", (a["livro_id"],))
    con.commit()
    con.close()
    return multa


def montar_aluguel(linha):
    a = dict(linha)
    if a["titulo"] is None:
        a["titulo"] = "(livro removido)"
        a["autor"] = ""
    if a["data_devolucao"] is None:
        a["multa"] = calcular_multa(a["data_prevista"], date.today())
        a["atrasado"] = a["multa"] > 0
    else:
        a["multa"] = 0
        a["atrasado"] = False
    return a


def listar_alugueis(id_cliente=None, so_ativos=False):
    sql = """
        SELECT a.*, l.titulo, l.autor, c.nome AS cliente
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

    con = conectar()
    linhas = con.execute(sql, params).fetchall()
    con.close()
    return [montar_aluguel(l) for l in linhas]


def resumo():
    con = conectar()
    dados = {
        "titulos": con.execute("SELECT COUNT(*) FROM livros").fetchone()[0],
        "exemplares": con.execute("SELECT COALESCE(SUM(estoque), 0) FROM livros").fetchone()[0],
        "clientes": con.execute("SELECT COUNT(*) FROM clientes").fetchone()[0],
        "ativos": con.execute("SELECT COUNT(*) FROM alugueis WHERE data_devolucao IS NULL").fetchone()[0],
        "faturamento": con.execute("SELECT COALESCE(SUM(valor), 0) FROM alugueis").fetchone()[0],
    }
    con.close()
    return dados
