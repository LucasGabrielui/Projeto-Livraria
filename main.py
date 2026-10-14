import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
import banco
import busca_web

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "chave-da-livraria-trocar-em-producao")

CARGOS = ["vendedor", "estoquista", "gerente"]


def moeda(valor):
    texto = f"{valor:,.2f}"
    return "R$ " + texto.replace(",", "#").replace(".", ",").replace("#", ".")


def data_br(texto):
    if not texto:
        return "-"
    ano, mes, dia = texto.split("-")
    return f"{dia}/{mes}/{ano}"


app.jinja_env.filters["moeda"] = moeda
app.jinja_env.filters["data"] = data_br


@app.context_processor
def variaveis_globais():
    return {
        "valor_semana": banco.VALOR_SEMANA,
        "max_semanas": banco.MAX_SEMANAS,
        "tipo": session.get("tipo"),
        "nome_logado": session.get("nome"),
        "cargo": session.get("cargo"),
    }


def so_cliente(func):
    @wraps(func)
    def verificar(*args, **kwargs):
        if session.get("tipo") != "cliente":
            flash("Entre na sua conta para continuar.", "aviso")
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return verificar


def so_funcionario(func):
    @wraps(func)
    def verificar(*args, **kwargs):
        if session.get("tipo") != "funcionario":
            flash("Área restrita aos funcionários.", "aviso")
            return redirect(url_for("admin_login"))
        return func(*args, **kwargs)
    return verificar


def so_gerente(func):
    @wraps(func)
    def verificar(*args, **kwargs):
        if session.get("tipo") != "funcionario":
            return redirect(url_for("admin_login"))
        if session.get("cargo") != "gerente":
            flash("Só o gerente pode acessar essa parte.", "erro")
            return redirect(url_for("painel"))
        return func(*args, **kwargs)
    return verificar


def ler_int(texto, padrao=None):
    try:
        return int(texto)
    except (TypeError, ValueError):
        return padrao


def ler_float(texto, padrao=None):
    try:
        return float(str(texto).replace(",", "."))
    except (TypeError, ValueError):
        return padrao


def limpar_cpf(texto):
    cpf = "".join(c for c in texto if c.isdigit())
    if len(cpf) != 11:
        return None
    return cpf


# area do cliente

@app.route("/")
def inicio():
    busca = request.args.get("q", "").strip()
    if busca:
        livros = banco.procurar_livros(busca)
    else:
        livros = banco.listar_livros()
    return render_template("inicio.html", livros=livros, busca=busca)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")
        cliente = banco.login_cliente(email, senha)
        if cliente is None:
            flash("Email ou senha incorretos.", "erro")
            return render_template("login.html", email=email)
        session.clear()
        session["tipo"] = "cliente"
        session["id"] = cliente["id"]
        session["nome"] = cliente["nome"]
        flash(f"Bem-vindo(a), {cliente['nome']}!", "sucesso")
        return redirect(url_for("inicio"))
    return render_template("login.html", email="")


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    form = request.form
    if request.method == "POST":
        nome = form.get("nome", "").strip()
        cpf = limpar_cpf(form.get("cpf", ""))
        email = form.get("email", "").strip()
        senha = form.get("senha", "")

        if nome == "" or email == "" or senha == "":
            flash("Preencha nome, email e senha.", "erro")
        elif cpf is None:
            flash("CPF inválido, precisa ter 11 dígitos.", "erro")
        elif len(senha) < 4:
            flash("A senha precisa ter pelo menos 4 caracteres.", "erro")
        elif senha != form.get("confirmar", ""):
            flash("As senhas não conferem.", "erro")
        elif not banco.cadastrar_cliente(nome, cpf, email, form.get("telefone", "").strip(),
                                         form.get("cidade", "").strip(), senha):
            flash("Já existe uma conta com esse CPF ou email.", "erro")
        else:
            flash("Conta criada! Agora é só entrar.", "sucesso")
            return redirect(url_for("login"))
    return render_template("cadastro.html", form=form)


