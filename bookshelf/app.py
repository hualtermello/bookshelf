from flask import Flask, render_template, request, redirect, url_for, flash, session, g, send_from_directory, abort, jsonify
import xml.etree.ElementTree as ET
import posixpath
import base64
import mimetypes
from flask_mysqldb import MySQL
import MySQLdb
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import zipfile
import os
import time  # Adicionado para gerenciar o tempo de espera do MySQL
import re
import sqlite3

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'bookshelf_secret_key')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # limite de upload: 50 MB
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', 'epubs')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', 'localhost')
app.config['MYSQL_PORT'] = int(os.environ.get('MYSQL_PORT', 3306))
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', 'escola')
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB', 'epub')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bookshelf.db')


class SQLiteDictCursor:
    def __init__(self, conn):
        self._conn = conn
        self._cursor = conn.cursor()

    def execute(self, query, params=None):
        q = query.replace('%s', '?')
        if params is not None:
            return self._cursor.execute(q, params)
        return self._cursor.execute(q)

    def fetchone(self):
        row = self._cursor.fetchone()
        return dict(row) if row is not None else None

    def fetchall(self):
        return [dict(r) for r in self._cursor.fetchall()]

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    def close(self):
        self._cursor.close()


class SQLiteConnectionWrapper:
    def __init__(self, db_path):
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON;")

    def cursor(self):
        return SQLiteDictCursor(self._conn)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


class MySQLWithFallback(MySQL):
    def __init__(self, app=None):
        self.use_sqlite = False
        super().__init__(app)

    @property
    def connection(self):
        if not self.use_sqlite:
            try:
                conn = super().connection
                if conn is not None:
                    return conn
            except Exception:
                self.use_sqlite = True
        if 'sqlite_db' not in g:
            g.sqlite_db = SQLiteConnectionWrapper(SQLITE_DB_PATH)
        return g.sqlite_db


mysql = MySQLWithFallback(app)


@app.teardown_appcontext
def fechar_conexao_sqlite(exception):
    db = g.pop('sqlite_db', None)
    if db is not None:
        db.close()


# Função para criar as tabelas automaticamente se não existirem
def inicializar_banco():
    with app.app_context():
        max_tentativas = 5 if app.config['MYSQL_HOST'] != 'localhost' else 1
        # Tenta conectar ao banco até 5 vezes (esperando o MySQL ligar no Docker)
        for tentativa in range(max_tentativas):
            try:
                conn_init = MySQLdb.connect(
                    host=app.config['MYSQL_HOST'],
                    port=app.config['MYSQL_PORT'],
                    user=app.config['MYSQL_USER'],
                    passwd=app.config['MYSQL_PASSWORD']
                )
                cur_init = conn_init.cursor()
                cur_init.execute(f"CREATE DATABASE IF NOT EXISTS `{app.config['MYSQL_DB']}`;")
                conn_init.commit()
                cur_init.close()
                conn_init.close()

                cursor = mysql.connection.cursor()
                # Cria tabela usuario
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS usuario (
                        id_usuario INT AUTO_INCREMENT PRIMARY KEY,
                        usuario VARCHAR(255) NOT NULL UNIQUE,
                        senha_hash VARCHAR(255) NOT NULL,
                        cpf VARCHAR(14) NOT NULL UNIQUE
                    );
                """)
                # Cria tabela livros
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS livros (
                        id_livro INT AUTO_INCREMENT PRIMARY KEY,
                        titulo VARCHAR(255) NOT NULL,
                        autor VARCHAR(255),
                        arquivo_epub VARCHAR(10),
                        id_categoria INT
                    );
                """)
                # Cria tabela biblioteca_usuario
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS biblioteca_usuario (
                        id_usuario INT,
                        id_livro INT,
                        progresso DECIMAL(5,2) DEFAULT 0.00,
                        PRIMARY KEY (id_usuario, id_livro),
                        FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE,
                        FOREIGN KEY (id_livro) REFERENCES livros(id_livro) ON DELETE CASCADE
                    );
                """)
                mysql.connection.commit()
                cursor.close()
                garantir_epubs_padrao()
                print("Banco de dados verificado/inicializado com sucesso!")
                return # Sai da função se der certo
            except Exception as e:
                print(f"Tentativa {tentativa + 1}/{max_tentativas}: Aguardando o MySQL iniciar... ({e})")
                if tentativa + 1 < max_tentativas:
                    time.sleep(4) # Aguarda 4 segundos antes de tentar de novo

        # Fallback automático para SQLite local caso o MySQL não esteja disponível
        mysql.use_sqlite = True
        cursor = mysql.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuario (
                id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario VARCHAR(255) NOT NULL UNIQUE,
                senha_hash VARCHAR(255) NOT NULL,
                cpf VARCHAR(14) NOT NULL UNIQUE
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS livros (
                id_livro INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo VARCHAR(255) NOT NULL,
                autor VARCHAR(255),
                arquivo_epub VARCHAR(10),
                id_categoria INT
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS biblioteca_usuario (
                id_usuario INT,
                id_livro INT,
                progresso DECIMAL(5,2) DEFAULT 0.00,
                PRIMARY KEY (id_usuario, id_livro),
                FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE,
                FOREIGN KEY (id_livro) REFERENCES livros(id_livro) ON DELETE CASCADE
            );
        """)
        mysql.connection.commit()
        cursor.close()
        garantir_epubs_padrao()
        print(f"Banco de dados local (SQLite) inicializado com sucesso em {SQLITE_DB_PATH}!")


