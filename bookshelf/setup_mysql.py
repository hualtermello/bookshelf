import os
import sys
import json
import MySQLdb

def carregar_env():
    caminho_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.isfile(caminho_env):
        with open(caminho_env, 'r', encoding='utf-8') as f:
            for linha in f:
                linha = linha.strip()
                if linha and not linha.startswith('#') and '=' in linha:
                    k, v = linha.split('=', 1)
                    k, v = k.strip(), v.strip().strip("'\"")
                    if k not in os.environ:
                        os.environ[k] = v

def main():
    carregar_env()
    host = os.environ.get('MYSQL_HOST', 'localhost')
    port = int(os.environ.get('MYSQL_PORT', 3306))
    user = os.environ.get('MYSQL_USER', 'root')
    password = os.environ.get('MYSQL_PASSWORD', '12345')
    db_name = os.environ.get('MYSQL_DB', 'epub')

    print("=" * 65)
    print("  INICIALIZAÇÃO DO BANCO DE DADOS MYSQL - BOOKSHELF")
    print("=" * 65)
    print(f"Host:     {host}:{port}")
    print(f"Usuário:  {user}")
    print(f"Banco:    {db_name}")
    print("-" * 65)

    # 1. Conexão ao servidor MySQL
    try:
        conn = MySQLdb.connect(
            host=host,
            port=port,
            user=user,
            passwd=password,
            charset='utf8mb4'
        )
        print("[OK] Conexão com o servidor MySQL estabelecida com sucesso!")
    except Exception as e:
        print(f"[ERRO] Falha ao conectar ao servidor MySQL: {e}")
        sys.exit(1)

    cur = conn.cursor()

    # 2. Leitura do arquivo schema.sql
    caminho_schema = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')
    if not os.path.isfile(caminho_schema):
        print(f"[ERRO] Arquivo schema.sql não encontrado em: {caminho_schema}")
        sys.exit(1)

    with open(caminho_schema, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    # 3. Execução dos comandos do schema
    print("\nExecutando script schema.sql...")
    
    # Divide os comandos por ponto e vírgula ignorando comentários
    linhas = []
    for l in schema_sql.splitlines():
        l_trim = l.strip()
        if not l_trim.startswith('--') and not l_trim.startswith('/*'):
            linhas.append(l)
    
    comandos_brutos = "\n".join(linhas).split(';')
    comandos_executados = 0

    for cmd in comandos_brutos:
        cmd_clean = cmd.strip()
        if cmd_clean:
            try:
                cur.execute(cmd_clean)
                comandos_executados += 1
            except Exception as e:
                print(f"[AVISO] Erro no comando:\n{cmd_clean[:100]}...\nMotivo: {e}")

    conn.commit()
    print(f"[OK] {comandos_executados} instruções SQL executadas com sucesso!")

    # População inicial de autores se estiver vazio
    cur.execute(f"USE `{db_name}`;")
    try:
        cur.execute("ALTER TABLE lancamentos_autorais ADD COLUMN capa_imagem VARCHAR(500);")
        conn.commit()
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE livros ADD COLUMN capa_imagem VARCHAR(500);")
        conn.commit()
    except Exception:
        pass

    try:
        from app import LANCAMENTOS_AUTORAIS
        cur.execute("SELECT COUNT(*) FROM `lancamentos_autorais`;")
        if cur.fetchone()[0] == 0:
            for l in LANCAMENTOS_AUTORAIS:
                cur.execute("""
                    INSERT INTO lancamentos_autorais (
                        id_lancamento, titulo, subtitulo, autor, autor_cidade, autor_bio,
                        genero, genero_label, cor_tema, capa_imagem, ano, data_lancamento,
                        paginas, tempo_leitura, avaliacao, total_avaliacoes, formato,
                        sinopse, nota_autor, badges_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    l['id'], l['titulo'], l['subtitulo'], l['autor'], l['autor_cidade'], l['autor_bio'],
                    l['genero'], l['genero_label'], l['cor_tema'], l.get('capa_imagem'), l['ano'], l['data_lancamento'],
                    l['paginas'], l['tempo_leitura'], l['avaliacao'], l['total_avaliacoes'], l['formato'],
                    l['sinopse'], l['nota_autor'], json.dumps(l['badges'], ensure_ascii=False)
                ))
            conn.commit()
            print("[OK] Tabela 'lancamentos_autorais' populada com dados mocados!")
        else:
            for l in LANCAMENTOS_AUTORAIS:
                cur.execute("UPDATE lancamentos_autorais SET capa_imagem = %s WHERE id_lancamento = %s", (l.get('capa_imagem'), l['id']))
            conn.commit()
            print("[OK] Capas atualizadas na tabela 'lancamentos_autorais'!")
    except Exception as e:
        print("[AVISO] População/atualização de lancamentos_autorais:", e)

    try:
        from app import AUTORES_MOCADOS
        cur.execute("SELECT COUNT(*) FROM `autores`;")
        if cur.fetchone()[0] == 0:
            for a in AUTORES_MOCADOS:
                cur.execute("""
                    INSERT INTO autores (
                        id_autor, nome, tipo, tipo_badge, foto, origem,
                        bio_curta, bio_completa, generos_json, livros_json,
                        total_leitores, total_livros, citacao
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    a['id'], a['nome'], a['tipo'], a['tipo_badge'], a['foto'], a['origem'],
                    a['bio_curta'], a['bio_completa'], json.dumps(a['generos'], ensure_ascii=False),
                    json.dumps(a['livros'], ensure_ascii=False), a['total_leitores'], a['total_livros'], a['citacao']
                ))
            conn.commit()
            print("[OK] Tabela 'autores' populada com dados mocados!")
        else:
            for a in AUTORES_MOCADOS:
                cur.execute("UPDATE autores SET livros_json = %s WHERE id_autor = %s", (json.dumps(a['livros'], ensure_ascii=False), a['id']))
            conn.commit()
            print("[OK] Capas atualizadas na estante da tabela 'autores'!")
    except Exception as e:
        print("[AVISO] População de autores:", e)

    try:
        cur.execute("UPDATE livros SET capa_imagem = 'https://images.unsplash.com/photo-1516979187457-637abb4f9353?auto=format&fit=crop&w=600&q=80' WHERE LOWER(titulo) = '5minutos'")
        cur.execute("UPDATE livros SET capa_imagem = 'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=600&q=80' WHERE LOWER(titulo) LIKE '%dádiva%' OR LOWER(titulo) LIKE '%dadiva%'")
        conn.commit()
        print("[OK] Capas atualizadas na tabela 'livros'!")
    except Exception as e:
        print("[AVISO] Atualização de capas em livros:", e)

    # População inicial de artigos se estiver vazio
    try:
        from app import ARTIGOS_MOCADOS
        cur.execute("SELECT COUNT(*) FROM `artigos`;")
        if cur.fetchone()[0] == 0:
            for art in ARTIGOS_MOCADOS:
                cur.execute("""
                    INSERT INTO artigos (
                        id_artigo, titulo, subtitulo, autor_nome, autor_foto, autor_origem,
                        categoria, categoria_slug, tempo_leitura, data_publicacao,
                        resumo, conteudo_html, tags_json, curtidas, comentarios_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    art['id'], art['titulo'], art['subtitulo'], art['autor_nome'], art['autor_foto'], art['autor_origem'],
                    art['categoria'], art['categoria_slug'], art['tempo_leitura'], art['data_publicacao'],
                    art['resumo'], art['conteudo_html'], json.dumps(art['tags'], ensure_ascii=False),
                    art['curtidas'], json.dumps(art['comentarios'], ensure_ascii=False)
                ))
            conn.commit()
            print("[OK] Tabela 'artigos' populada com dados mocados!")
    except Exception as e:
        print("[AVISO] População de artigos:", e)

    # 4. Verificação das tabelas criadas no banco
    cur.execute(f"USE `{db_name}`;")
    cur.execute("SHOW TABLES;")
    tabelas = [row[0] for row in cur.fetchall()]
    
    print("\n" + "=" * 65)
    print("  TABELAS CRIADAS NO BANCO DE DADOS:")
    print("=" * 65)

    for t in sorted(tabelas):
        cur.execute(f"SELECT COUNT(*) FROM `{t}`;")
        qtd = cur.fetchone()[0]
        print(f"  • {t:<25} ({qtd} registros)")

    print("-" * 65)
    print("Banco de dados MySQL 'epub' totalmente configurado e pronto!")
    print("=" * 65)

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