@app.route("/sair")
def sair():
    era_funcionario = session.get("tipo") == "funcionario"
    session.clear()
    flash("Você saiu da conta.", "sucesso")
    if era_funcionario:
        return redirect(url_for("admin_login"))
    return redirect(url_for("inicio"))


@app.route("/livro/<int:id_livro>/alugar", methods=["POST"])
@so_cliente
def alugar(id_livro):
    semanas = ler_int(request.form.get("semanas"), 1)
    erro = banco.alugar_livro(session["id"], id_livro, semanas)
    if erro:
        flash(erro, "erro")
        return redirect(url_for("inicio"))
    flash(f"Livro alugado por {semanas} semana(s). Total: {moeda(semanas * banco.VALOR_SEMANA)}.", "sucesso")
    return redirect(url_for("minha_estante"))


@app.route("/minha-estante")
@so_cliente
def minha_estante():
    alugueis = banco.listar_alugueis(id_cliente=session["id"])
    ativos = [a for a in alugueis if a["data_devolucao"] is None]
    historico = [a for a in alugueis if a["data_devolucao"] is not None]
    return render_template("minha_estante.html", ativos=ativos, historico=historico)


# area administrativa

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        func = banco.login_funcionario(usuario, request.form.get("senha", ""))
        if func is None:
            flash("Usuário ou senha incorretos.", "erro")
            return render_template("admin/login.html", usuario=usuario)
        session.clear()
        session["tipo"] = "funcionario"
        session["id"] = func["id"]
        session["nome"] = func["nome"]
        session["cargo"] = func["cargo"]
        return redirect(url_for("painel"))
    return render_template("admin/login.html", usuario="")


@app.route("/admin")
@so_funcionario
def painel():
    atrasados = [a for a in banco.listar_alugueis(so_ativos=True) if a["atrasado"]]
    return render_template("admin/painel.html", dados=banco.resumo(), atrasados=atrasados)


@app.route("/admin/livros", methods=["GET", "POST"])
@so_funcionario
def admin_livros():
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        autor = request.form.get("autor", "").strip()
        ano = ler_int(request.form.get("ano"))
        preco = ler_float(request.form.get("preco"))
        estoque = ler_int(request.form.get("estoque"))
        if titulo == "" or autor == "":
            flash("Título e autor são obrigatórios.", "erro")
        elif preco is None or preco < 0 or estoque is None or estoque < 0:
            flash("Preço e estoque precisam ser números positivos.", "erro")
        elif banco.adicionar_livro(titulo, autor, ano, preco, estoque):
            flash(f"'{titulo}' cadastrado!", "sucesso")
        else:
            flash("Esse livro já está cadastrado.", "erro")
        return redirect(url_for("admin_livros"))

    busca = request.args.get("q", "").strip()
    livros = banco.procurar_livros(busca) if busca else banco.listar_livros()
    return render_template("admin/livros.html", livros=livros, busca=busca)


@app.route("/admin/livros/<int:id_livro>/editar", methods=["POST"])
@so_funcionario
def editar_livro(id_livro):
    preco = ler_float(request.form.get("preco"))
    estoque = ler_int(request.form.get("estoque"))
    if preco is None or preco < 0 or estoque is None or estoque < 0:
        flash("Valores inválidos.", "erro")
    elif banco.editar_livro(id_livro, preco, estoque):
        flash("Livro atualizado!", "sucesso")
    return redirect(url_for("admin_livros", q=request.form.get("q", "")))


@app.route("/admin/livros/<int:id_livro>/remover", methods=["POST"])
@so_funcionario
def remover_livro(id_livro):
    if banco.remover_livro(id_livro):
        flash("Livro removido.", "sucesso")
    else:
        flash("Não dá pra remover um livro que está alugado.", "erro")
    return redirect(url_for("admin_livros"))