def garantir_epubs_padrao():
    import shutil
    raiz_projeto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    livros_padrao = [
        ('5minutos.epub', '5minutos', 'José de Alencar'),
        ('A Dadiva do Lobo - Anne Rice.epub', 'A Dádiva do Lobo', 'Anne Rice'),
    ]
    cursor = mysql.connection.cursor()
    for nome_arquivo, titulo, autor in livros_padrao:
        origem = os.path.join(raiz_projeto, nome_arquivo)
        if not os.path.isfile(origem):
            continue
        cursor.execute("SELECT id_livro FROM livros WHERE LOWER(titulo) = LOWER(%s)", (titulo,))
        existente = cursor.fetchone()
        if existente:
            id_livro = existente['id_livro']
        else:
            cursor.execute(
                "INSERT INTO livros (titulo, autor, arquivo_epub, id_categoria) VALUES (%s, %s, %s, %s)",
                (titulo, autor, 'EPUB', None)
            )
            id_livro = cursor.lastrowid
        destino = os.path.join(UPLOAD_FOLDER, f"{id_livro}.epub")
        if not os.path.isfile(destino):
            shutil.copyfile(origem, destino)
    mysql.connection.commit()
    cursor.close()


@app.route('/')
@app.route('/index')
@app.route('/home')
def index():
    busca = request.args.get('q', '') or request.args.get('search', '')
    cursor = mysql.connection.cursor()
    if busca:
        query = "SELECT id_livro as id, titulo, autor, arquivo_epub as formato, 'Upload' as tamanho FROM livros WHERE titulo LIKE %s OR autor LIKE %s"
        cursor.execute(query, (f"%{busca}%", f"%{busca}%"))
    else:
        query = "SELECT id_livro as id, titulo, autor, arquivo_epub as formato, 'Upload' as tamanho FROM livros"
        cursor.execute(query)
    livros_filtrados = cursor.fetchall()
    cursor.close()
    return render_template('home.html', livros=livros_filtrados, busca=busca)


@app.route('/descricao')
@app.route('/livro/<int:id_livro>')
def descricao_livro(id_livro=None):
    livro = None
    if id_livro is not None:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id_livro as id, titulo, autor, arquivo_epub as formato FROM livros WHERE id_livro = %s", (id_livro,))
        livro = cursor.fetchone()
        cursor.close()
    return render_template('descricaolv.html', livro=livro)


@app.route('/ler/<int:id_livro>')
def ler_livro(id_livro):
    cursor = mysql.connection.cursor()
    cursor.execute(
        "SELECT id_livro as id, titulo, autor, arquivo_epub as formato FROM livros WHERE id_livro = %s",
        (id_livro,)
    )
    livro = cursor.fetchone()
    cursor.close()
    if not livro:
        flash("Livro não encontrado.", "error")
        return redirect(url_for('index'))
    caminho_epub = os.path.join(UPLOAD_FOLDER, f"{id_livro}.epub")
    livro['tem_epub'] = os.path.isfile(caminho_epub)
    return render_template('leitura.html', livro=livro)


