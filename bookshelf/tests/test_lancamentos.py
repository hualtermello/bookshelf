import sys
import os

# Adiciona o diretório do bookshelf ao path de importação
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, LANCAMENTOS_AUTORAIS

def test_lancamentos_route():
    print("Iniciando testes da rota /lancamentos...")
    with app.test_client() as client:
        # 1. Teste de status 200 na página de lançamentos
        res = client.get('/lancamentos')
        assert res.status_code == 200, f"Esperado 200, obtido {res.status_code}"
        html = res.get_data(as_text=True)
        assert "Lançamentos de Própria Autoria" in html, "Título principal não encontrado"
        assert "Vitrine Oficial de Obras Autorais" in html, "Badge hero não encontrado"
        print("✓ Rota /lancamentos responde 200 com HTML correto.")

        # 2. Teste de presença dos 4 gêneros obrigatórios
        generos_esperados = {'acao', 'romance', 'comedia', 'documentario'}
        generos_presentes = {livro['genero'] for livro in LANCAMENTOS_AUTORAIS}
        assert generos_esperados.issubset(generos_presentes), f"Faltam gêneros: {generos_esperados - generos_presentes}"
        print(f"✓ Todos os 4 gêneros solicitados estão presentes: {generos_presentes}")

        # 3. Teste de dados de autoria própria
        for livro in LANCAMENTOS_AUTORAIS:
            assert livro['autor'], f"Livro {livro['id']} sem autor"
            assert livro['nota_autor'], f"Livro {livro['id']} sem nota de própria autoria"
            assert livro['sinopse'], f"Livro {livro['id']} sem sinopse"
            assert livro['titulo'], f"Livro {livro['id']} sem título"
        print("✓ Todos os registros mocados possuem autor, nota de autoria, sinopse e título.")

        # 4. Teste de filtro por gênero: Ação
        res_acao = client.get('/lancamentos?genero=acao')
        assert res_acao.status_code == 200
        html_acao = res_acao.get_data(as_text=True)
        assert "O Protocolo Ômega" in html_acao
        assert "Cartas para o Amanhã" not in html_acao
        print("✓ Filtro de gênero 'acao' funcionando corretamente.")

        # 5. Teste de filtro por gênero: Romance
        res_romance = client.get('/lancamentos?genero=romance')
        assert res_romance.status_code == 200
        html_romance = res_romance.get_data(as_text=True)
        assert "Cartas para o Amanhã" in html_romance
        assert "O Protocolo Ômega" not in html_romance
        print("✓ Filtro de gênero 'romance' funcionando corretamente.")

        # 6. Teste de filtro por gênero: Comédia
        res_comedia = client.get('/lancamentos?genero=comedia')
        assert res_comedia.status_code == 200
        html_comedia = res_comedia.get_data(as_text=True)
        assert "Manual do Caos Diário" in html_comedia
        assert "Vozes do Sertão" not in html_comedia
        print("✓ Filtro de gênero 'comedia' funcionando corretamente.")

        # 7. Teste de filtro por gênero: Documentários
        res_doc = client.get('/lancamentos?genero=documentario')
        assert res_doc.status_code == 200
        html_doc = res_doc.get_data(as_text=True)
        assert "Vozes do Sertão" in html_doc
        assert "Além do Algoritmo" in html_doc
        assert "Manual do Caos Diário" not in html_doc
        print("✓ Filtro de gênero 'documentario' funcionando corretamente.")

        # 8. Teste de busca textual
        res_busca = client.get('/lancamentos?q=Carlos')
        assert res_busca.status_code == 200
        html_busca = res_busca.get_data(as_text=True)
        assert "Carlos Viana" in html_busca
        print("✓ Busca por autor funcionando corretamente.")

        # 9. Teste do link no navbar da home
        res_home = client.get('/')
        assert res_home.status_code == 200
        assert '/lancamentos' in res_home.get_data(as_text=True), "Link /lancamentos não encontrado na navbar da Home"
        print("✓ Link da navbar apontando para /lancamentos validado com sucesso.")

    print("\nTodos os 9 testes passaram com sucesso! 🎉")

if __name__ == '__main__':
    test_lancamentos_route()
