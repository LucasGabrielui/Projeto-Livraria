import getpass
import banco
import busca_web
import cookies


def ler_int(msg):
    while True:
        valor = input(msg)
        try:
            return int(valor)
        except ValueError:
            print("Digite um número inteiro.")


def ler_float(msg):
    while True:
        valor = input(msg).replace(",", ".")
        try:
            return float(valor)
        except ValueError:
            print("Digite um valor válido.")


def ler_cpf():
    while True:
        cpf = input("CPF (só números): ").strip()
        if len(cpf) == 11 and cpf.isdigit():
            return cpf
        print("CPF inválido, precisa ter 11 dígitos.")


def mostrar_livros(livros):
    if len(livros) == 0:
        print("Nenhum livro encontrado.")
        return
    print()
    print(f"{'ID':<4} {'Título':<35} {'Autor':<22} {'Ano':<6} {'Preço':>9} {'Estoque':>8}")
    for l in livros:
        ano = l[3] if l[3] else "-"
        print(f"{l[0]:<4} {l[1][:35]:<35} {l[2][:22]:<22} {str(ano):<6} {'R$ %.2f' % l[4]:>9} {l[5]:>8}")


def login():
    sessao = cookies.pegar_sessao()
    if sessao is not None:
        print(f"Bem-vindo de volta, {sessao['nome']}!")
        return sessao

    print("\n--- LOGIN ---")
    while True:
        ultimo = cookies.ultimo_usuario()
        if ultimo:
            usuario = input(f"Usuário [{ultimo}]: ").strip()
            if usuario == "":
                usuario = ultimo
        else:
            usuario = input("Usuário: ").strip()
        senha = getpass.getpass("Senha: ")

        func = banco.fazer_login(usuario, senha)
        if func is None:
            print("Usuário ou senha incorretos.")
        else:
            cookies.criar_sessao(func, usuario)
            print(f"Olá, {func['nome']}!")
            return cookies.pegar_sessao()


def menu_livros():
    while True:
        cookies.renovar_sessao()
        print("\n--- LIVROS ---")
        print("1 - Listar acervo")
        print("2 - Procurar por título ou autor")
        print("3 - Adicionar livro manualmente")
        print("4 - Adicionar livro pela internet")
        print("5 - Alterar estoque")
        print("6 - Remover livro")
        print("0 - Voltar")
        op = input("Opção: ").strip()

        if op == "1":
            mostrar_livros(banco.listar_livros())

        elif op == "2":
            pesquisas = cookies.ultimas_pesquisas()
            if pesquisas:
                print("Últimas pesquisas:", ", ".join(pesquisas))
            texto = input("Digite o título ou autor: ").strip()
            if texto == "":
                print("Pesquisa vazia.")
                continue
            cookies.guardar_pesquisa(texto)
            mostrar_livros(banco.procurar_livros(texto))

        elif op == "3":
            titulo = input("Título: ").strip()
            autor = input("Autor: ").strip()
            if titulo == "" or autor == "":
                print("Título e autor são obrigatórios.")
                continue
            ano = ler_int("Ano de publicação: ")
            preco = ler_float("Preço: ")
            estoque = ler_int("Estoque: ")
            if banco.adicionar_livro(titulo, autor, ano, preco, estoque):
                print("Livro cadastrado!")
            else:
                print("Esse livro já está cadastrado.")

        elif op == "4":
            pesquisar_web()

        elif op == "5":
            id_livro = ler_int("ID do livro: ")
            livro = banco.buscar_livro_id(id_livro)
            if livro is None:
                print("Livro não encontrado.")
                continue
            print(f"{livro[1]} - estoque atual: {livro[5]}")
            estoque = ler_int("Novo estoque: ")
            if estoque < 0:
                print("Estoque não pode ser negativo.")
                continue
            banco.alterar_estoque(id_livro, estoque)
            print("Estoque atualizado!")

        elif op == "6":
            id_livro = ler_int("ID do livro: ")
            livro = banco.buscar_livro_id(id_livro)
            if livro is None:
                print("Livro não encontrado.")
                continue
            conf = input(f"Remover '{livro[1]}'? (s/n): ").strip().lower()
            if conf == "s":
                banco.remover_livro(id_livro)
                print("Livro removido!")

        elif op == "0":
            break

        else:
            print("Opção inválida.")