@app.route('/epub/<int:id_livro>.epub')
def servir_epub(id_livro):
    # O nome do arquivo é gerado pelo ID do banco, nunca pelo nome enviado pelo usuário.
    nome_arquivo = f'{id_livro}.epub'
    if not os.path.isfile(os.path.join(UPLOAD_FOLDER, nome_arquivo)):
        abort(404, description='Arquivo EPUB não encontrado para esta obra.')
    return send_from_directory(UPLOAD_FOLDER, nome_arquivo, mimetype='application/epub+zip', as_attachment=False)


def extrair_capitulos_epub(caminho_epub):
    capitulos = []
    with zipfile.ZipFile(caminho_epub, 'r') as zf:
        nomes_zip = {n.replace('\\', '/'): n for n in zf.namelist()}
        opf_path = None

        if 'META-INF/container.xml' in nomes_zip:
            try:
                container_xml = zf.read(nomes_zip['META-INF/container.xml'])
                root = ET.fromstring(container_xml)
                for elem in root.iter():
                    if elem.tag.endswith('rootfile') and elem.attrib.get('full-path'):
                        opf_path = elem.attrib['full-path'].replace('\\', '/')
                        break
            except Exception:
                pass

        if not opf_path or opf_path not in nomes_zip:
            for nome in nomes_zip:
                if nome.lower().endswith('.opf'):
                    opf_path = nome
                    break

        arquivos_capitulos = []
        titulos_toc = {}

        if opf_path and opf_path in nomes_zip:
            opf_dir = posixpath.dirname(opf_path)
            try:
                opf_root = ET.fromstring(zf.read(nomes_zip[opf_path]))
                manifest = {}
                ncx_href = None
                nav_href = None

                for item in opf_root.iter():
                    if item.tag.endswith('item'):
                        item_id = item.attrib.get('id')
                        href = item.attrib.get('href', '')
                        media_type = item.attrib.get('media-type', '')
                        props = item.attrib.get('properties', '')
                        if item_id and href:
                            resolved = posixpath.normpath(posixpath.join(opf_dir, href)) if opf_dir else posixpath.normpath(href)
                            manifest[item_id] = (resolved, media_type, href)
                            if 'nav' in props.split():
                                nav_href = resolved
                            elif media_type == 'application/x-dtbncx+xml' or href.lower().endswith('.ncx'):
                                ncx_href = resolved

                if ncx_href and ncx_href in nomes_zip:
                    try:
                        ncx_dir = posixpath.dirname(ncx_href)
                        ncx_root = ET.fromstring(zf.read(nomes_zip[ncx_href]))
                        for navpoint in ncx_root.iter():
                            if navpoint.tag.endswith('navPoint'):
                                label_text = None
                                content_src = None
                                for child in navpoint.iter():
                                    if child.tag.endswith('text') and child.text and not label_text:
                                        label_text = child.text.strip()
                                    elif child.tag.endswith('content') and child.attrib.get('src') and not content_src:
                                        src_clean = child.attrib['src'].split('#')[0]
                                        content_src = posixpath.normpath(posixpath.join(ncx_dir, src_clean)) if ncx_dir else posixpath.normpath(src_clean)
                                if label_text and content_src and content_src not in titulos_toc:
                                    titulos_toc[content_src] = label_text
                    except Exception:
                        pass

                for itemref in opf_root.iter():
                    if itemref.tag.endswith('itemref'):
                        idref = itemref.attrib.get('idref')
                        if idref in manifest:
                            resolved, media_type, _ = manifest[idref]
                            if resolved in nomes_zip and (
                                'html' in media_type.lower() or resolved.lower().endswith(('.xhtml', '.html', '.htm'))
                            ):
                                arquivos_capitulos.append(resolved)
            except Exception:
                pass

        if not arquivos_capitulos:
            arquivos_capitulos = sorted(
                n for n in nomes_zip
                if n.lower().endswith(('.xhtml', '.html', '.htm')) and not posixpath.basename(n).lower().startswith('nav')
            )

        for idx, cap_path in enumerate(arquivos_capitulos):
            raw_bytes = zf.read(nomes_zip[cap_path])
            try:
                html_str = raw_bytes.decode('utf-8')
            except UnicodeDecodeError:
                html_str = raw_bytes.decode('latin-1', errors='replace')

            cap_dir = posixpath.dirname(cap_path)

            def substituir_img(match):
                prefixo, aspas, src = match.group(1), match.group(2), match.group(3)
                if src.startswith(('data:', 'http://', 'https://')):
                    return match.group(0)
                src_limpo = src.split('#')[0].split('?')[0]
                img_path = posixpath.normpath(posixpath.join(cap_dir, src_limpo)) if cap_dir else posixpath.normpath(src_limpo)
                if img_path in nomes_zip:
                    mime, _ = mimetypes.guess_type(img_path)
                    mime = mime or 'image/jpeg'
                    b64 = base64.b64encode(zf.read(nomes_zip[img_path])).decode('ascii')
                    return f'{prefixo}{aspas}data:{mime};base64,{b64}{aspas}'
                return match.group(0)

            html_str = re.sub(r'(<img\b[^>]*?\bsrc=)([\'"])(.*?)\2', substituir_img, html_str, flags=re.IGNORECASE)

            body_match = re.search(r'<body[^>]*>(.*?)</body>', html_str, flags=re.IGNORECASE | re.DOTALL)
            conteudo = body_match.group(1) if body_match else html_str
            conteudo = re.sub(r'<script\b[^>]*>.*?</script>', '', conteudo, flags=re.IGNORECASE | re.DOTALL)
            conteudo = re.sub(r'<style\b[^>]*>.*?</style>', '', conteudo, flags=re.IGNORECASE | re.DOTALL)

            texto_limpo = re.sub(r'<[^>]+>', '', conteudo).strip()
            if not texto_limpo and '<img' not in conteudo.lower() and '<svg' not in conteudo.lower():
                continue

            titulo_cap = titulos_toc.get(cap_path)
            if not titulo_cap:
                h_match = re.search(r'<h[1-3][^>]*>(.*?)</h[1-3]>', conteudo, flags=re.IGNORECASE | re.DOTALL)
                if h_match:
                    titulo_cap = re.sub(r'<[^>]+>', '', h_match.group(1)).strip()
            if not titulo_cap:
                t_match = re.search(r'<title[^>]*>(.*?)</title>', html_str, flags=re.IGNORECASE | re.DOTALL)
                if t_match:
                    titulo_cap = re.sub(r'<[^>]+>', '', t_match.group(1)).strip()
            if not titulo_cap:
                titulo_cap = f'Capítulo {len(capitulos) + 1}'

            capitulos.append({
                'titulo': titulo_cap[:90],
                'html': conteudo.strip()
            })

    return capitulos


