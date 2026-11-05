import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, ARTIGOS_MOCADOS

def test_artigos_section():
    print("Iniciando testes da seção editorial /artigos e leitor /artigo/<id>...")
    with app.test_client() as client:
        # 1. Teste de status 200 da página inicial de artigos
        res = client.get('/artigos')
        assert res.status_code == 200, f"Esperado 200, obtido {res.status_code}"
        html = res.get_data(as_text=True)
        assert "Ensaios, Críticas & Opinião dos Autores" in html, "Título da Seção de Artigos não encontrado"
        assert "Diferente do formato de livro" in html, "Texto de contraste editorial não encontrado"
        print("✓ Rota /artigos responde 200 com HTML e cabeçalho editorial corretos.")

        # 2. Validação da presença dos artigos mocados
        assert len(ARTIGOS_MOCADOS) >= 8, f"Esperado ao menos 8 artigos mocados, obtido {len(ARTIGOS_MOCADOS)}"
        for art in ARTIGOS_MOCADOS:
            assert art['titulo'] in html, f"Artigo '{art['titulo']}' não encontrado na listagem"
            assert art['autor_nome'] in html, f"Autor '{art['autor_nome']}' não encontrado na listagem"
        print(f"✓ Todos os {len(ARTIGOS_MOCADOS)} artigos mocados foram renderizados na listagem.")

        # 3. Teste do Leitor Editorial de Artigo (/artigo/1)
        res_art = client.get('/artigo/1')
        assert res_art.status_code == 200, f"Esperado 200 para /artigo/1, obtido {res_art.status_code}"
        html_art = res_art.get_data(as_text=True)
        assert "Por que a Inteligência Artificial nunca sentirá a dor da página em branco" in html_art
        assert "Eduardo Brandão" in html_art
        assert "min de leitura" in html_art
        assert "pull-quote" in html_art
        assert "Debate & Opiniões" in html_art
        print("✓ Rota /artigo/1 renderiza o leitor editorial contínuo com pull-quotes e bio do autor.")

        # 4. Teste de filtro por categoria
        res_cat = client.get('/artigos?categoria=tecnologia')
        assert res_cat.status_code == 200
        html_cat = res_cat.get_data(as_text=True)
        assert "Inteligência Artificial" in html_cat
        assert "Elogio à Lentidão" not in html_cat
        print("✓ Filtro por categoria 'tecnologia' validado com sucesso.")

        # 5. Teste de filtro por busca
        res_busca = client.get('/artigos?q=Machado')
        assert res_busca.status_code == 200
        html_busca = res_busca.get_data(as_text=True)
        assert "Da utilidade secreta das ilusões" in html_busca
        assert "Eduardo Brandão" not in html_busca
        print("✓ Busca por termo textual 'Machado' validada com sucesso.")

        # 6. Teste da API de curtidas (claps/likes)
        res_like = client.post('/api/artigo/1/curtir')
        assert res_like.status_code == 200
        data_like = json.loads(res_like.get_data(as_text=True))
        assert data_like.get('ok') is True
        assert 'curtidas' in data_like
        print(f"✓ Endpoint POST /api/artigo/1/curtir validado. Curtidas atuais: {data_like.get('curtidas')}")

        # 7. Teste da API de comentários
        with client.session_transaction() as sess:
            sess['nome'] = 'Testador BookShelf'
            sess['usuario_id'] = 999

        res_comentario = client.post('/api/artigo/1/comentar', 
            data=json.dumps({'texto': 'Excelente reflexão sobre os algoritmos!'}),
            content_type='application/json'
        )
        assert res_comentario.status_code == 200
        data_com = json.loads(res_comentario.get_data(as_text=True))
        assert data_com.get('ok') is True
        assert data_com.get('comentario', {}).get('autor') == 'Testador BookShelf'
        print("✓ Endpoint POST /api/artigo/1/comentar validado com sucesso.")

        # 8. Teste de presença do link /artigos no cabeçalho das páginas principais
        for rota in ['/', '/lancamentos', '/autores']:
            res_nav = client.get(rota)
            assert res_nav.status_code == 200
            assert 'href="/artigos"' in res_nav.get_data(as_text=True), f"Link de Artigos ausente na navbar de {rota}"
        print("✓ Link para /artigos validado na navegação global de /, /lancamentos e /autores.")

    print("\nTODOS OS TESTES DA SEÇÃO DE ARTIGOS PASSARAM COM SUCESSO!")

if __name__ == '__main__':
    test_artigos_section()
