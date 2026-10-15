import os
import math
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


def so_estoque(func):
    @wraps(func)
    def verificar(*args, **kwargs):
        if session.get("tipo") != "funcionario":
            return redirect(url_for("admin_login"))
        if session.get("cargo") not in ["gerente", "estoquista"]:
            flash("Só o gerente e o estoquista podem acessar essa parte.", "erro")
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


def so_numeros(texto, tamanho):
    numeros = "".join(c for c in texto if c.isdigit())
    if len(numeros) != tamanho:
        return None
    return numeros


# so aceita link de site, pra ninguem colocar javascript no lugar
def ler_link(texto):
    link = (texto or "").strip()
    if link == "":
        return None
    if not link.startswith(("https://", "http://")):
        return False
    return link


def prazo_texto(horas):
    if horas is None:
        return "indisponível"
    if horas < 24:
        return f"cerca de {max(1, round(horas))} hora(s)"
    return f"cerca de {math.ceil(horas / 24)} dia(s)"


app.jinja_env.filters["prazo"] = prazo_texto


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
    tipo = request.form.get("tipo", "loja")
    erro = banco.alugar_livro(session["id"], id_livro, semanas, tipo)
    if erro:
        flash(erro, "erro")
        return redirect(url_for("inicio"))
    if tipo == "online":
        flash(f"E-book liberado por {semanas} semana(s). Total: {moeda(semanas * banco.VALOR_SEMANA)}. É só clicar em Ler agora.", "sucesso")
    else:
        flash(f"Livro reservado por {semanas} semana(s). Total: {moeda(semanas * banco.VALOR_SEMANA)}. Retire na loja.", "sucesso")
    return redirect(url_for("minha_estante"))


@app.route("/minha-estante")
@so_cliente
def minha_estante():
    alugueis = banco.listar_alugueis(id_cliente=session["id"])
    ativos = [a for a in alugueis if a["data_devolucao"] is None]
    historico = [a for a in alugueis if a["data_devolucao"] is not None]
    return render_template("minha_estante.html", ativos=ativos, historico=historico)


@app.route("/livro/<int:id_livro>/comprar", methods=["GET", "POST"])
@so_cliente
def comprar(id_livro):
    livro = banco.buscar_livro_id(id_livro)
    if livro is None:
        flash("Livro não encontrado.", "erro")
        return redirect(url_for("inicio"))

    calculo = None
    if request.method == "POST" and request.form.get("acao") == "confirmar":
        compra = session.get("compra")
        if compra is None or compra["livro"] != id_livro:
            flash("Calcule o prazo antes de confirmar.", "erro")
            return redirect(url_for("comprar", id_livro=id_livro))
        erro = banco.registrar_pedido(session["id"], id_livro, compra["cep"], compra["endereco"], compra["km"])
        session.pop("compra", None)
        if erro:
            flash(erro, "erro")
            return redirect(url_for("inicio"))
        flash("Compra confirmada! Acompanhe a entrega em Meus pedidos.", "sucesso")
        return redirect(url_for("meus_pedidos"))

    if request.method == "POST":
        cep = so_numeros(request.form.get("cep", ""), 8)
        numero = request.form.get("numero", "").strip()
        complemento = request.form.get("complemento", "").strip()
        if cep is None:
            flash("CEP inválido, precisa ter 8 dígitos.", "erro")
        elif numero == "":
            flash("Informe o número da casa.", "erro")
        else:
            local = busca_web.distancia_ate_sede(cep)
            if local == {}:
                flash("CEP não encontrado.", "erro")
            else:
                if local is None:
                    flash("Sem conexão com o serviço de mapas, o prazo não pôde ser calculado.", "aviso")
                    local = {"km": None, "endereco": f"CEP {cep[:5]}-{cep[5:]}"}
                endereco = local["endereco"] + ", nº " + numero
                if complemento:
                    endereco += " - " + complemento
                calculo = banco.calcular_prazo(id_livro, local["km"])
                if calculo["erro"]:
                    flash(calculo["erro"], "erro")
                    return redirect(url_for("inicio"))
                calculo["km"] = local["km"]
                calculo["endereco"] = endereco
                session["compra"] = {"livro": id_livro, "cep": cep, "endereco": endereco, "km": local["km"]}

    return render_template("comprar.html", livro=livro, calculo=calculo, form=request.form,
                           velocidades=banco.VEICULOS, separacao=banco.HORAS_SEPARACAO)


@app.route("/meus-pedidos")
@so_cliente
def meus_pedidos():
    return render_template("meus_pedidos.html", pedidos=banco.listar_pedidos(id_cliente=session["id"]))


@app.route("/parcerias", methods=["GET", "POST"])
def parcerias():
    form = request.form
    if request.method == "POST":
        tipo = form.get("tipo", "")
        nome = form.get("nome", "").strip()
        email = form.get("email", "").strip()
        proposta = form.get("proposta", "").strip()
        if tipo not in ["livraria", "autor"]:
            flash("Escolha se é livraria ou autor.", "erro")
        elif nome == "" or email == "" or proposta == "":
            flash("Preencha nome, email e a proposta.", "erro")
        else:
            banco.cadastrar_parceria(tipo, nome, email, form.get("telefone", "").strip(),
                                     form.get("cidade", "").strip(), proposta)
            flash("Proposta enviada! Nossa equipe vai entrar em contato.", "sucesso")
            return redirect(url_for("parcerias"))
    return render_template("parcerias.html", form=form)


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
        ebook = ler_link(request.form.get("ebook"))
        if titulo == "" or autor == "":
            flash("Título e autor são obrigatórios.", "erro")
        elif preco is None or preco < 0 or estoque is None or estoque < 0:
            flash("Preço e estoque precisam ser números positivos.", "erro")
        elif ebook is False:
            flash("O link do e-book precisa começar com https://", "erro")
        elif banco.adicionar_livro(titulo, autor, ano, preco, estoque, ebook=ebook):
            flash(f"'{titulo}' cadastrado!", "sucesso")
        else:
            flash("Esse livro já está cadastrado.", "erro")
        return redirect(url_for("admin_livros"))

    busca = request.args.get("q", "").strip()
    livros = banco.procurar_livros(busca) if busca else banco.listar_livros()
    return render_template("admin/livros.html", livros=livros, busca=busca, fornecedores=banco.listar_fornecedores())