@app.route('/api/epub/<int:id_livro>/capitulos')
def capitulos_epub(id_livro):
    caminho_epub = os.path.join(UPLOAD_FOLDER, f'{id_livro}.epub')
    if not os.path.isfile(caminho_epub):
        abort(404, description='Arquivo EPUB não encontrado.')
    try:
        capitulos = extrair_capitulos_epub(caminho_epub)
        return jsonify({'id_livro': id_livro, 'capitulos': capitulos})
    except Exception as e:
        return jsonify({'erro': str(e), 'capitulos': []}), 500


@app.route('/api/livro/<int:id_livro>/progresso', methods=['POST'])
def salvar_progresso_livro(id_livro):
    if 'usuario_id' not in session:
        return jsonify({'ok': False}), 200
    dados = request.get_json(silent=True) or {}
    try:
        progresso = max(0.0, min(100.0, float(dados.get('progresso', 0))))
    except (TypeError, ValueError):
        progresso = 0.0
    cursor = mysql.connection.cursor()
    cursor.execute(
        "SELECT 1 FROM biblioteca_usuario WHERE id_usuario = %s AND id_livro = %s",
        (session['usuario_id'], id_livro)
    )
    if cursor.fetchone():
        cursor.execute(
            "UPDATE biblioteca_usuario SET progresso = %s WHERE id_usuario = %s AND id_livro = %s",
            (progresso, session['usuario_id'], id_livro)
        )
    else:
        cursor.execute(
            "INSERT INTO biblioteca_usuario (id_usuario, id_livro, progresso) VALUES (%s, %s, %s)",
            (session['usuario_id'], id_livro, progresso)
        )
    mysql.connection.commit()
    cursor.close()
    return jsonify({'ok': True, 'progresso': progresso})


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario_input = request.form.get('email') 
        senha = request.form.get('senha')
        
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM usuario WHERE usuario = %s", (usuario_input,))
        user = cursor.fetchone()
        cursor.close()
        
        if user and check_password_hash(user['senha_hash'], senha):
            session['usuario_id'] = user['id_usuario']
            session['username'] = user['usuario']
            return redirect(url_for('perfil'))
        else:
            flash("Usuário ou senha incorretos.", "error")
            
    return render_template('cadastro_login.html')


