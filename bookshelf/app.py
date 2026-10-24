from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from flask_mysqldb import MySQL
import MySQLdb
from werkzeug.security import generate_password_hash, check_password_hash
import os
import time  # Adicionado para gerenciar o tempo de espera do MySQL
import re
import sqlite3

app = Flask(__name__)
app.secret_key = 'bookshelf_secret_key'

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
        print(f"Banco de dados local (SQLite) inicializado com sucesso em {SQLITE_DB_PATH}!")


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
        
    titulo = request.form.get('titulo')
    arquivo = request.files.get('arquivo')
    
    if titulo and arquivo and arquivo.filename != '':
        extensao = (os.path.splitext(arquivo.filename)[1].replace('.', '') or 'EPUB')[:10]
        
        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO livros (titulo, arquivo_epub, autor, id_categoria) VALUES (%s, %s, %s, %s)",
            (titulo, extensao.upper(), "Você (Autor Bookshelf)", None)
        )
        id_novo_livro = cursor.lastrowid
        
        cursor.execute(
            "INSERT INTO biblioteca_usuario (id_usuario, id_livro, progresso) VALUES (%s, %s, %s)",
            (session['usuario_id'], id_novo_livro, 100.00)
        )
        
        mysql.connection.commit()
        cursor.close()
        
        flash(f"Obra '{titulo}' cadastrada com sucesso no MySQL!", "success")
        return redirect(url_for('perfil'))
        
    flash("Erro ao enviar o arquivo do manuscrito.", "error")
    return redirect(url_for('perfil'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# GATILHO: Executa a criação das tabelas antes de ligar o servidor de fato
inicializar_banco()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
