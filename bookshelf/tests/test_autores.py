import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, AUTORES_MOCADOS

def test_autores_page():
    print("Iniciando testes da rota /autores e dados dos autores...")
    with app.test_client() as client:
        # 1. Teste de status 200
        res = client.get('/autores')
        assert res.status_code == 200, f"Esperado 200, obtido {res.status_code}"
        html = res.get_data(as_text=True)
        assert "Galeria de Autores BookShelf" in html, "Título da Galeria de Autores não encontrado"
        print("✓ Rota /autores responde 200 com HTML correto.")

        # 2. Validação da presença dos autores da comunidade (própria autoria)
        autores_comunidade = [a for a in AUTORES_MOCADOS if a['tipo'] == 'comunidade']
        assert len(autores_comunidade) >= 8, f"Esperado ao menos 8 autores da comunidade, obtido {len(autores_comunidade)}"
        for a in autores_comunidade:
            assert a['nome'] in html, f"Autor da comunidade {a['nome']} não exibido no HTML"
            assert a['foto'], f"Autor {a['nome']} sem foto"
            assert a['bio_curta'] and a['bio_completa'], f"Autor {a['nome']} sem biografia"
            assert len(a['livros']) >= 1, f"Autor {a['nome']} sem livros publicados"
        print(f"✓ {len(autores_comunidade)} autores da comunidade (própria autoria) validados.")

        # 3. Validação dos autores clássicos e do acervo da plataforma
        autores_acervo = [a for a in AUTORES_MOCADOS if a['tipo'] == 'acervo']
        assert len(autores_acervo) >= 5, f"Esperado ao menos 5 autores do acervo, obtido {len(autores_acervo)}"
        for a in autores_acervo:
            assert a['nome'] in html, f"Autor do acervo {a['nome']} não exibido no HTML"
        print(f"✓ {len(autores_acervo)} mestres do acervo da plataforma validados.")

        # 4. Teste de filtro por tipo: comunidade
        res_com = client.get('/autores?tipo=comunidade')
        assert res_com.status_code == 200
        html_com = res_com.get_data(as_text=True)
        assert "Carlos Viana" in html_com
        assert "Machado de Assis" not in html_com
        print("✓ Filtro por tipo 'comunidade' funcionando perfeitamente.")

        # 5. Teste de filtro por tipo: acervo
        res_ac = client.get('/autores?tipo=acervo')
        assert res_ac.status_code == 200
        html_ac = res_ac.get_data(as_text=True)
        assert "Machado de Assis" in html_ac
        assert "Carlos Viana" not in html_ac
        print("✓ Filtro por tipo 'acervo' funcionando perfeitamente.")

        # 6. Teste de busca por nome de autor
        res_busca = client.get('/autores?q=Albuquerque')
        assert res_busca.status_code == 200
        html_busca = res_busca.get_data(as_text=True)
        assert "Beatriz Albuquerque" in html_busca
        print("✓ Busca por nome de autor funcionando.")

        # 7. Teste de busca por título de livro do autor
        res_busca_livro = client.get('/autores?q=Protocolo')
        assert res_busca_livro.status_code == 200
        html_busca_livro = res_busca_livro.get_data(as_text=True)
        assert "Carlos Viana" in html_busca_livro
        print("✓ Busca por título do livro publicado pelo autor funcionando.")

        # 8. Teste de link na navbar
        res_home = client.get('/')
        assert '/autores' in res_home.get_data(as_text=True), "Link /autores não encontrado na navbar da Home"
        print("✓ Link para /autores presente na navbar global.")

    print("\nTodos os 8 testes da Galeria de Autores passaram com 100% de sucesso! 🚀")

if __name__ == '__main__':
    test_autores_page()
