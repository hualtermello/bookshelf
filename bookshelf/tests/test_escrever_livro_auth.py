import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, mysql

def test_escrever_livro_auth():
    print("Iniciando testes de controle de acesso ao módulo de Escrever Livro (Modelo Gráfica)...")
    
    with app.test_client() as client:
        # 1. Usuário NÃO LOGADO acessando /modelo-grafica ou /escrever
        res_visitante = client.get('/modelo-grafica')
        assert res_visitante.status_code == 200, f"Esperado 200, obtido {res_visitante.status_code}"
        html_visitante = res_visitante.get_data(as_text=True)

        assert "window.USUARIO_LOGADO = false;" in html_visitante, "Flag USUARIO_LOGADO não está false para visitante"
        assert "modalLoginObrigatorio" in html_visitante, "Modal de login obrigatório não encontrado no HTML"
        assert "Modo Escolha de Modelo (Visitante)" in html_visitante, "Banner de modo visitante ausente"
        assert "grafica-genres-selector" in html_visitante, "Seletor de modelos e gêneros ausente"
        assert "Fazer Login" in html_visitante, "Botão para Fazer Login ausente na página"
        print("✓ Visitante não logado acessa página no Modo Escolha com seletores e modal de login prontos.")

        # 2. Rota alternativa /escrever
        res_escrever = client.get('/escrever')
        assert res_escrever.status_code == 200
        assert "window.USUARIO_LOGADO = false;" in res_escrever.get_data(as_text=True)
        print("✓ Rota /escrever responde com os mesmos controles de segurança e escolha.")

        # 3. Tentativa de salvar via API sem autenticação
        payload = {
            'meta': {'titulo': 'Meu Livro Sem Login', 'autor': 'Anônimo'},
            'paginasMiolo': [{'id': 'm1', 'capituloTitulo': 'Cap 1', 'conteudo': 'Texto'}]
        }
        res_salvar_anonimo = client.post(
            '/api/modelo-grafica/salvar',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert res_salvar_anonimo.status_code == 401, f"Esperado 401 para salvar anônimo, obtido {res_salvar_anonimo.status_code}"
        dados_salvar = json.loads(res_salvar_anonimo.get_data(as_text=True))
        assert dados_salvar.get('precisa_login') is True, "Flag precisa_login ausente na resposta de salvar"
        print("✓ API /api/modelo-grafica/salvar bloqueia usuário anônimo com status 401 e precisa_login: True.")

        # 4. Tentativa de publicar via API sem autenticação
        res_publicar_anonimo = client.post(
            '/api/modelo-grafica/publicar',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert res_publicar_anonimo.status_code == 401, f"Esperado 401 para publicar anônimo, obtido {res_publicar_anonimo.status_code}"
        dados_publicar = json.loads(res_publicar_anonimo.get_data(as_text=True))
        assert dados_publicar.get('precisa_login') is True
        print("✓ API /api/modelo-grafica/publicar bloqueia usuário anônimo com status 401 e precisa_login: True.")

        # Cria ou obtém usuário válido no banco
        with app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT id_usuario, nome, usuario FROM usuario LIMIT 1")
            user_db = cursor.fetchone()
            if not user_db:
                cursor.execute(
                    "INSERT INTO usuario (nome, usuario, senha_hash, cpf) VALUES (%s, %s, %s, %s)",
                    ('Carlos Escritor', 'carlos_escritor@teste.com', 'hash_teste_123', '88877766655')
                )
                mysql.connection.commit()
                user_id = cursor.lastrowid
                user_nome = 'Carlos Escritor'
                user_email = 'carlos_escritor@teste.com'
            else:
                user_id = user_db['id_usuario'] if isinstance(user_db, dict) else user_db[0]
                user_nome = user_db['nome'] if isinstance(user_db, dict) else user_db[1]
                user_email = user_db['usuario'] if isinstance(user_db, dict) else user_db[2]
            cursor.close()

        # 5. Usuário LOGADO acessando o editor
        nome_autor_teste = 'Carlos Escritor'
        with client.session_transaction() as sess:
            sess['usuario_id'] = user_id
            sess['username'] = user_email
            sess['nome'] = nome_autor_teste

        res_logado = client.get('/modelo-grafica')
        assert res_logado.status_code == 200
        html_logado = res_logado.get_data(as_text=True)
        assert "window.USUARIO_LOGADO = true;" in html_logado, "Flag USUARIO_LOGADO não está true para usuário logado"
        assert "Modo Autor Ativo" in html_logado, "Banner de autor ativo ausente para usuário logado"
        assert nome_autor_teste in html_logado, "Identificação do autor logado ausente no banner"
        print("✓ Usuário logado recebe flag USUARIO_LOGADO = true e visualiza a escrita completa liberada.")

        # 6. Usuário logado salvando modelo com sucesso
        res_salvar_logado = client.post(
            '/api/modelo-grafica/salvar',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert res_salvar_logado.status_code == 200, f"Esperado 200 para salvar logado, obtido {res_salvar_logado.status_code}"
        dados_salvar_logado = json.loads(res_salvar_logado.get_data(as_text=True))
        assert dados_salvar_logado.get('ok') is True
        print("✓ Usuário logado salva o modelo no banco de dados com sucesso.")

        # 7. Validação das funções e interceptadores no arquivo JS
        caminho_js = os.path.join(os.path.dirname(__file__), '..', 'static', 'js', 'modelo_grafica.js')
        with open(caminho_js, 'r', encoding='utf-8') as f:
            js_content = f.read()

        assert "abrirPopupLogin" in js_content, "Função abrirPopupLogin ausente no JS"
        assert "fecharPopupLogin" in js_content, "Função fecharPopupLogin ausente no JS"
        assert "modalLoginObrigatorio" in js_content, "Referência ao modalLoginObrigatorio ausente no JS"
        assert "escrita-restrita-box" in js_content, "Classe escrita-restrita-box ausente no JS"
        assert "beforeunload" in js_content, "Listener beforeunload para saída da página ausente no JS"
        assert "presetsGeneros" in js_content, "Presets de escolha de gênero ausentes no JS"
        print("✓ Arquivo modelo_grafica.js contém todos os interceptadores de salvar, sair e caixas de restrição.")

    print("\nTODOS OS TESTES DE CONTROLE DE ESCRITA E POPUP DE LOGIN PASSARAM COM 100% DE SUCESSO! ✍️🔒🎉")

if __name__ == '__main__':
    test_escrever_livro_auth()