def pesquisar_web():
    pesquisas = cookies.ultimas_pesquisas()
    if pesquisas:
        print("Últimas pesquisas:", ", ".join(pesquisas))
    titulo = input("Título para pesquisar: ").strip()
    if titulo == "":
        print("Pesquisa vazia.")
        return
    cookies.guardar_pesquisa(titulo)

    print("Pesquisando na Open Library...")
    resultados = busca_web.pesquisar_livros(titulo)
    if resultados is None:
        print("Não foi possível acessar a internet. Tente de novo mais tarde.")
        return
    if len(resultados) == 0:
        print("Nenhum resultado encontrado.")
        return

    for i, r in enumerate(resultados, 1):
        ano = r["ano"] if r["ano"] else "-"
        dp = " [domínio público]" if r["publico"] else ""
        print(f"{i} - {r['titulo']} | {r['autor']} | {ano}{dp}")

    num = ler_int("Número do livro para cadastrar (0 para cancelar): ")
    if num == 0:
        return
    if num < 1 or num > len(resultados):
        print("Opção inválida.")
        return

    escolhido = resultados[num - 1]
    if banco.livro_existe(escolhido["titulo"], escolhido["autor"]):
        print("Esse livro já está cadastrado.")
        return
    preco = ler_float("Preço: ")
    estoque = ler_int("Estoque: ")
    banco.adicionar_livro(escolhido["titulo"], escolhido["autor"], escolhido["ano"], preco, estoque)
    print("Livro cadastrado!")


def menu_clientes():
    while True:
        cookies.renovar_sessao()
        print("\n--- CLIENTES ---")
        print("1 - Cadastrar cliente")
        print("2 - Listar clientes")
        print("3 - Buscar por CPF")
        print("0 - Voltar")
        op = input("Opção: ").strip()

        if op == "1":
            nome = input("Nome: ").strip()
            if nome == "":
                print("Nome é obrigatório.")
                continue
            cpf = ler_cpf()
            email = input("Email: ").strip()
            telefone = input("Telefone: ").strip()
            cidade = input("Cidade: ").strip()
            if banco.cadastrar_cliente(nome, cpf, email, telefone, cidade):
                print("Cliente cadastrado!")
            else:
                print("Já existe um cliente com esse CPF.")

        elif op == "2":
            clientes = banco.listar_clientes()
            if len(clientes) == 0:
                print("Nenhum cliente cadastrado.")
            for c in clientes:
                print(f"{c[0]} - {c[1]} | CPF: {c[2]} | {c[3]} | {c[4]} | {c[5]}")

        elif op == "3":
            cpf = ler_cpf()
            c = banco.buscar_cliente_cpf(cpf)
            if c is None:
                print("Cliente não encontrado.")
            else:
                print(f"Nome: {c[1]}\nCPF: {c[2]}\nEmail: {c[3]}\nTelefone: {c[4]}\nCidade: {c[5]}")

        elif op == "0":
            break

        else:
            print("Opção inválida.")


def menu_funcionarios():
    while True:
        cookies.renovar_sessao()
        print("\n--- FUNCIONÁRIOS ---")
        print("1 - Cadastrar funcionário")
        print("2 - Listar funcionários")
        print("0 - Voltar")
        op = input("Opção: ").strip()

        if op == "1":
            nome = input("Nome: ").strip()
            if nome == "":
                print("Nome é obrigatório.")
                continue
            cpf = ler_cpf()
            cargo = input("Cargo (vendedor, estoquista, gerente): ").strip().lower()
            if cargo not in ["vendedor", "estoquista", "gerente"]:
                print("Cargo inválido.")
                continue
            usuario = input("Usuário: ").strip()
            senha = getpass.getpass("Senha: ")
            if usuario == "" or senha == "":
                print("Usuário e senha são obrigatórios.")
                continue
            if banco.cadastrar_funcionario(nome, cpf, cargo, usuario, senha):
                print("Funcionário cadastrado!")
            else:
                print("CPF ou usuário já cadastrado.")

        elif op == "2":
            for f in banco.listar_funcionarios():
                print(f"{f[0]} - {f[1]} | CPF: {f[2]} | {f[3]} | usuário: {f[4]}")

        elif op == "0":
            break

        else:
            print("Opção inválida.")


def main():
    banco.criar_tabelas()
    print("=== LIVRARIA ===")
    sessao = login()

    while True:
        cookies.renovar_sessao()
        print(f"\n--- MENU PRINCIPAL ({sessao['nome']} - {sessao['cargo']}) ---")
        print("1 - Livros")
        print("2 - Clientes")
        print("3 - Funcionários")
        print("4 - Sair da conta")
        print("5 - Fechar")
        op = input("Opção: ").strip()

        if op == "1":
            menu_livros()
        elif op == "2":
            menu_clientes()
        elif op == "3":
            if sessao["cargo"] == "gerente":
                menu_funcionarios()
            else:
                print("Só o gerente pode acessar essa parte.")
        elif op == "4":
            cookies.apagar_sessao()
            print("Você saiu da conta.")
            sessao = login()
        elif op == "5":
            print("Até mais!")
            break
        else:
            print("Opção inválida.")


main()
