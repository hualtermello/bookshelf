import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app

def test_book_card_actions_and_reading_time():
    print("Iniciando testes de validação das ações dos livros (Like, Favorito, Relógio com Tempo Lido)...")
    with app.test_client() as client:
        # 1. Testar Home Page
        res = client.get('/')
        assert res.status_code == 200, f"Rota / retornou status {res.status_code}"
        html = res.get_data(as_text=True)

        # Validação do Coração de Like
        assert 'book-card__action-btn--like' in html, "Botão de Like (coração) ausente nos cards de livros da Home"
        assert 'title="Curtir (Like)"' in html or 'title="Curtido! ❤️"' in html, "Tooltip de Like ausente"

        # Validação do Coração de Favoritar
        assert 'book-card__action-btn--fav' in html, "Botão de Favoritar (coração favorito) ausente nos cards de livros da Home"
        assert 'title="Favoritar este livro"' in html or 'title="Salvo nos favoritos! ⭐"' in html, "Tooltip de Favoritar ausente"

        # Validação do Relógio com Tempo Lido
        assert 'book-card__reading-time' in html, "Relógio com tempo de leitura ausente nos cards de livros da Home"
        assert 'book-card__icon-clock' in html, "Ícone do relógio ausente nos cards de livros da Home"
        assert '2h 45m' in html, "Tempo de leitura de 'As Crônicas do Horizonte Vermelho' não exibido"
        assert '1h 50m' in html, "Tempo de leitura de 'Dom Casmurro' não exibido"
        print("✓ Home: Coração de Like, Coração de Favorito e Relógio de tempo lido validados com sucesso!")

        # 2. Testar Perfil do Usuário
        with client.session_transaction() as sess:
            sess['usuario_id'] = 1
            sess['nome'] = 'Leitor Teste'
            sess['username'] = 'leitor@bookshelf.com'

        res_perfil = client.get('/perfil')
        assert res_perfil.status_code == 200, f"Rota /perfil retornou status {res_perfil.status_code}"
        html_perfil = res_perfil.get_data(as_text=True)

        assert 'book-card__action-btn--like' in html_perfil, "Botão de Like ausente nos cards do Perfil"
        assert 'book-card__action-btn--fav' in html_perfil, "Botão de Favorito ausente nos cards do Perfil"
        assert 'book-card__reading-time' in html_perfil, "Relógio com tempo de leitura ausente nos cards do Perfil"
        print("✓ Perfil: Ações dos cards validadas na estante do usuário!")

        # 3. Validação do CSS
        caminho_css = os.path.join(os.path.dirname(__file__), '..', 'static', 'estilogr.css')
        with open(caminho_css, 'r', encoding='utf-8') as f:
            css = f.read()

        assert '.book-card__action-btn--like' in css, "Classe .book-card__action-btn--like ausente no CSS"
        assert '.book-card__action-btn--fav' in css, "Classe .book-card__action-btn--fav ausente no CSS"
        assert '.book-card__reading-time' in css, "Classe .book-card__reading-time ausente no CSS"
        assert 'heartPulse' in css, "Keyframe heartPulse de like ausente no CSS"
        assert 'favGlow' in css, "Keyframe favGlow de favorito ausente no CSS"
        print("✓ CSS: Efeitos visuais, animações de like/favorito e relógio validados no arquivo estilogr.css!")

        # 4. Validação do JS
        caminho_js = os.path.join(os.path.dirname(__file__), '..', 'static', 'js', 'homejs.js')
        with open(caminho_js, 'r', encoding='utf-8') as f:
            js = f.read()

        assert 'toggleBookLike' in js, "Função toggleBookLike ausente em homejs.js"
        assert 'toggleBookFav' in js, "Função toggleBookFav ausente em homejs.js"
        assert 'mostrarTempoLeitura' in js, "Função mostrarTempoLeitura ausente em homejs.js"
        print("✓ JS: Interatividade do Like, Favorito e Toast do Relógio validadas em homejs.js!")

    print("\nTODOS OS TESTES DOS CARDS DE LIVROS PASSARAM COM 100% DE SUCESSO! 📚❤️⭐⏱️")

if __name__ == '__main__':
    test_book_card_actions_and_reading_time()
