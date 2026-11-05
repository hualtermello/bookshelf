import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, mysql

def test_nome_no_cadastro_e_login():
    print("Iniciando teste de exibição do Nome de Cadastro no Login e Perfil...")
    
    email_teste = "escritor_paulo@bookshelf.com"
    nome_teste = "Paulo Silva Ferreira"
    cpf_teste = "12345678909"
    senha_teste = "SenhaForte123"

    with app.app_context():
        # Limpa resquício se houver
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM usuario WHERE usuario = %s OR cpf = %s", (email_teste, cpf_teste))
        mysql.connection.commit()
        cur.close()

    with app.test_client() as client:
        # 1. Faz o cadastro informando o Nome Completo
        res_cadastro = client.post('/cadastro', data={
            'nome': nome_teste,
            'email': email_teste,
            'senha': senha_teste,
            'confirmaSenha': senha_teste,
            'cpf': cpf_teste
        }, follow_redirects=True)
        assert res_cadastro.status_code == 200
        print("✓ Cadastro submetido com sucesso.")

        # 2. Verifica se o Nome foi gravado na coluna 'nome' do MySQL
        with app.app_context():
            cur = mysql.connection.cursor()
            cur.execute("SELECT id_usuario, nome, usuario, cpf FROM usuario WHERE usuario = %s", (email_teste,))
            user_db = cur.fetchone()
            cur.close()
            assert user_db is not None, "Usuário não encontrado no MySQL"
            assert user_db['nome'] == nome_teste, f"Esperado '{nome_teste}', gravado '{user_db['nome']}'"
            print(f"✓ Coluna 'nome' no MySQL conferida com sucesso: '{user_db['nome']}'")

        # 3. Realiza o login com o e-mail cadastrado
        res_login = client.post('/login', data={
            'email': email_teste,
            'senha': senha_teste
        }, follow_redirects=True)
        assert res_login.status_code == 200
        login_html = res_login.get_data(as_text=True)

        # 4. Verifica se na tela de Perfil o usuário é chamado pelo Nome e não pelo e-mail
        assert f"<h2>{nome_teste}</h2>" in login_html or nome_teste in login_html, f"Nome '{nome_teste}' não exibido no perfil"
        assert f"Olá, {nome_teste}!" in login_html, f"Saudação com nome 'Olá, {nome_teste}!' não exibida na navbar"
        print(f"✓ Perfil exibe o Nome de Cadastro: '{nome_teste}' ao invés do e-mail.")

        # 5. Verifica se na Home e Lançamentos o nome também aparece na barra de topo
        res_home = client.get('/')
        assert f"Olá, {nome_teste}!" in res_home.get_data(as_text=True)
        print(f"✓ Navbar da Home exibe 'Olá, {nome_teste}!'")

        res_lancamentos = client.get('/lancamentos')
        assert f"Olá, {nome_teste}!" in res_lancamentos.get_data(as_text=True)
        print(f"✓ Navbar de Lançamentos exibe 'Olá, {nome_teste}!'")

    # Limpeza do usuário de teste
    with app.app_context():
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM usuario WHERE usuario = %s", (email_teste,))
        mysql.connection.commit()
        cur.close()
        print("✓ Limpeza de usuário de teste finalizada.")

    print("\nTodos os testes de exibição do Nome passaram com 100% de sucesso! 🚀")

if __name__ == '__main__':
    test_nome_no_cadastro_e_login()
