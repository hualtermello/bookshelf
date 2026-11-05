import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app

def test_footer_structure_and_spacing():
    print("Iniciando testes de validação da estrutura e espaçamento do rodapé (Footer)...")
    with app.test_client() as client:
        rotas = ['/', '/lancamentos', '/autores', '/artigos']
        for r in rotas:
            res = client.get(r)
            assert res.status_code == 200, f"Rota {r} retornou status {res.status_code}"
            html = res.get_data(as_text=True)

            # 1. Verifica presença do footer global
            assert 'class="footer-global"' in html, f"Rodapé ausente na rota {r}"
            assert 'class="footer-global__container"' in html, f"Container do rodapé ausente na rota {r}"
            assert 'class="footer-global__bottom"' in html, f"Barra inferior do rodapé ausente na rota {r}"

            # 2. Verifica presença das 3 colunas principais
            assert "BookShelf" in html
            assert "Institucional" in html
            assert "Fale Conosco" in html
            assert "suporte@bookshelf.com" in html
            assert "0800 123 4567" in html

            # 3. Garante que 'Baixe nosso App' e 'Google Play' foram removidos
            assert "Baixe nosso App" not in html, f"'Baixe nosso App' ainda presente no HTML da rota {r}"
            assert "Google Play" not in html, f"'Google Play' ainda presente no HTML da rota {r}"
            assert "App Store" not in html, f"'App Store' ainda presente no HTML da rota {r}"

            print(f"✓ Rodapé da rota {r} validado: 3 colunas espaçadas e sem menção a aplicativos.")

        # Validação do CSS do Footer
        caminho_css = os.path.join(os.path.dirname(__file__), '..', 'static', 'estilogr.css')
        with open(caminho_css, 'r', encoding='utf-8') as f:
            css = f.read()

        assert "margin-top: 64px;" in css, "Espaçamento superior (margin-top) ausente no CSS do footer"
        assert "gap: 56px;" in css, "Espaçamento entre colunas (gap: 56px) ausente no CSS do footer"
        assert "footer-global__bottom" in css, "Barra inferior do rodapé ausente no CSS"
        print("✓ Regras de espaçamento e tipografia do rodapé validadas no CSS.")

    print("\nTODOS OS TESTES DO RODAPÉ PASSARAM COM 100% DE SUCESSO! 🦶✨")

if __name__ == '__main__':
    test_footer_structure_and_spacing()
