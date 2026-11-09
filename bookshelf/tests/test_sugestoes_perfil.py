import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, mysql, PERFIS_MOCADOS, gerar_sugestoes_personalizadas

def test_sugestoes_e_perfil_conectado_banco():
    print("=" * 70)
    print("  TESTES DO SISTEMA DE PERFIL E SUGESTÕES DE LIVROS (CONEXÃO BD & DADOS MOCADOS)")
    print("=" * 70)

    with app.test_client() as client:
        # Cria um usuário temporário no banco para os testes
        with app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT id_usuario FROM usuario WHERE usuario = 'teste_perfil_ai@bookshelf.com'")
            u_antigo = cursor.fetchone()
            if u_antigo:
                id_u = u_antigo['id_usuario'] if isinstance(u_antigo, dict) else u_antigo[0]
                cursor.execute("DELETE FROM biblioteca_usuario WHERE id_usuario = %s", (id_u,))
                cursor.execute("DELETE FROM usuario WHERE id_usuario = %s", (id_u,))
                mysql.connection.commit()

            cursor.execute("""
                INSERT INTO usuario (nome, usuario, senha_hash, cpf, bio, generos_favoritos, interesses, autores_favoritos)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                'Leitor Inicial de Teste',
                'teste_perfil_ai@bookshelf.com',
                'hash_teste_123',
                '111.222.333-44',
                'Explorando novos mundos literários e tecnologia.',
                'Ficção Científica, Tecnologia',
                'inteligência artificial, cibersegurança, robôs',
                'Carlos Viana, Eduardo Brandão'
            ))
            mysql.connection.commit()
            cursor.execute("SELECT id_usuario FROM usuario WHERE usuario = 'teste_perfil_ai@bookshelf.com'")
            novo_usr = cursor.fetchone()
            id_teste = novo_usr['id_usuario'] if isinstance(novo_usr, dict) else novo_usr[0]
            cursor.close()

        # Simula a sessão logada do usuário
        with client.session_transaction() as sess:
            sess['usuario_id'] = id_teste
            sess['username'] = 'teste_perfil_ai@bookshelf.com'
            sess['nome'] = 'Leitor Inicial de Teste'

        # 1. Teste da página de perfil carregando dados conectados do banco
        res = client.get('/perfil?tab=suggestions')
        assert res.status_code == 200, f"Status code {res.status_code} em /perfil"
        html = res.get_data(as_text=True)
        assert "Leitor Inicial de Teste" in html
        assert "Sugestões Personalizadas" in html
        assert "Motor de Recomendação Conectado ao MySQL" in html
        assert "Ficção Científica" in html
        print("✓ Perfil carregado com sucesso conectando dados do usuário no banco!")

        # 2. Teste das sugestões para o perfil de Ficção Científica & Tecnologia
        assert "O Protocolo Ômega: Linha de Fogo" in html, "Obra de ficção científica não sugerida para perfil de sci-fi"
        assert "Além do Algoritmo" in html, "Documentário de IA e tecnologia não sugerido"
        print("✓ Sugestões para Ficção Científica & Tecnologia calculadas com alta afinidade!")

        # 3. Teste de aplicação do perfil mocado de Clássicos Brasileiros (Prof. Carlos Eduardo Silveira)
        res_mocado_classicos = client.get('/perfil/carregar_mocado/classicos_brasileiros', follow_redirects=True)
        assert res_mocado_classicos.status_code == 200
        html_classicos = res_mocado_classicos.get_data(as_text=True)
        assert "Prof. Carlos Eduardo Silveira" in html_classicos
        assert "Clássicos" in html_classicos
        assert "Dom Casmurro" in html_classicos, "Dom Casmurro deve ser altamente sugerido para amante de clássicos"
        assert "Machado de Assis" in html_classicos
        print("✓ Aplicação do perfil mocado de Clássicos gravou no banco e recalculou sugestões para Machado de Assis!")

        # 4. Teste de aplicação do perfil mocado de Suspense & Terror Gótico (Mariana Valente)
        res_mocado_suspense = client.get('/perfil/carregar_mocado/suspense_gotico', follow_redirects=True)
        assert res_mocado_suspense.status_code == 200
        html_suspense = res_mocado_suspense.get_data(as_text=True)
        assert "Mariana Santos Valente" in html_suspense
        assert "A Dádiva do Lobo" in html_suspense, "A Dádiva do Lobo deve ser sugerida para fã de horror/vampiros"
        assert "Anne Rice" in html_suspense
        assert "Alvo em Movimento" in html_suspense
        print("✓ Aplicação do perfil mocado de Suspense & Terror gerou sugestões com Anne Rice e perseguição policial!")

        # 5. Teste de aplicação do perfil mocado de Romance & Sensibilidade (Beatriz Albuquerque)
        res_mocado_romance = client.get('/perfil/carregar_mocado/romance_afeto', follow_redirects=True)
        assert res_mocado_romance.status_code == 200
        html_romance = res_mocado_romance.get_data(as_text=True)
        assert "Beatriz Lins de Albuquerque" in html_romance
        assert "Cartas para o Amanhã" in html_romance
        assert "Sob a Luz das Estrelas de Outono" in html_romance
        print("✓ Aplicação do perfil mocado de Romance gerou sugestões românticas e epistolares!")

        # 6. Teste de salvamento de novas informações escritas no perfil via POST
        res_salvar = client.post('/perfil/salvar_preferencias', data={
            'nome': 'Clarice Leitora Criativa',
            'bio': 'Adoro comédias ácidas, sátiras urbanas e reflexões impagáveis sobre o caos da vida moderna.',
            'generos_favoritos': 'Comédia, Crônicas',
            'interesses': 'vida adulta, humor, reuniões, caos',
            'autores_favoritos': 'Tiago Fontes, Clarice Montenegro'
        }, follow_redirects=True)
        assert res_salvar.status_code == 200
        html_salvo = res_salvar.get_data(as_text=True)
        assert "Clarice Leitora Criativa" in html_salvo
        assert "Manual do Caos Diário" in html_salvo, "Manual do Caos Diário deve ser sugerido para quem escreveu sobre comédia/vida adulta"
        assert "O Casamento da Minha Inimiga" in html_salvo

        # Confirmação direta no banco de dados que os dados foram persistidos
        with app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT nome, bio, generos_favoritos FROM usuario WHERE id_usuario = %s", (id_teste,))
            db_row = cursor.fetchone()
            assert db_row['nome'] == 'Clarice Leitora Criativa'
            assert 'vida moderna' in db_row['bio']
            assert 'Comédia' in db_row['generos_favoritos']
            cursor.close()
        print("✓ Salvamento de informações customizadas escritas no perfil persistido no banco e com sugestões de comédia geradas!")

        # 7. Teste de adicionar livro sugerido à estante virtual do usuário
        res_add = client.post('/perfil/adicionar_estante/1', follow_redirects=True) # ID 1 = 5minutos
        assert res_add.status_code == 200
        with app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT 1 FROM biblioteca_usuario WHERE id_usuario = %s AND id_livro = 1", (id_teste,))
            assert cursor.fetchone() is not None, "Livro ID 1 não foi registrado em biblioteca_usuario"
            cursor.close()
        print("✓ Livro sugerido adicionado com sucesso à tabela biblioteca_usuario no banco de dados!")

        # 8. Teste do endpoint JSON de sugestões em tempo real (/api/sugestoes)
        res_api = client.post('/api/sugestoes', json={
            'bio': 'Gosto de romances clássicos de época no Rio de Janeiro antigo.',
            'generos_favoritos': 'Clássicos',
            'interesses': 'rio de janeiro, amor',
            'autores_favoritos': 'José de Alencar'
        })
        assert res_api.status_code == 200
        dados_api = res_api.get_json()
        assert dados_api['ok'] is True
        assert len(dados_api['sugestoes']) > 0
        titulos_api = [s['titulo'] for s in dados_api['sugestoes']]
        assert any("5minutos" in t or "Iracema" in t or "Dom Casmurro" in t for t in titulos_api)
        print("✓ API /api/sugestoes calculando sugestões dinâmicas com justificativas e afinidade!")

        # Limpeza do usuário de teste
        with app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute("DELETE FROM biblioteca_usuario WHERE id_usuario = %s", (id_teste,))
            cursor.execute("DELETE FROM usuario WHERE id_usuario = %s", (id_teste,))
            mysql.connection.commit()
            cursor.close()
            print("✓ Limpeza dos dados de teste realizada com sucesso.")

    print("\nTODOS OS TESTES DO PERFIL CONECTADO AO BANCO COM SUGESTÕES E DADOS MOCADOS PASSARAM COM 100% DE SUCESSO! 📚✨🎉")

if __name__ == '__main__':
    test_sugestoes_e_perfil_conectado_banco()
