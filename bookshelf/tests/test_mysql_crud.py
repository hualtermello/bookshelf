import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, mysql

def test_mysql_crud():
    print("Iniciando testes de operações diretas no MySQL...")
    with app.app_context():
        # 1. Testa se estamos realmente conectados ao MySQL (e não ao SQLite)
        assert mysql.use_sqlite is False, "A aplicação não deveria estar em modo fallback SQLite!"
        print("✓ Conexão ativa com o banco MySQL confirmada (use_sqlite == False).")

        cursor = mysql.connection.cursor()

        # 2. Verifica tabelas no banco de dados MySQL
        cursor.execute("SHOW TABLES;")
        tabelas = [list(row.values())[0] if isinstance(row, dict) else row[0] for row in cursor.fetchall()]
        tabelas_esperadas = {'usuario', 'livros', 'biblioteca_usuario', 'modelo_grafica', 'lancamentos_autorais'}
        assert tabelas_esperadas.issubset(set(tabelas)), f"Tabelas ausentes: {tabelas_esperadas - set(tabelas)}"
        print(f"✓ Todas as 5 tabelas encontradas no MySQL: {tabelas}")

        # 3. Testa leitura da tabela lancamentos_autorais
        cursor.execute("SELECT COUNT(*) as total FROM lancamentos_autorais")
        row = cursor.fetchone()
        total_lancamentos = row['total'] if isinstance(row, dict) else row[0]
        assert total_lancamentos >= 8, f"Esperado ao menos 8 lançamentos, obtido {total_lancamentos}"
        print(f"✓ Tabela lancamentos_autorais populada com {total_lancamentos} registros.")

        # 4. Testa leitura da tabela livros
        cursor.execute("SELECT COUNT(*) as total FROM livros")
        row = cursor.fetchone()
        total_livros = row['total'] if isinstance(row, dict) else row[0]
        assert total_livros >= 2, f"Esperado ao menos 2 livros padrão, obtido {total_livros}"
        print(f"✓ Tabela livros possui {total_livros} obras cadastradas.")

        # 5. Testa inserção e remoção limpa de teste na tabela usuario
        email_teste = "teste_mysql_crud@bookshelf.com"
        cursor.execute("DELETE FROM usuario WHERE usuario = %s", (email_teste,))
        mysql.connection.commit()

        cursor.execute(
            "INSERT INTO usuario (usuario, senha_hash, cpf) VALUES (%s, %s, %s)",
            (email_teste, "hash_teste_123", "99988877766")
        )
        mysql.connection.commit()

        cursor.execute("SELECT id_usuario, usuario FROM usuario WHERE usuario = %s", (email_teste,))
        user_inserido = cursor.fetchone()
        assert user_inserido is not None, "Usuário de teste não foi encontrado após inserção"
        id_usuario_teste = user_inserido['id_usuario'] if isinstance(user_inserido, dict) else user_inserido[0]
        print(f"✓ Usuário de teste inserido com sucesso (ID: {id_usuario_teste}).")

        # Limpeza
        cursor.execute("DELETE FROM usuario WHERE id_usuario = %s", (id_usuario_teste,))
        mysql.connection.commit()
        print("✓ Limpeza de dados de teste concluída com sucesso.")

        cursor.close()

    print("\nTodos os testes de validação do MySQL foram concluídos com 100% de sucesso! 🚀")

if __name__ == '__main__':
    test_mysql_crud()
