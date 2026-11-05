import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app

def test_busca_dados_mocados_global():
    print("Iniciando testes de validação da barra de pesquisa com todos os dados mocados do site...")
    with app.test_client() as client:
        # 1. Busca por livro mocado de Suas Literaturas ("Dom Casmurro")
        res = client.get('/?q=Dom+Casmurro')
        assert res.status_code == 200, f"Status code {res.status_code} na busca de Dom Casmurro"
        html = res.get_data(as_text=True)
        assert "Dom Casmurro" in html, "Dom Casmurro não foi encontrado na busca"
        # O Cortiço não deve aparecer em suas literaturas quando filtramos por Dom Casmurro
        assert "O Cortiço" not in html, "O Cortiço não deveria aparecer ao buscar especificamente por Dom Casmurro"
        print("✓ Busca por 'Dom Casmurro' filtando dados mocados de 'suas literaturas' validada!")

        # 2. Busca por autor de livros mocados ("Machado")
        res_machado = client.get('/?q=Machado')
        assert res_machado.status_code == 200
        html_machado = res_machado.get_data(as_text=True)
        assert "Dom Casmurro" in html_machado, "Dom Casmurro ausente na busca por Machado"
        assert "Memórias Póstumas" in html_machado, "Memórias Póstumas ausente na busca por Machado"
        assert "Machado de Assis" in html_machado, "Autor Machado de Assis ausente nos resultados"
        print("✓ Busca por autor 'Machado' retornando livros e autor mocado validada!")

        # 3. Busca na Home por livro mocado da seção de Lançamentos ("Protocolo Ômega")
        res_lanc = client.get('/?q=Protocolo+Ômega')
        assert res_lanc.status_code == 200
        html_lanc = res_lanc.get_data(as_text=True)
        assert "O Protocolo Ômega: Linha de Fogo" in html_lanc, "Livro mocado 'O Protocolo Ômega: Linha de Fogo' não encontrado na busca da Home"
        print("✓ Busca na Home encontrando obras mocadas de lançamentos validada!")

        # 4. Busca na Home por autora mocada da comunidade ("Helena Bastos")
        res_autora = client.get('/?q=Helena+Bastos')
        assert res_autora.status_code == 200
        html_autora = res_autora.get_data(as_text=True)
        assert "Helena Bastos" in html_autora, "Autora mocada 'Helena Bastos' não exibida nos autores encontrados da Home"
        print("✓ Busca na Home encontrando autores mocados da comunidade validada!")

        # 5. Busca na Home por artigo mocado ("Inteligência Artificial")
        res_art = client.get('/?q=Inteligência+Artificial')
        assert res_art.status_code == 200
        html_art = res_art.get_data(as_text=True)
        assert "Por que a Inteligência Artificial nunca sentirá a dor da página em branco" in html_art, "Artigo mocado sobre Inteligência Artificial não exibido na busca da Home"
        print("✓ Busca na Home encontrando artigos e ensaios mocados validada!")

        # 6. Redirecionamento por categoria selecionada no dropdown
        res_cat_autores = client.get('/?q=Clarice&category=autores')
        assert res_cat_autores.status_code == 302, "Deveria redirecionar para /autores ao selecionar categoria autores"
        assert '/autores' in res_cat_autores.location, "Redirecionamento incorreto para categoria autores"

        res_cat_lanc = client.get('/?q=Romance&category=lancamentos')
        assert res_cat_lanc.status_code == 302, "Deveria redirecionar para /lancamentos"
        assert '/lancamentos' in res_cat_lanc.location

        res_cat_art = client.get('/?q=Escrita&category=artigos')
        assert res_cat_art.status_code == 302, "Deveria redirecionar para /artigos"
        assert '/artigos' in res_cat_art.location
        print("✓ Redirecionamentos inteligentes do dropdown de categorias validados!")

        # 7. Rota /biblioteca preservando a busca
        res_bib = client.get('/biblioteca?q=Iracema')
        assert res_bib.status_code == 302, "Rota /biblioteca deve redirecionar mantendo query de busca"
        assert 'q=Iracema' in res_bib.location
        print("✓ Rota /biblioteca unificada com a busca da Home!")

        # 8. Busca interna em /lancamentos, /autores e /artigos
        res_lanc_dir = client.get('/lancamentos?q=Inimiga')
        assert "O Casamento da Minha Inimiga" in res_lanc_dir.get_data(as_text=True)

        res_aut_dir = client.get('/autores?q=Alencar')
        assert "José de Alencar" in res_aut_dir.get_data(as_text=True)

        res_art_dir = client.get('/artigos?q=Lentidão')
        assert "O elogio à lentidão" in res_art_dir.get_data(as_text=True)
        print("✓ Buscas específicas de cada módulo validando dados mocados com sucesso!")

    print("\nTODOS OS TESTES DA BARRA DE PESQUISA COM DADOS MOCADOS PASSARAM COM 100% DE SUCESSO! 🔍📚✨")

if __name__ == '__main__':
    test_busca_dados_mocados_global()
