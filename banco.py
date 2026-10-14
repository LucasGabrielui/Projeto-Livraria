import sqlite3
import hashlib
import secrets

ARQUIVO_BANCO = "livraria.db"


def conectar():
    con = sqlite3.connect(ARQUIVO_BANCO)
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
            cidade TEXT
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

    cur.execute("SELECT COUNT(*) FROM livros")
    if cur.fetchone()[0] == 0:
        livros = [
            ("Dom Casmurro", "Machado de Assis", 1899, 29.90, 10),
            ("Memórias Póstumas de Brás Cubas", "Machado de Assis", 1881, 32.50, 8),
            ("Quincas Borba", "Machado de Assis", 1891, 27.00, 5),
            ("O Alienista", "Machado de Assis", 1882, 19.90, 12),
            ("Iracema", "José de Alencar", 1865, 22.00, 7),
            ("O Guarani", "José de Alencar", 1857, 34.90, 6),
            ("Senhora", "José de Alencar", 1875, 25.00, 9),
            ("O Cortiço", "Aluísio Azevedo", 1890, 28.50, 10),
            ("Triste Fim de Policarpo Quaresma", "Lima Barreto", 1915, 26.90, 4),
            ("Os Sertões", "Euclides da Cunha", 1902, 45.00, 3),
            ("Orgulho e Preconceito", "Jane Austen", 1813, 39.90, 8),
            ("Frankenstein", "Mary Shelley", 1818, 35.00, 6),
            ("Dom Quixote", "Miguel de Cervantes", 1605, 59.90, 5),
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
    cur = con.cursor()
    cur.execute("SELECT * FROM livros ORDER BY titulo")
    livros = cur.fetchall()
    con.close()
    return livros


def procurar_livros(texto):
    con = conectar()
    cur = con.cursor()
    cur.execute("SELECT * FROM livros WHERE titulo LIKE ? OR autor LIKE ?", ("%" + texto + "%", "%" + texto + "%"))
    livros = cur.fetchall()
    con.close()
    return livros


def buscar_livro_id(id_livro):
    con = conectar()
    cur = con.cursor()
    cur.execute("SELECT * FROM livros WHERE id = ?", (id_livro,))
    livro = cur.fetchone()
    con.close()
    return livro


def livro_existe(titulo, autor):
    con = conectar()
    cur = con.cursor()
    cur.execute("SELECT id FROM livros WHERE lower(titulo) = lower(?) AND lower(autor) = lower(?)", (titulo.strip(), autor.strip()))
    achou = cur.fetchone()
    con.close()
    return achou is not None


def adicionar_livro(titulo, autor, ano, preco, estoque):
    if livro_existe(titulo, autor):
        return False
    con = conectar()
    cur = con.cursor()
    cur.execute("INSERT INTO livros (titulo, autor, ano, preco, estoque) VALUES (?, ?, ?, ?, ?)",
                (titulo.strip(), autor.strip(), ano, preco, estoque))
    con.commit()
    con.close()
    return True


def alterar_estoque(id_livro, estoque):
    con = conectar()
    cur = con.cursor()
    cur.execute("UPDATE livros SET estoque = ? WHERE id = ?", (estoque, id_livro))
    con.commit()
    ok = cur.rowcount > 0
    con.close()
    return ok


def remover_livro(id_livro):
    con = conectar()
    cur = con.cursor()
    cur.execute("DELETE FROM livros WHERE id = ?", (id_livro,))
    con.commit()
    ok = cur.rowcount > 0
    con.close()
    return ok


# clientes

def cadastrar_cliente(nome, cpf, email, telefone, cidade):
    con = conectar()
    cur = con.cursor()
    try:
        cur.execute("INSERT INTO clientes (nome, cpf, email, telefone, cidade) VALUES (?, ?, ?, ?, ?)",
                    (nome, cpf, email, telefone, cidade))
        con.commit()
        ok = True
    except sqlite3.IntegrityError:
        ok = False
    con.close()
    return ok


def listar_clientes():
    con = conectar()
    cur = con.cursor()
    cur.execute("SELECT * FROM clientes ORDER BY nome")
    clientes = cur.fetchall()
    con.close()
    return clientes


def buscar_cliente_cpf(cpf):
    con = conectar()
    cur = con.cursor()
    cur.execute("SELECT * FROM clientes WHERE cpf = ?", (cpf,))
    cliente = cur.fetchone()
    con.close()
    return cliente


# funcionarios

def cadastrar_funcionario(nome, cpf, cargo, usuario, senha):
    sal = secrets.token_hex(16)
    con = conectar()
    cur = con.cursor()
    try:
        cur.execute("INSERT INTO funcionarios (nome, cpf, cargo, usuario, senha, sal) VALUES (?, ?, ?, ?, ?, ?)",
                    (nome, cpf, cargo, usuario, gerar_hash(senha, sal), sal))
        con.commit()
        ok = True
    except sqlite3.IntegrityError:
        ok = False
    con.close()
    return ok


def listar_funcionarios():
    con = conectar()
    cur = con.cursor()
    cur.execute("SELECT id, nome, cpf, cargo, usuario FROM funcionarios ORDER BY nome")
    funcs = cur.fetchall()
    con.close()
    return funcs


def fazer_login(usuario, senha):
    con = conectar()
    cur = con.cursor()
    cur.execute("SELECT id, nome, cargo, senha, sal FROM funcionarios WHERE usuario = ?", (usuario,))
    func = cur.fetchone()
    con.close()
    if func is None:
        return None
    if gerar_hash(senha, func[4]) != func[3]:
        return None
    return {"id": func[0], "nome": func[1], "cargo": func[2]}