@app.route("/admin/livros/<int:id_livro>/editar", methods=["POST"])
@so_funcionario
def editar_livro(id_livro):
    preco = ler_float(request.form.get("preco"))
    estoque = ler_int(request.form.get("estoque"))
    fornecedor = ler_int(request.form.get("fornecedor"))
    ebook = ler_link(request.form.get("ebook"))
    if preco is None or preco < 0 or estoque is None or estoque < 0:
        flash("Valores inválidos.", "erro")
    elif ebook is False:
        flash("O link do e-book precisa começar com https://", "erro")
    elif banco.editar_livro(id_livro, preco, estoque, fornecedor, ebook):
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
        elif banco.adicionar_livro(titulo, autor, ler_int(request.form.get("ano")), preco, estoque,
                                   ler_int(request.form.get("capa"))):
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


@app.route("/admin/entregas")
@so_funcionario
def admin_entregas():
    return render_template("admin/entregas.html", pedidos=banco.listar_pedidos(), status=banco.STATUS_PEDIDO)


@app.route("/admin/entregas/<int:id_pedido>/status", methods=["POST"])
@so_funcionario
def status_entrega(id_pedido):
    status = request.form.get("status", "")
    if status in banco.STATUS_PEDIDO and banco.mudar_status_pedido(id_pedido, status):
        flash("Situação da entrega atualizada!", "sucesso")
    else:
        flash("Situação inválida.", "erro")
    return redirect(url_for("admin_entregas"))


@app.route("/admin/fornecedores", methods=["GET", "POST"])
@so_estoque
def admin_fornecedores():
    if request.method == "POST":
        form = request.form
        nome = form.get("nome", "").strip()
        cnpj = so_numeros(form.get("cnpj", ""), 14)
        cep = so_numeros(form.get("cep", ""), 8)
        veiculo = form.get("veiculo", "")
        distancia = ler_float(form.get("distancia"))
        cidade = form.get("cidade", "").strip()
        if nome == "":
            flash("Nome é obrigatório.", "erro")
        elif cnpj is None:
            flash("CNPJ inválido, precisa ter 14 dígitos.", "erro")
        elif cep is None:
            flash("CEP inválido, precisa ter 8 dígitos.", "erro")
        elif veiculo not in banco.VEICULOS:
            flash("Veículo inválido.", "erro")
        else:
            # se nao digitou a distancia tenta calcular pelo cep
            if distancia is None:
                local = busca_web.distancia_ate_sede(cep)
                if local:
                    distancia = local["km"]
                    cidade = local["cidade"]
            if distancia is None or distancia < 0:
                flash("Não deu pra calcular a distância pelo CEP. Digite a distância em km.", "erro")
            elif banco.cadastrar_fornecedor(nome, cnpj, form.get("telefone", "").strip(), cep, cidade, distancia, veiculo):
                flash(f"Fornecedor cadastrado! Fica a {distancia:.0f} km da sede.", "sucesso")
            else:
                flash("Já existe um fornecedor com esse CNPJ.", "erro")
        return redirect(url_for("admin_fornecedores"))

    return render_template("admin/fornecedores.html", fornecedores=banco.listar_fornecedores(),
                           veiculos=banco.VEICULOS)


@app.route("/admin/entregadores", methods=["GET", "POST"])
@so_estoque
def admin_entregadores():
    if request.method == "POST":
        form = request.form
        nome = form.get("nome", "").strip()
        cpf = limpar_cpf(form.get("cpf", ""))
        veiculo = form.get("veiculo", "")
        if nome == "":
            flash("Nome é obrigatório.", "erro")
        elif cpf is None:
            flash("CPF inválido, precisa ter 11 dígitos.", "erro")
        elif veiculo not in banco.VEICULOS:
            flash("Veículo inválido.", "erro")
        elif banco.cadastrar_entregador(nome, cpf, form.get("telefone", "").strip(), veiculo,
                                        form.get("placa", "").strip().upper()):
            flash("Entregador cadastrado!", "sucesso")
        else:
            flash("Já existe um entregador com esse CPF.", "erro")
        return redirect(url_for("admin_entregadores"))

    return render_template("admin/entregadores.html", entregadores=banco.listar_entregadores(),
                           veiculos=banco.VEICULOS)


@app.route("/admin/parcerias")
@so_estoque
def admin_parcerias():
    return render_template("admin/parcerias.html", parcerias=banco.listar_parcerias())


@app.route("/admin/parcerias/<int:id_parceria>/status", methods=["POST"])
@so_estoque
def status_parceria(id_parceria):
    status = request.form.get("status", "")
    if status in ["aprovada", "recusada"]:
        banco.mudar_status_parceria(id_parceria, status)
        flash(f"Parceria {status}.", "sucesso")
    return redirect(url_for("admin_parcerias"))


banco.criar_tabelas()

if __name__ == "__main__":
    app.run(debug=True)