@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email') 
        senha = request.form.get('senha')
        confirma_senha = request.form.get('confirmaSenha')
        cpf = request.form.get('cpf')
        
        # 1. Validação de campos vazios
        if not nome or not email or not senha or not cpf:
            flash("Todos os campos são obrigatórios.", "error")
            return render_template('cadastro_login.html')

        if confirma_senha is not None and senha != confirma_senha:
            flash("As senhas informadas não coincidem.", "error")
            return render_template('cadastro_login.html')
            
        # 2. Validação do padrão do CPF (Permite 11122233344 ou 111.222.333-44)
        cpf_limpo = re.sub(r'\D', '', cpf)  # Remove pontos e traços para testar
        if len(cpf_limpo) != 11:
            flash("O CPF deve conter exatamente 11 dígitos numéricos.", "error")
            return render_template('cadastro_login.html')
            
        # 3. Validação do padrão da Senha (Mínimo 8 caracteres, pelo menos 1 letra e 1 número)
        if len(senha) < 8 or not re.search(r"[a-zA-Z]", senha) or not re.search(r"[0-9]", senha):
            flash("A senha deve ter no mínimo 8 caracteres, incluindo letras e números.", "error")
            return render_template('cadastro_login.html')
        
        senha_hash = generate_password_hash(senha)
        
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id_usuario FROM usuario WHERE usuario = %s OR cpf = %s", (email, cpf))
        existente = cursor.fetchone()
        
        if existente:
            flash("Nome de usuário (E-mail) ou CPF já cadastrado.", "error")
            cursor.close()
        else:
            cursor.execute(
                "INSERT INTO usuario (usuario, senha_hash, cpf) VALUES (%s, %s, %s)",
                (email, senha_hash, cpf)
            )
            mysql.connection.commit()
            cursor.close()
            
            flash("Cadastro realizado com sucesso!", "success")
            return redirect(url_for('login'))
            
    return render_template('cadastro_login.html')


@app.route('/biblioteca')
def biblioteca():
    busca = request.args.get('q', '') or request.args.get('search', '')
    cursor = mysql.connection.cursor()
    
    if busca:
        query = "SELECT id_livro as id, titulo, autor, arquivo_epub as formato, 'Upload' as tamanho FROM livros WHERE titulo LIKE %s OR autor LIKE %s"
        cursor.execute(query, (f"%{busca}%", f"%{busca}%"))
    else:
        query = "SELECT id_livro as id, titulo, autor, arquivo_epub as formato, 'Upload' as tamanho FROM livros"
        cursor.execute(query)
        
    livros_filtrados = cursor.fetchall()
    cursor.close()
    
    return render_template('home.html', livros=livros_filtrados, busca=busca)

