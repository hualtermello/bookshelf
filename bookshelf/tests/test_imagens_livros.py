import sys
import os
import html as html_module

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, SUAS_LITERATURAS_MOCADAS, LANCAMENTOS_AUTORAIS, AUTORES_MOCADOS

def test_imagens_livros():
    print("Iniciando testes de validação das imagens fictícias nos modelos de livros...")
    with app.test_client() as client:
        # 1. Teste da Home (/) - Suas literaturas e Novas recomendações
        res_home = client.get('/')
        assert res_home.status_code == 200, f"Esperado 200 para '/', obtido {res_home.status_code}"
        html_home = html_module.unescape(res_home.get_data(as_text=True))

        for l in SUAS_LITERATURAS_MOCADAS:
            assert l['titulo'] in html_home, f"Título '{l['titulo']}' não encontrado na home"
            assert l['capa'] in html_home, f"Capa fictícia de '{l['titulo']}' não renderizada na home"
        print(f"✓ Todos os {len(SUAS_LITERATURAS_MOCADAS)} livros do carrossel principal da Home possuem imagens fictícias renderizadas.")

        # 2. Teste de Lançamentos (/lancamentos)
        res_lanc = client.get('/lancamentos')
        assert res_lanc.status_code == 200, f"Esperado 200 para /lancamentos, obtido {res_lanc.status_code}"
        html_lanc = html_module.unescape(res_lanc.get_data(as_text=True))

        for l in LANCAMENTOS_AUTORAIS:
            assert l['titulo'] in html_lanc, f"Livro autoral '{l['titulo']}' ausente em lançamentos"
            assert l['capa_imagem'] in html_lanc, f"Capa fictícia da obra '{l['titulo']}' não encontrada no HTML de lançamentos"
        print(f"✓ Todas as {len(LANCAMENTOS_AUTORAIS)} obras autorais de lançamentos possuem imagens fictícias de capa.")

        # 3. Teste da Galeria de Autores (/autores)
        res_autores = client.get('/autores')
        assert res_autores.status_code == 200
        html_autores = html_module.unescape(res_autores.get_data(as_text=True))

        # Checa se mini-capas fictícias estão presentes nas estantes dos autores
        assert "images.unsplash.com" in html_autores, "Imagens fictícias de capas ausentes na estante de autores"
        for a in AUTORES_MOCADOS:
            for liv in a.get('livros', []):
                if liv.get('capa'):
                    assert liv['capa'] in html_autores, f"Mini-capa do livro '{liv['titulo']}' não encontrada na estante do autor {a['nome']}"
        print("✓ Mini-capas fictícias validadas nas prateleiras da Galeria de Autores.")

        # 4. Teste de Detalhes do Livro (/descricao)
        res_desc = client.get('/descricao')
        assert res_desc.status_code == 200
        html_desc = html_module.unescape(res_desc.get_data(as_text=True))
        assert "<img src=" in html_desc and "book-cover" in html_desc
        print("✓ Página de detalhes do livro (/descricao) exibindo elemento de capa com sucesso.")

        # 5. Validação do arquivo JS do Modelo para Gráfica
        caminho_js = os.path.join(os.path.dirname(__file__), '..', 'static', 'js', 'modelo_grafica.js')
        with open(caminho_js, 'r', encoding='utf-8') as f:
            conteudo_js = f.read()
        assert "btn-preset-capa" in conteudo_js, "Seletor de modelos de capas ilustradas ausente no JS do Modelo para Gráfica"
        assert "capaImagemUrl" in conteudo_js, "Propriedade capaImagemUrl ausente no JS do Modelo para Gráfica"
        print("✓ Presets e suporte a imagens fictícias no Modelo Oficial de Livro para Gráfica (A4) validados.")

    print("\nTODOS OS TESTES DE IMAGENS FICTÍCIAS DE LIVROS PASSARAM COM 100% DE SUCESSO! 📚🎨")

if __name__ == '__main__':
    test_imagens_livros()