@app.route("/admin/livros/internet", methods=["GET", "POST"])
@so_funcionario
def buscar_internet():
    if request.method == "POST":
        titulo = request.form.get("titulo", "")
        autor = request.form.get("autor", "")
        preco = ler_float(request.form.get("preco"))
        estoque = ler_int(request.form.get("estoque"))
        if preco is None or preco < 0 or estoque is None or estoque < 0:
            flash("Informe preço e estoque válidos.", "erro")
        elif banco.adicionar_livro(titulo, autor, ler_int(request.form.get("ano")), preco, estoque):
            flash(f"'{titulo}' cadastrado!", "sucesso")
        else:
            flash("Esse livro já está cadastrado.", "erro")
        return redirect(url_for("buscar_internet", q=request.form.get("q", "")))

    busca = request.args.get("q", "").strip()
    resultados = []
    if busca:
        resultados = busca_web.pesquisar_livros(busca)
        if resultados is None:
            flash("Não foi possível acessar a Open Library. Tente de novo mais tarde.", "erro")
            resultados = []
    return render_template("admin/internet.html", resultados=resultados, busca=busca)


@app.route("/admin/clientes", methods=["GET", "POST"])
@so_funcionario
def admin_clientes():
    if request.method == "POST":
        form = request.form
        nome = form.get("nome", "").strip()
        cpf = limpar_cpf(form.get("cpf", ""))
        email = form.get("email", "").strip()
        senha = form.get("senha", "")
        if nome == "" or email == "" or senha == "":
            flash("Nome, email e senha são obrigatórios.", "erro")
        elif cpf is None:
            flash("CPF inválido, precisa ter 11 dígitos.", "erro")
        elif banco.cadastrar_cliente(nome, cpf, email, form.get("telefone", "").strip(),
                                     form.get("cidade", "").strip(), senha):
            flash("Cliente cadastrado!", "sucesso")
        else:
            flash("Já existe um cliente com esse CPF ou email.", "erro")
        return redirect(url_for("admin_clientes"))

    busca = request.args.get("q", "").strip()
    return render_template("admin/clientes.html", clientes=banco.listar_clientes(busca), busca=busca)


@app.route("/admin/alugueis")
@so_funcionario
def admin_alugueis():
    todos = request.args.get("todos") == "1"
    alugueis = banco.listar_alugueis(so_ativos=not todos)
    return render_template("admin/alugueis.html", alugueis=alugueis, todos=todos)


@app.route("/admin/alugueis/<int:id_aluguel>/devolver", methods=["POST"])
@so_funcionario
def devolver(id_aluguel):
    multa = banco.devolver_livro(id_aluguel)
    if multa is None:
        flash("Esse aluguel já foi devolvido.", "erro")
    elif multa > 0:
        flash(f"Devolução registrada com atraso. Cobrar {moeda(multa)} a mais.", "aviso")
    else:
        flash("Devolução registrada!", "sucesso")
    return redirect(url_for("admin_alugueis"))


@app.route("/admin/funcionarios", methods=["GET", "POST"])
@so_gerente
def admin_funcionarios():
    if request.method == "POST":
        form = request.form
        nome = form.get("nome", "").strip()
        cpf = limpar_cpf(form.get("cpf", ""))
        cargo = form.get("cargo", "")
        usuario = form.get("usuario", "").strip()
        senha = form.get("senha", "")
        if nome == "" or usuario == "" or senha == "":
            flash("Nome, usuário e senha são obrigatórios.", "erro")
        elif cpf is None:
            flash("CPF inválido, precisa ter 11 dígitos.", "erro")
        elif cargo not in CARGOS:
            flash("Cargo inválido.", "erro")
        elif banco.cadastrar_funcionario(nome, cpf, cargo, usuario, senha):
            flash("Funcionário cadastrado!", "sucesso")
        else:
            flash("CPF ou usuário já cadastrado.", "erro")
        return redirect(url_for("admin_funcionarios"))

    return render_template("admin/funcionarios.html", funcionarios=banco.listar_funcionarios(), cargos=CARGOS)


banco.criar_tabelas()

if __name__ == "__main__":
    app.run(debug=True)