@app.route('/perfil')
def perfil():
    if 'usuario_id' not in session:
        flash("Por favor, faça o login primeiro.", "error")
        return redirect(url_for('login'))
        
    busca = request.args.get('q', '') or request.args.get('search', '')
    id_usuario = session['usuario_id']
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT usuario, cpf FROM usuario WHERE id_usuario = %s", (id_usuario,))
    db_user = cursor.fetchone()
    
    usuario_atual = {
        "nome": db_user['usuario'] if db_user else "Escritor",
        "username": db_user['usuario'] if db_user else "anonimo",
        "cpf": db_user['cpf'] if db_user else "",
        "bio": "Membro da comunidade Bookshelf conectado ao MySQL."
    }
    
    if busca:
        query = """
            SELECT l.id_livro as id, l.titulo, l.autor, l.arquivo_epub as formato, bu.progresso 
            FROM biblioteca_usuario bu
            JOIN livros l ON bu.id_livro = l.id_livro
            WHERE bu.id_usuario = %s AND (l.titulo LIKE %s OR l.autor LIKE %s)
        """
        cursor.execute(query, (id_usuario, f"%{busca}%", f"%{busca}%"))
    else:
        query = """
            SELECT l.id_livro as id, l.titulo, l.autor, l.arquivo_epub as formato, bu.progresso 
            FROM biblioteca_usuario bu
            JOIN livros l ON bu.id_livro = l.id_livro
            WHERE bu.id_usuario = %s
        """
        cursor.execute(query, (id_usuario,))
        
    livros_prateleira = cursor.fetchall()
    cursor.close()

    rascunhos_estaticos = [
        {
            "id": 1,
            "titulo": "Crônicas de Bordeaux: O Início",
            "updated_at": "14/09/2026",
            "previa": "O sol se punha atrás das colinas avermelhadas..."
        }
    ]

    return render_template(
        'usuario.html', 
        usuario=usuario_atual, 
        livros_prateleira=livros_prateleira,
        rascunhos=rascunhos_estaticos,
        publicados=[],
        busca=busca
    )

@app.route('/perfil/publicar', methods=['POST'])
def publicar_livro():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    titulo = (request.form.get('titulo') or '').strip()
    arquivo = request.files.get('arquivo')

    if not titulo or not arquivo or not arquivo.filename:
        flash("Informe o título e selecione um arquivo EPUB.", "error")
        return redirect(url_for('perfil'))

    nome_seguro = secure_filename(arquivo.filename)
    if not nome_seguro.lower().endswith('.epub'):
        flash("Para disponibilizar a leitura online, envie um arquivo .epub.", "error")
        return redirect(url_for('perfil'))

    # Um EPUB é um ZIP com os arquivos de navegação e conteúdo do livro.
    import tempfile
    caminho_temporario = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False, dir=UPLOAD_FOLDER) as temporario:
            caminho_temporario = temporario.name
            arquivo.save(temporario)

        if not zipfile.is_zipfile(caminho_temporario):
            raise ValueError('O arquivo selecionado não é um EPUB válido.')
        with zipfile.ZipFile(caminho_temporario) as epub:
            nomes = set(epub.namelist())
            if not any(n.replace('\\', '/').lower().endswith(('container.xml', '.opf', '.xhtml', '.html', '.htm')) for n in nomes):
                raise ValueError('O EPUB está incompleto ou inválido.')

        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO livros (titulo, arquivo_epub, autor, id_categoria) VALUES (%s, %s, %s, %s)",
            (titulo, 'EPUB', "Você (Autor Bookshelf)", None)
        )
        id_novo_livro = cursor.lastrowid
        destino = os.path.join(UPLOAD_FOLDER, f'{id_novo_livro}.epub')
        os.replace(caminho_temporario, destino)
        caminho_temporario = None

        cursor.execute(
            "INSERT INTO biblioteca_usuario (id_usuario, id_livro, progresso) VALUES (%s, %s, %s)",
            (session['usuario_id'], id_novo_livro, 0.00)
        )
        mysql.connection.commit()
        cursor.close()
        flash(f"Obra '{titulo}' publicada e pronta para leitura!", "success")
        return redirect(url_for('perfil'))
    except (ValueError, zipfile.BadZipFile) as erro:
        flash(str(erro), "error")
        return redirect(url_for('perfil'))
    except Exception:
        flash("Não foi possível salvar a obra. Tente novamente.", "error")
        return redirect(url_for('perfil'))
    finally:
        if caminho_temporario and os.path.exists(caminho_temporario):
            os.remove(caminho_temporario)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# GATILHO: Executa a criação das tabelas antes de ligar o servidor de fato
inicializar_banco()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
