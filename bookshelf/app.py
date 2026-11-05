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
import re
import json
import sqlite3

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

carregar_env()

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

    def teardown(self, exception):
        try:
            super().teardown(exception)
        except Exception:
            pass

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
                    nome VARCHAR(255),
                    usuario VARCHAR(255) NOT NULL UNIQUE,
                    senha_hash VARCHAR(255) NOT NULL,
                    cpf VARCHAR(14) NOT NULL UNIQUE
                );
            """)
            try:
                cursor.execute("ALTER TABLE usuario ADD COLUMN nome VARCHAR(255) AFTER id_usuario;")
                mysql.connection.commit()
            except Exception:
                pass
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
            # Cria tabela modelo_grafica para salvar o livro página por página
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS modelo_grafica (
                    id_modelo INT AUTO_INCREMENT PRIMARY KEY,
                    id_usuario INT UNIQUE,
                    titulo VARCHAR(255),
                    autor VARCHAR(255),
                    dados_json LONGTEXT,
                    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE
                );
            """)
            # Cria tabela lancamentos_autorais
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lancamentos_autorais (
                    id_lancamento INT AUTO_INCREMENT PRIMARY KEY,
                    titulo VARCHAR(255) NOT NULL,
                    subtitulo VARCHAR(255),
                    autor VARCHAR(255) NOT NULL,
                    autor_cidade VARCHAR(100),
                    autor_bio TEXT,
                    genero VARCHAR(50) NOT NULL,
                    genero_label VARCHAR(50) NOT NULL,
                    cor_tema VARCHAR(20) DEFAULT '#5E0B15',
                    ano INT DEFAULT 2026,
                    data_lancamento VARCHAR(20),
                    paginas INT DEFAULT 200,
                    tempo_leitura VARCHAR(50),
                    avaliacao DECIMAL(3,1) DEFAULT 5.0,
                    total_avaliacoes INT DEFAULT 0,
                    formato VARCHAR(50) DEFAULT 'EPUB Digital',
                    sinopse TEXT,
                    nota_autor TEXT,
                    badges_json TEXT,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # Cria tabela autores
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS autores (
                    id_autor INT AUTO_INCREMENT PRIMARY KEY,
                    nome VARCHAR(255) NOT NULL,
                    tipo VARCHAR(50) NOT NULL,
                    tipo_badge VARCHAR(100) NOT NULL,
                    foto VARCHAR(500),
                    origem VARCHAR(100),
                    bio_curta TEXT,
                    bio_completa LONGTEXT,
                    generos_json TEXT,
                    livros_json LONGTEXT,
                    total_leitores VARCHAR(50) DEFAULT '1.2k',
                    total_livros INT DEFAULT 1,
                    citacao TEXT,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # Cria tabela artigos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS artigos (
                    id_artigo INT AUTO_INCREMENT PRIMARY KEY,
                    titulo VARCHAR(255) NOT NULL,
                    subtitulo VARCHAR(255),
                    autor_nome VARCHAR(255) NOT NULL,
                    autor_foto VARCHAR(500),
                    autor_origem VARCHAR(100),
                    categoria VARCHAR(100) NOT NULL,
                    categoria_slug VARCHAR(50),
                    tempo_leitura VARCHAR(50) DEFAULT '5 min de leitura',
                    data_publicacao VARCHAR(50),
                    resumo TEXT,
                    conteudo_html LONGTEXT NOT NULL,
                    tags_json TEXT,
                    curtidas INT DEFAULT 0,
                    comentarios_json LONGTEXT,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            try:
                cursor.execute("ALTER TABLE lancamentos_autorais ADD COLUMN capa_imagem VARCHAR(500);")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE livros ADD COLUMN capa_imagem VARCHAR(500);")
            except Exception:
                pass
            mysql.connection.commit()
            cursor.close()
            garantir_epubs_padrao()
            print("Banco de dados MySQL verificado/inicializado com sucesso!")
            return # Sai da função se der certo
        except Exception as e:
            print(f"Aviso: Não foi possível conectar ao MySQL ({e}). Usando banco local SQLite como fallback.")

        # Fallback automático para SQLite local caso o MySQL não esteja disponível
        mysql.use_sqlite = True
        cursor = mysql.connection.cursor()
        cursor.execute("""
        
            CREATE TABLE IF NOT EXISTS usuario (
                id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
                nome VARCHAR(255),
                usuario VARCHAR(255) NOT NULL UNIQUE,
                senha_hash VARCHAR(255) NOT NULL,
                cpf VARCHAR(14) NOT NULL UNIQUE
            );
        """)
        try:
            cursor.execute("ALTER TABLE usuario ADD COLUMN nome VARCHAR(255);")
            mysql.connection.commit()
        except Exception:
            pass
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS livros (
                id_livro INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo VARCHAR(255) NOT NULL,
                autor VARCHAR(255),
                arquivo_epub VARCHAR(10),
                id_categoria INT
            );
        """)
        try:
            cursor.execute("ALTER TABLE livros ADD COLUMN capa_imagem VARCHAR(500);")
        except Exception:
            pass
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS modelo_grafica (
                id_modelo INTEGER PRIMARY KEY AUTOINCREMENT,
                id_usuario INT UNIQUE,
                titulo VARCHAR(255),
                autor VARCHAR(255),
                dados_json TEXT,
                FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE CASCADE
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
        ('5minutos.epub', '5minutos', 'José de Alencar', 'https://images.unsplash.com/photo-1516979187457-637abb4f9353?auto=format&fit=crop&w=600&q=80'),
        ('A Dadiva do Lobo - Anne Rice.epub', 'A Dádiva do Lobo', 'Anne Rice', 'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=600&q=80'),
    ]
    cursor = mysql.connection.cursor()
    for nome_arquivo, titulo, autor, capa in livros_padrao:
        origem = os.path.join(raiz_projeto, nome_arquivo)
        if not os.path.isfile(origem):
            continue
        cursor.execute("SELECT id_livro FROM livros WHERE LOWER(titulo) = LOWER(%s)", (titulo,))
        existente = cursor.fetchone()
        if existente:
            id_livro = existente['id_livro']
            try:
                cursor.execute("UPDATE livros SET capa_imagem = %s WHERE id_livro = %s AND (capa_imagem IS NULL OR capa_imagem = '')", (capa, id_livro))
            except Exception:
                pass
        else:
            try:
                cursor.execute(
                    "INSERT INTO livros (titulo, autor, arquivo_epub, id_categoria, capa_imagem) VALUES (%s, %s, %s, %s, %s)",
                    (titulo, autor, 'EPUB', None, capa)
                )
                id_livro = cursor.lastrowid
            except Exception:
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


LANCAMENTOS_AUTORAIS = [
    {
        "id": 1,
        "titulo": "O Protocolo Ômega: Linha de Fogo",
        "subtitulo": "Uma conspiração cibernética e agentes em fuga na América Latina",
        "autor": "Carlos Viana",
        "autor_cidade": "São Paulo, SP",
        "autor_bio": "Perito em cibersegurança e escritor independente de ação e espionagem tática.",
        "genero": "acao",
        "genero_label": "Ação",
        "cor_tema": "#dc2626",
        "capa_imagem": "https://images.unsplash.com/photo-1508739773434-c26b3d09e071?auto=format&fit=crop&w=600&q=80",
        "ano": 2026,
        "data_lancamento": "12/10/2026",
        "paginas": 340,
        "tempo_leitura": "6h 20min",
        "avaliacao": 4.9,
        "total_avaliacoes": 148,
        "formato": "EPUB Digital",
        "sinopse": "Quando um pacote de dados ultrassecreto é interceptado nas fronteiras do Cone Sul, o ex-analista Hugo Montenegro se vê perseguido por uma organização paramilitar fantasma. Em uma corrida contra o tempo repleta de tiroteios táticos e espionagem eletrônica, sua única saída é expor a conspiração antes que o silêncio se torne permanente.",
        "nota_autor": "Escrevi esta obra ao longo de dois anos nas madrugadas após meus plantões. Meu objetivo foi conceber um thriller de ação eletrizante genuinamente ambientado no Brasil e na América do Sul, sem clichês e com ritmo cinematográfico 100% autoral.",
        "badges": ["100% Autoral", "Ação Eletrizante", "Destaque 2026"]
    },
    {
        "id": 2,
        "titulo": "Alvo em Movimento: Rota 116",
        "subtitulo": "700 quilômetros entre a verdade e a sobrevivência",
        "autor": "Mariana Prado",
        "autor_cidade": "Belo Horizonte, MG",
        "autor_bio": "Especialista em pilotagem defensiva e autora de ficção policial e perseguições.",
        "genero": "acao",
        "genero_label": "Ação",
        "cor_tema": "#b91c1c",
        "capa_imagem": "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?auto=format&fit=crop&w=600&q=80",
        "ano": 2026,
        "data_lancamento": "28/09/2026",
        "paginas": 295,
        "tempo_leitura": "5h 15min",
        "avaliacao": 4.8,
        "total_avaliacoes": 92,
        "formato": "EPUB Digital",
        "sinopse": "Uma motorista de transporte blindado transportando uma testemunha-chave precisa cruzar a rodovia federal enquanto emboscadas coordenadas tentam impedi-la a qualquer custo. Velocidade implacável e decisões em frações de segundo marcam cada curva do trajeto.",
        "nota_autor": "Minha vivência nas estradas brasileiras serviu de combustível para cada linha deste livro autoral. Queria uma protagonista feminina forte, inteligente e que vencesse pela técnica e coragem bruta.",
        "badges": ["Obra Autoral", "Perseguição Tática"]
    },
    {
        "id": 3,
        "titulo": "Cartas para o Amanhã",
        "subtitulo": "O tempo separa destinos, mas a memória reencontra caminhos",
        "autor": "Beatriz Albuquerque",
        "autor_cidade": "Curitiba, PR",
        "autor_bio": "Poeta e romancista autoral, apaixonada por narrativas epistolares e dramas afetivos.",
        "genero": "romance",
        "genero_label": "Romance",
        "cor_tema": "#db2777",
        "capa_imagem": "https://images.unsplash.com/photo-1516589178581-6cd7833ae3b2?auto=format&fit=crop&w=600&q=80",
        "ano": 2026,
        "data_lancamento": "18/10/2026",
        "paginas": 310,
        "tempo_leitura": "5h 40min",
        "avaliacao": 5.0,
        "total_avaliacoes": 215,
        "formato": "EPUB Digital",
        "sinopse": "Entre cafeterias históricas e estações de trem antigas no inverno do sul, dois jovens artistas trocam correspondências anônimas cheias de confidências e sensibilidade, sem suspeitar que convivem diariamente como rivais de ateliê.",
        "nota_autor": "Este romance nasceu das cartas reais que guardei durante anos em uma gaveta de mogno. Lançar de forma autoral e independente no BookShelf foi a realização de um sonho de dar voz a amores genuínos que sobrevivem ao tempo.",
        "badges": ["100% Autoral", "Favorito dos Leitores", "Romance Emocionante"]
    },
    {
        "id": 4,
        "titulo": "Sob a Luz das Estrelas de Outono",
        "subtitulo": "Promessas feitas sob a maré alta",
        "autor": "Lucas Santana",
        "autor_cidade": "Salvador, BA",
        "autor_bio": "Escritor independente baiano focado em romances contemporâneos e afeto cotidiano.",
        "genero": "romance",
        "genero_label": "Romance",
        "cor_tema": "#c026d3",
        "capa_imagem": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=600&q=80",
        "ano": 2026,
        "data_lancamento": "05/10/2026",
        "paginas": 260,
        "tempo_leitura": "4h 30min",
        "avaliacao": 4.9,
        "total_avaliacoes": 110,
        "formato": "EPUB Digital",
        "sinopse": "Um biólogo marinho e uma arquiteta urbana se encontram durante um retiro no litoral baiano, descobrindo que o amor exige a coragem de desacelerar o ritmo do mundo moderno para ouvir as marés do próprio coração.",
        "nota_autor": "Dediquei três anos escrevendo cada diálogo deste livro ouvindo o quebrar das ondas. Queria mostrar que o romance maduro é construído na escuta e na gentileza compartilhada.",
        "badges": ["Obra Autoral", "Romance Contemporâneo"]
    },
    {
        "id": 5,
        "titulo": "Manual do Caos Diário: Como Sobreviver a Si Mesmo",
        "subtitulo": "Crônicas impagáveis sobre a arte de complicar a vida adulta",
        "autor": "Tiago Fontes",
        "autor_cidade": "Rio de Janeiro, RJ",
        "autor_bio": "Roteirista, cronista de humor e sobrevivente de reuniões corporativas que poderiam ser e-mails.",
        "genero": "comedia",
        "genero_label": "Comédia",
        "cor_tema": "#f59e0b",
        "capa_imagem": "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=600&q=80",
        "ano": 2026,
        "data_lancamento": "10/10/2026",
        "paginas": 220,
        "tempo_leitura": "3h 50min",
        "avaliacao": 4.9,
        "total_avaliacoes": 184,
        "formato": "EPUB Digital",
        "sinopse": "Uma coletânea impagável de desastres cotidianos: a saga de montar móveis sem ler o manual, conversas constrangedoras em elevadores apinhados, dietas que duram 42 minutos e o dilema existencial de responder mensagens no domingo à noite.",
        "nota_autor": "Escrevi cada capítulo rindo e chorando de mim mesmo. Se a vida adulta é um boleto que nunca para de chegar, o riso é o único desconto concedido pela realidade. Uma obra 100% escrita com as minhas próprias vergonhas!",
        "badges": ["100% Autoral", "Gargalhadas Garantidas", "Sucesso de Leituras"]
    },
    {
        "id": 6,
        "titulo": "O Casamento da Minha Inimiga",
        "subtitulo": "O que fazer quando você é promovida a madrinha por engano?",
        "autor": "Clarice Montenegro",
        "autor_cidade": "Recife, PE",
        "autor_bio": "Cronista de costumes e autora autoral de comédias satíricas e ácidas.",
        "genero": "comedia",
        "genero_label": "Comédia",
        "cor_tema": "#ea580c",
        "capa_imagem": "https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&w=600&q=80",
        "ano": 2026,
        "data_lancamento": "22/09/2026",
        "paginas": 245,
        "tempo_leitura": "4h 10min",
        "avaliacao": 4.8,
        "total_avaliacoes": 137,
        "formato": "EPUB Digital",
        "sinopse": "Uma sequência absurda de coincidências coloca Clara na posição de coordenar o luxuoso casamento da garota que infernizou seu ensino médio. O evento vira um campo minado de docinhos sabotados, parentes indiscretos e um padrinho incrivelmente charmoso.",
        "nota_autor": "Sempre fui aquela amiga que narrava as gafes de festas e fazia todo mundo chorar de rir. Transformar esse talento em um livro autoral e divertir centenas de leitores é o maior prazer da minha carreira.",
        "badges": ["Obra Autoral", "Comédia Ácida"]
    },
    {
        "id": 7,
        "titulo": "Vozes do Sertão: Memórias, Seca e Resistência",
        "subtitulo": "Histórias orais de quem fez da terra árida poesia e sustento",
        "autor": "Helena Castro",
        "autor_cidade": "Juazeiro do Norte, CE",
        "autor_bio": "Pesquisadora social, documentarista independente e defensora da tradição oral brasileira.",
        "genero": "documentario",
        "genero_label": "Documentários",
        "cor_tema": "#2563eb",
        "capa_imagem": "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?auto=format&fit=crop&w=600&q=80",
        "ano": 2026,
        "data_lancamento": "01/10/2026",
        "paginas": 380,
        "tempo_leitura": "7h 15min",
        "avaliacao": 5.0,
        "total_avaliacoes": 276,
        "formato": "EPUB Digital",
        "sinopse": "Resultado de quatro anos de expedições pelo semiárido brasileiro, reunindo 42 relatos orais inéditos de agricultoras, artesãos e mestres da cultura popular. Uma radiografia humana comovente sobre ancestralidade, ecologia e persistência.",
        "nota_autor": "Percorri milhares de quilômetros de poeira e sol com meu gravador. Como autora independente, minha missão foi garantir que a sabedoria e a dignidade desse povo fossem imortalizadas nas páginas deste documento histórico.",
        "badges": ["100% Autoral", "Documentário Premiado", "Pesquisa Histórica"]
    },
    {
        "id": 8,
        "titulo": "Além do Algoritmo: A Revolução Invisível da Tecnologia",
        "subtitulo": "Uma investigação profunda sobre como a IA redefiniu o trabalho humano",
        "autor": "Eduardo Brandão",
        "autor_cidade": "Florianópolis, SC",
        "autor_bio": "Jornalista de investigação, ensaísta e escritor com foco em tecnologia e sociedade.",
        "genero": "documentario",
        "genero_label": "Documentários",
        "cor_tema": "#1d4ed8",
        "capa_imagem": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=600&q=80",
        "ano": 2026,
        "data_lancamento": "14/10/2026",
        "paginas": 325,
        "tempo_leitura": "6h 00min",
        "avaliacao": 4.9,
        "total_avaliacoes": 165,
        "formato": "EPUB Digital",
        "sinopse": "Uma investigação documental contundente que ouve operários, médicos, professores e desenvolvedores para revelar os bastidores da automação e discutir o futuro do trabalho criativo e da sensibilidade humana no século XXI.",
        "nota_autor": "Este documentário escrito é fruto de dezenas de entrevistas gravadas e checadas pessoalmente por mim. Escrever de autoria própria permitiu manter a independência editorial sem amarras corporativas.",
        "badges": ["Investigação Documental", "100% Autoral", "Pensamento Crítico"]
    }
]


@app.route('/lancamentos')
def lancamentos():
    genero_filtro = (request.args.get('genero') or '').strip().lower()
    busca = (request.args.get('q') or '').strip().lower()

    livros_base = LANCAMENTOS_AUTORAIS
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM lancamentos_autorais")
        rows = cursor.fetchall()
        cursor.close()
        if rows:
            for r in rows:
                if 'id_lancamento' in r:
                    r['id'] = r['id_lancamento']
                if isinstance(r.get('badges_json'), str):
                    try:
                        r['badges'] = json.loads(r['badges_json'])
                    except Exception:
                        r['badges'] = ["100% Autoral"]
                elif 'badges' not in r:
                    r['badges'] = ["100% Autoral"]
            livros_base = rows
    except Exception:
        livros_base = LANCAMENTOS_AUTORAIS

    livros_filtrados = livros_base

    if genero_filtro and genero_filtro != 'todos':
        livros_filtrados = [
            livro for livro in livros_filtrados
            if livro['genero'].lower() == genero_filtro
        ]

    if busca:
        livros_filtrados = [
            livro for livro in livros_filtrados
            if busca in livro['titulo'].lower()
            or busca in livro['autor'].lower()
            or busca in (livro.get('subtitulo') or '').lower()
            or busca in (livro.get('sinopse') or '').lower()
            or busca in (livro.get('genero_label') or '').lower()
        ]

    contagens = {
        'todos': len(livros_base),
        'acao': sum(1 for l in livros_base if l['genero'] == 'acao'),
        'romance': sum(1 for l in livros_base if l['genero'] == 'romance'),
        'comedia': sum(1 for l in livros_base if l['genero'] == 'comedia'),
        'documentario': sum(1 for l in livros_base if l['genero'] == 'documentario'),
    }

    return render_template(
        'lancamentos.html',
        lancamentos=livros_filtrados,
        genero_ativo=genero_filtro or 'todos',
        busca=busca,
        contagens=contagens
    )


AUTORES_MOCADOS = [
    {
        "id": 1,
        "nome": "Carlos Viana",
        "tipo": "comunidade",
        "tipo_badge": "Autor da Comunidade (Própria Autoria)",
        "foto": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=500&q=80",
        "origem": "São Paulo, SP",
        "bio_curta": "Perito em cibersegurança e escritor autoral de thrillers táticos e espionagem contemporânea.",
        "bio_completa": "Carlos Viana atua há mais de 12 anos na área de inteligência e segurança da informação. Fascinado pela geopolítica latino-americana e operações secretas, decidiu transformar suas pesquisas em ficção literária autoral. Escreveu 'O Protocolo Ômega' nas madrugadas pós-plantão, consolidando-se como uma das vozes mais promissoras da literatura de ação independente no BookShelf.",
        "generos": ["Ação", "Espionagem", "Suspense"],
        "livros": [
            {"titulo": "O Protocolo Ômega: Linha de Fogo", "genero": "Ação", "ano": 2026, "formato": "EPUB Digital", "cor": "#dc2626", "capa": "https://images.unsplash.com/photo-1508739773434-c26b3d09e071?auto=format&fit=crop&w=400&q=80"}
        ],
        "total_leitores": "1.4k leitores",
        "total_livros": 1,
        "citacao": "A melhor ficção de ação é aquela que faz você desconfiar de cada sombra no mundo real."
    },
    {
        "id": 2,
        "nome": "Beatriz Albuquerque",
        "tipo": "comunidade",
        "tipo_badge": "Autora da Comunidade (Própria Autoria)",
        "foto": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=500&q=80",
        "origem": "Curitiba, PR",
        "bio_curta": "Poeta e romancista autoral, especialista em tramas epistolares e dramas afetivos sensíveis.",
        "bio_completa": "Formada em Letras e artes visuais, Beatriz dedica suas horas à caligrafia tradicional e à escrita afetiva. Seu romance de própria autoria 'Cartas para o Amanhã' nasceu a partir de cartas reais preservadas ao longo de uma década, cativando centenas de leitores no BookShelf pela riqueza poética e diálogos profundos.",
        "generos": ["Romance", "Drama", "Poesia"],
        "livros": [
            {"titulo": "Cartas para o Amanhã", "genero": "Romance", "ano": 2026, "formato": "EPUB Digital", "cor": "#db2777", "capa": "https://images.unsplash.com/photo-1516589178581-6cd7833ae3b2?auto=format&fit=crop&w=400&q=80"}
        ],
        "total_leitores": "2.1k leitores",
        "total_livros": 1,
        "citacao": "As palavras escritas à mão têm o poder mágico de vencer qualquer distância temporal."
    },
    {
        "id": 3,
        "nome": "Tiago Fontes",
        "tipo": "comunidade",
        "tipo_badge": "Autor da Comunidade (Própria Autoria)",
        "foto": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=500&q=80",
        "origem": "Rio de Janeiro, RJ",
        "bio_curta": "Cronista de humor cotidiano e roteirista apaixonado pela arte de rir dos próprios tropeços.",
        "bio_completa": "Carioca da gema, Tiago transformou desastres corporativos e perrengues urbanos em literatura de entretenimento leve e inteligente. Sua coletânea de própria autoria 'Manual do Caos Diário' tornou-se leitura obrigatória para quem precisa desestressar com boas gargalhadas no trajeto para o trabalho.",
        "generos": ["Comédia", "Humor", "Crônica"],
        "livros": [
            {"titulo": "Manual do Caos Diário: Como Sobreviver a Si Mesmo", "genero": "Comédia", "ano": 2026, "formato": "EPUB Digital", "cor": "#f59e0b", "capa": "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=400&q=80"}
        ],
        "total_leitores": "1.8k leitores",
        "total_livros": 1,
        "citacao": "Se a vida adulta não vem com manual de instruções, pelo menos deve vir com boas piadas."
    },
    {
        "id": 4,
        "nome": "Helena Castro",
        "tipo": "comunidade",
        "tipo_badge": "Autora da Comunidade (Própria Autoria)",
        "foto": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=500&q=80",
        "origem": "Juazeiro do Norte, CE",
        "bio_curta": "Pesquisadora social, memorialista oral e defensora da história viva do povo sertanejo.",
        "bio_completa": "Dedicou mais de 4 anos viajando com gravador e caderneta por vilarejos remotos do semiárido. Seu documentário literário autoral 'Vozes do Sertão' imortalizou 42 histórias orais de mestres da tradição, agricultores e poetas populares, recebendo aclamação crítica pela sensibilidade e rigor documental.",
        "generos": ["Documentários", "História Oral", "Não-Ficção"],
        "livros": [
            {"titulo": "Vozes do Sertão: Memórias, Seca e Resistência", "genero": "Documentários", "ano": 2026, "formato": "EPUB Digital", "cor": "#2563eb", "capa": "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?auto=format&fit=crop&w=400&q=80"}
        ],
        "total_leitores": "2.7k leitores",
        "total_livros": 1,
        "citacao": "Contar a história de quem a história oficial esqueceu é o dever mais nobre de um escritor."
    },
    {
        "id": 5,
        "nome": "Mariana Prado",
        "tipo": "comunidade",
        "tipo_badge": "Autora da Comunidade (Própria Autoria)",
        "foto": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=500&q=80",
        "origem": "Belo Horizonte, MG",
        "bio_curta": "Instrutora de direção defensiva e romancista de ficção policial e perseguições eletrizantes.",
        "bio_completa": "Apaixonada por motores e velocidade desde a adolescência, Mariana escreveu de própria autoria 'Alvo em Movimento: Rota 116', trazendo mulheres fortes para o centro de investigações táticas e cenas de ação no asfalto brasileiro.",
        "generos": ["Ação", "Policial", "Investigação"],
        "livros": [
            {"titulo": "Alvo em Movimento: Rota 116", "genero": "Ação", "ano": 2026, "formato": "EPUB Digital", "cor": "#b91c1c", "capa": "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?auto=format&fit=crop&w=400&q=80"}
        ],
        "total_leitores": "950 leitores",
        "total_livros": 1,
        "citacao": "Na estrada e na escrita, a velocidade só tem valor se você dominar o volante."
    },
    {
        "id": 6,
        "nome": "Lucas Santana",
        "tipo": "comunidade",
        "tipo_badge": "Autor da Comunidade (Própria Autoria)",
        "foto": "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=500&q=80",
        "origem": "Salvador, BA",
        "bio_curta": "Biólogo e escritor independente de romances contemporâneos acolhedores.",
        "bio_completa": "Escreveu seu primeiro livro autoral 'Sob a Luz das Estrelas de Outono' entre idas e vindas de pesquisas marinhas na Baía de Todos-os-Santos. Defende a literatura que acolhe o leitor e promove a conexão com a natureza e com os afetos simples.",
        "generos": ["Romance", "Contemporâneo"],
        "livros": [
            {"titulo": "Sob a Luz das Estrelas de Outono", "genero": "Romance", "ano": 2026, "formato": "EPUB Digital", "cor": "#c026d3", "capa": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=400&q=80"}
        ],
        "total_leitores": "1.1k leitores",
        "total_livros": 1,
        "citacao": "O amor maduro não tem pressa; ele aprende a respirar no ritmo da maré."
    },
    {
        "id": 7,
        "nome": "Clarice Montenegro",
        "tipo": "comunidade",
        "tipo_badge": "Autora da Comunidade (Própria Autoria)",
        "foto": "https://images.unsplash.com/photo-1580489944761-15a19d654956?auto=format&fit=crop&w=500&q=80",
        "origem": "Recife, PE",
        "bio_curta": "Autora autoral de comédias satíricas, romances divertidos e peripécias sociais.",
        "bio_completa": "Conhecida pelo olhar atento para as pequenas hipocrisias dos encontros de família e eventos sociais, Clarice escreveu de própria autoria 'O Casamento da Minha Inimiga', conquistando leitores com ironia refinada e diálogos impagáveis.",
        "generos": ["Comédia", "Sátira", "Romance"],
        "livros": [
            {"titulo": "O Casamento da Minha Inimiga", "genero": "Comédia", "ano": 2026, "formato": "EPUB Digital", "cor": "#ea580c", "capa": "https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&w=400&q=80"}
        ],
        "total_leitores": "1.3k leitores",
        "total_livros": 1,
        "citacao": "A ironia é a maneira mais elegante de rir das confusões da vida."
    },
    {
        "id": 8,
        "nome": "Eduardo Brandão",
        "tipo": "comunidade",
        "tipo_badge": "Autor da Comunidade (Própria Autoria)",
        "foto": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=500&q=80",
        "origem": "Florianópolis, SC",
        "bio_curta": "Jornalista investigativo focado nos impactos sociais e humanos da revolução tecnológica.",
        "bio_completa": "Com passagens por redações e centros de pesquisa de tecnologia, produziu de forma 100% autoral a obra 'Além do Algoritmo', investigando como a automação e a inteligência artificial afetam o ofício criativo de trabalhadores ao redor do mundo.",
        "generos": ["Documentários", "Tecnologia", "Investigação"],
        "livros": [
            {"titulo": "Além do Algoritmo: A Revolução Invisível da Tecnologia", "genero": "Documentários", "ano": 2026, "formato": "EPUB Digital", "cor": "#1d4ed8", "capa": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=400&q=80"}
        ],
        "total_leitores": "1.6k leitores",
        "total_livros": 1,
        "citacao": "A inteligência artificial pode imitar a sintaxe, mas a alma da história só o ser humano é capaz de sentir."
    },
    {
        "id": 9,
        "nome": "Machado de Assis",
        "tipo": "acervo",
        "tipo_badge": "Mestre do Acervo BookShelf",
        "foto": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cd/Machado_de_Assis_real.jpg/480px-Machado_de_Assis_real.jpg",
        "origem": "Rio de Janeiro (1839 - 1908)",
        "bio_curta": "Fundador da Academia Brasileira de Letras e um dos maiores gênios da literatura universal.",
        "bio_completa": "Joaquim Maria Machado de Assis é amplamente considerado o maior escritor da literatura brasileira. Romancista, contista, dramaturgo e poeta, revolucionou o romance ocidental com narradores não-confiáveis, ironia cáustica e uma análise psicológica sem precedentes da alma humana.",
        "generos": ["Clássicos", "Realismo"],
        "livros": [
            {"titulo": "Dom Casmurro", "genero": "Clássicos", "ano": 1899, "formato": "EPUB", "cor": "#5E0B15", "capa": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&w=400&q=80"},
            {"titulo": "Memórias Póstumas de Brás Cubas", "genero": "Clássicos", "ano": 1881, "formato": "EPUB", "cor": "#90323D", "capa": "https://images.unsplash.com/photo-1457369804613-52c61a468e7d?auto=format&fit=crop&w=400&q=80"}
        ],
        "total_leitores": "15.8k leitores",
        "total_livros": 2,
        "citacao": "A melhor definição de amor não vale um beijo de moça namorada."
    },
    {
        "id": 10,
        "nome": "José de Alencar",
        "tipo": "acervo",
        "tipo_badge": "Mestre do Acervo BookShelf",
        "foto": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b8/Jos%C3%A9_de_Alencar_por_Ferdinand_Krumholz%2C_1874.jpg/480px-Jos%C3%A9_de_Alencar_por_Ferdinand_Krumholz%2C_1874.jpg",
        "origem": "Fortaleza (1829 - 1877)",
        "bio_curta": "Patrono da literatura romântica brasileira e criador de épicos fundacionais.",
        "bio_completa": "Advogado, jornalista e escritor cearense, Alencar foi o grande arquiteto da nacionalidade na prosa brasileira. Suas obras abordam desde narrativas urbanas de costumes até épicos indianistas líricos, consolidando a identidade cultural do país no século XIX.",
        "generos": ["Clássicos", "Romantismo"],
        "livros": [
            {"titulo": "5minutos", "genero": "Clássicos", "ano": 1856, "formato": "EPUB", "cor": "#BC8034", "capa": "https://images.unsplash.com/photo-1516979187457-637abb4f9353?auto=format&fit=crop&w=400&q=80"},
            {"titulo": "Iracema", "genero": "Clássicos", "ano": 1865, "formato": "EPUB", "cor": "#78350f", "capa": "https://images.unsplash.com/photo-1448375240586-882707db888b?auto=format&fit=crop&w=400&q=80"}
        ],
        "total_leitores": "9.4k leitores",
        "total_livros": 2,
        "citacao": "O amor é a vida do coração; sem ele a alma definha e morre."
    },
    {
        "id": 11,
        "nome": "Aluísio Azevedo",
        "tipo": "acervo",
        "tipo_badge": "Mestre do Acervo BookShelf",
        "foto": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Alu%C3%ADsio_Azevedo.jpg/480px-Alu%C3%ADsio_Azevedo.jpg",
        "origem": "São Luís (1857 - 1913)",
        "bio_curta": "Pioneiro do Naturalismo brasileiro e retratista das tensões urbanas e sociais.",
        "bio_completa": "Diplomata, jornalista e romancista maranhense, introduziu a estética naturalista no Brasil com 'O Mulato' e eternizou as contradições da vida coletiva carioca na obra-prima 'O Cortiço', combinando observação incisiva e crítica social vigorosa.",
        "generos": ["Clássicos", "Naturalismo"],
        "livros": [
            {"titulo": "O Cortiço", "genero": "Clássicos", "ano": 1890, "formato": "EPUB", "cor": "#854d0e", "capa": "https://images.unsplash.com/photo-1476275466078-4007374efbbe?auto=format&fit=crop&w=400&q=80"}
        ],
        "total_leitores": "8.2k leitores",
        "total_livros": 1,
        "citacao": "O meio determina o homem, mas a literatura ilumina as sombras desse meio."
    },
    {
        "id": 12,
        "nome": "Anne Rice",
        "tipo": "acervo",
        "tipo_badge": "Autora Internacional do Acervo",
        "foto": "https://images.unsplash.com/photo-1544717305-2782549b5136?auto=format&fit=crop&w=500&q=80",
        "origem": "Nova Orleans (1941 - 2021)",
        "bio_curta": "Escritora norte-americana mestre da ficção gótica, mitologia de vampiros e licantropos.",
        "bio_completa": "Nascida na atmosfera mística de Nova Orleans, Anne Rice revolucionou a literatura fantástica moderna, humanizando criaturas sobrenaturais e explorando dilemas existenciais, imortalidade e sensualidade em obras como 'A Dádiva do Lobo' e 'As Crônicas Vampirescas'.",
        "generos": ["Fantasia", "Ficção Gótica"],
        "livros": [
            {"titulo": "A Dádiva do Lobo", "genero": "Fantasia", "ano": 2012, "formato": "EPUB", "cor": "#4c1d95", "capa": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=400&q=80"}
        ],
        "total_leitores": "11.5k leitores",
        "total_livros": 1,
        "citacao": "A escuridão revela verdades que a luz do dia insiste em disfarçar."
    },
    {
        "id": 13,
        "nome": "Graciliano Ramos",
        "tipo": "acervo",
        "tipo_badge": "Mestre do Acervo BookShelf",
        "foto": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Graciliano_Ramos.jpg/480px-Graciliano_Ramos.jpg",
        "origem": "Quebrangulo (1892 - 1953)",
        "bio_curta": "Ícone do Modernismo de 30 e mestre da concisão estilística e do realismo documental.",
        "bio_completa": "Escritor alagoano, sua prosa enxuta e cortante retratou com fidelidade pungente a tragédia da seca e a dignidade do sertanejo em 'Vidas Secas'. Uma das maiores referências de estilo e compromisso ético da literatura em língua portuguesa.",
        "generos": ["Clássicos", "Modernismo"],
        "livros": [
            {"titulo": "Vidas Secas", "genero": "Clássicos", "ano": 1938, "formato": "EPUB", "cor": "#713f12", "capa": "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?auto=format&fit=crop&w=400&q=80"}
        ],
        "total_leitores": "12.3k leitores",
        "total_livros": 1,
        "citacao": "A palavra não foi feita para enfeitar, foi feita para dizer."
    }
]


@app.route('/autores')
def autores():
    tipo_filtro = (request.args.get('tipo') or '').strip().lower()
    genero_filtro = (request.args.get('genero') or '').strip().lower()
    busca = (request.args.get('q') or '').strip().lower()

    autores_base = AUTORES_MOCADOS
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM autores")
        rows = cursor.fetchall()
        cursor.close()
        if rows:
            for r in rows:
                if 'id_autor' in r:
                    r['id'] = r['id_autor']
                if isinstance(r.get('generos_json'), str):
                    try:
                        r['generos'] = json.loads(r['generos_json'])
                    except Exception:
                        r['generos'] = []
                elif 'generos' not in r:
                    r['generos'] = []
                if isinstance(r.get('livros_json'), str):
                    try:
                        r['livros'] = json.loads(r['livros_json'])
                    except Exception:
                        r['livros'] = []
                elif 'livros' not in r:
                    r['livros'] = []
            autores_base = rows
    except Exception:
        autores_base = AUTORES_MOCADOS

    autores_filtrados = autores_base

    if tipo_filtro and tipo_filtro != 'todos':
        autores_filtrados = [
            a for a in autores_filtrados
            if a['tipo'].lower() == tipo_filtro
        ]

    if genero_filtro and genero_filtro != 'todos':
        autores_filtrados = [
            a for a in autores_filtrados
            if any(genero_filtro in g.lower() for g in a.get('generos', []))
        ]

    if busca:
        autores_filtrados = [
            a for a in autores_filtrados
            if busca in a['nome'].lower()
            or busca in (a.get('bio_curta') or '').lower()
            or busca in (a.get('bio_completa') or '').lower()
            or busca in (a.get('origem') or '').lower()
            or any(busca in l.get('titulo', '').lower() for l in a.get('livros', []))
        ]

    contagens = {
        'todos': len(autores_base),
        'comunidade': sum(1 for a in autores_base if a['tipo'] == 'comunidade'),
        'acervo': sum(1 for a in autores_base if a['tipo'] == 'acervo')
    }

    return render_template(
        'autores.html',
        autores=autores_filtrados,
        tipo_ativo=tipo_filtro or 'todos',
        genero_ativo=genero_filtro or 'todos',
        busca=busca,
        contagens=contagens
    )


@app.route('/autor/<int:id_autor>')
def detalhe_autor(id_autor):
    autor_encontrado = None
    for a in AUTORES_MOCADOS:
        if a['id'] == id_autor:
            autor_encontrado = a
            break
    if not autor_encontrado:
        flash("Autor não encontrado.", "error")
        return redirect(url_for('autores'))
    return render_template('autores.html', autores=[autor_encontrado], tipo_ativo='todos', genero_ativo='todos', busca='', contagens={'todos': 1, 'comunidade': 1 if autor_encontrado['tipo'] == 'comunidade' else 0, 'acervo': 1 if autor_encontrado['tipo'] == 'acervo' else 0}, autor_foco=autor_encontrado)


# ====================================================================
# ARTIGOS DE OPINIÃO E ENSAIOS LITERÁRIOS (ESCRITA EDITORIAL)
# ====================================================================
ARTIGOS_MOCADOS = [
    {
        "id": 1,
        "titulo": "Por que a Inteligência Artificial nunca sentirá a dor da página em branco",
        "subtitulo": "Algoritmos combinam probabilidades estatísticas em frações de segundo, mas a literatura autêntica brota da imperfeição, da dúvida e do assombro humano.",
        "autor_nome": "Eduardo Brandão",
        "autor_foto": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=500&q=80",
        "autor_origem": "Florianópolis, SC",
        "categoria": "Tecnologia & Escrita",
        "categoria_slug": "tecnologia",
        "tempo_leitura": "6 min de leitura",
        "data_publicacao": "03 de Novembro de 2026",
        "resumo": "Nos últimos meses, o mercado editorial foi inundado pela euforia da automação textual. Mas o que máquinas que nunca viveram um luto ou uma paixão podem realmente dizer sobre a condição humana?",
        "conteudo_html": """
<p class="article-lead">Nos últimos dois anos, vi dezenas de conferências anunciarem que o algoritmo substituiria o romancista e o ensaísta. Como alguém que passou metade da vida cobrindo tecnologia e a outra metade escrevendo reportagens investigativas e livros no BookShelf, sinto que estamos cometendo um erro categórico grotesco: estamos confundindo fluência gramatical com alma literária.</p>

<h3>A fábrica de respostas prontas</h3>
<p>Um modelo de linguagem em larga escala não escreve porque precisa desabafar, sangrar ou compreender uma perda. Ele prevê o próximo token mais estatisticamente provável com base em bilhões de palavras que outros seres humanos já pronunciaram. O algoritmo é, em essência, o maior conservador da história da linguagem: ele opera na média, no previsível, no consenso.</p>

<blockquote class="pull-quote">“A grande literatura nunca nasce do que é estatisticamente esperado. Ela explode exatamente quando o escritor desafia a média e nomeia o inominável.”</blockquote>

<h3>A vertigem do abismo em branco</h3>
<p>Qualquer pessoa que já se sentou às três da manhã diante de um cursor piscando conhece o peso da página em branco. Aquele silêncio que nos olha de volta não é um vazio operacional; é um espelho. É a hesitação que nos obriga a escolher entre a verdade desconfortável e a mentira elegante.</p>

<p>A máquina não hesita porque não tem nada a arriscar. Ela não teme o julgamento, não conhece o constrangimento, não chora no banho lembrando de uma frase infeliz dita há dez anos. Sem essa vulnerabilidade, o texto gerado pode ser impecável na métrica, mas soa como um quarto de hotel despersonalizado: perfeitamente arrumado, mas onde ninguém jamais habitou de verdade.</p>

<h3>O artesanato da palavra</h3>
<p>O futuro da literatura no BookShelf e no mundo não será a rendição cega à IA, mas o reencontro com o artesanato imperfeito. Leitores procuram livros e ensaios não para admirar o desempenho de uma máquina, mas para se sentirem menos sozinhos no universo. E essa comunhão, meus caros, nenhum cluster de servidores jamais será capaz de simular.</p>
""",
        "tags": ["Inteligência Artificial", "Processo Criativo", "Futuro do Trabalho", "Ensaio"],
        "curtidas": 142,
        "comentarios": [
            {
                "autor": "Helena Castro",
                "foto": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=500&q=80",
                "data": "Há 2 dias",
                "texto": "Brilhante reflexão, Eduardo. Quando estive no sertão ouvindo rezadeiras e vaqueiros, percebi que a poesia deles vinha do calo na mão e da seca na terra. Não há rede neural que simule a poeira nos olhos de quem vive.",
                "curtidas": 28
            },
            {
                "autor": "Carlos Viana",
                "foto": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=500&q=80",
                "data": "Há 1 dia",
                "texto": "Concordo em gênero, número e grau. No thriller tático, o suspense vem da hesitação moral do personagem. A IA é calculista demais para entender quando um herói decide errar por empatia.",
                "curtidas": 19
            }
        ]
    },
    {
        "id": 2,
        "titulo": "O elogio à lentidão: por que ainda precisamos de romances densos na era do scroll infinito",
        "subtitulo": "Em um ecossistema digital que fragmenta nossa atenção a cada três segundos, sentar-se com uma história de 300 páginas é o maior ato de rebeldia existencial.",
        "autor_nome": "Beatriz Albuquerque",
        "autor_foto": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=500&q=80",
        "autor_origem": "Curitiba, PR",
        "categoria": "Crítica Cultural",
        "categoria_slug": "critica",
        "tempo_leitura": "5 min de leitura",
        "data_publicacao": "29 de Outubro de 2026",
        "resumo": "A velocidade das notificações promete nos manter conectados a tudo, mas nos desconecta da profundidade. O romance não é passatempo; é um treino de permanência e empatia.",
        "conteudo_html": """
<p class="article-lead">Fui provocada recentemente por um leitor que me perguntou por que meu romance 'Cartas para o Amanhã' exigia tantos momentos de pausa e contemplação em vez de cortar direto para o clímax. Minha resposta foi simples: porque a vida real não é um feed de vídeos acelerados em duas vezes.</p>

<h3>A epidemia do imediatismo</h3>
<p>Fomos condicionados a encarar o tempo livre como uma lacuna a ser preenchida com estímulos rápidos. O resultado é uma ansiedade crônica: começamos dez leituras, não terminamos nenhuma e temos a sensação constante de que estamos perdendo algo urgente que aconteceu há cinco minutos em outra aba.</p>

<blockquote class="pull-quote">“Ler um romance denso não é uma fuga da realidade; é um retorno à única velocidade na qual o coração humano é capaz de compreender o outro.”</blockquote>

<h3>O santuário da página</h3>
<p>O romance exige um contrato de fidelidade que nenhuma outra mídia contemporânea tem coragem de pedir. Ele nos pede que esqueçamos as notificações por uma hora. Que moremos na mente de um personagem imperfeito, que andemos pelas suas ruas de terra ou cafeterias úmidas, que sintamos a textura do seu silêncio.</p>

<p>Ao fechar um livro após semanas de convivência com seus habitantes de papel, nós não apenas 'consumimos uma história': nós ampliamos o perímetro da nossa própria alma. Não tenhamos pressa de terminar o livro. A pressa é para as máquinas; o vagar é para os seres que amam.</p>
""",
        "tags": ["Leitura Profunda", "Atenção Plena", "Romance", "Resistência Cultural"],
        "curtidas": 198,
        "comentarios": [
            {
                "autor": "Tiago Fontes",
                "foto": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=500&q=80",
                "data": "Há 3 dias",
                "texto": "Faço coro, Beatriz! Inclusive tentei ler um livro enquanto respondia WhatsApp e acabei chorando na mensagem do síndico e rindo do velório no livro. A mente humana precisa desacelerar urgente!",
                "curtidas": 34
            },
            {
                "autor": "Lucas Santana",
                "foto": "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=500&q=80",
                "data": "Há 2 dias",
                "texto": "Perfeito. Escrevo sobre a beira-mar exatamente para lembrar as pessoas do ritmo das ondas. Ninguém consegue apressar a maré.",
                "curtidas": 15
            }
        ]
    },
    {
        "id": 3,
        "titulo": "Ficção de ação na América Latina: chega de importar heróis que não conhecem nossas ruas",
        "subtitulo": "Temos fronteiras porosas, conspirações geopolíticas reais e uma riqueza tática monumental. Já passou da hora da nossa literatura policial falar com a nossa própria voz.",
        "autor_nome": "Carlos Viana",
        "autor_foto": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=500&q=80",
        "autor_origem": "São Paulo, SP",
        "categoria": "Manifestos",
        "categoria_slug": "manifesto",
        "tempo_leitura": "7 min de leitura",
        "data_publicacao": "25 de Outubro de 2026",
        "resumo": "Durante décadas fomos educados a acreditar que intrigas de alto nível só ocorrem em Washington ou Londres. Meu manifesto como autor autoral é fincar os dois pés na nossa realidade latino-americana.",
        "conteudo_html": """
<p class="article-lead">Durante décadas fomos educados a acreditar que conspirações ultrassecretas só ocorrem nos corredores de Langley, nos subterrâneos de Berlim ou nos arranha-céus de Wall Street. Se um autor brasileiro quisesse escrever um romance de espionagem, parecia obrigado a inventar um agente chamado John ou Jack com passaporte falso em Genebra. Pois bem: isso é uma tolice provinciana que precisamos sepultar.</p>

<h3>A selva de concreto e a fronteira seca</h3>
<p>Quem conhece a tríplice fronteira, as estradas vicinais do Centro-Oeste, os portos de Santos e Paranaguá ou a complexidade das telecomunicações em São Paulo sabe que a América do Sul é o tabuleiro mais dinâmico, imprevisível e tenso do planeta. Aqui o perigo não veste smoking impecável: ele roda em picapes com placas trocadas e negocia em barracas de beira de rio.</p>

<blockquote class="pull-quote">“Não precisamos imitar o agente britânico de terno italiano quando temos policiais, peritos e sobreviventes com histórias mil vezes mais viscerais em solo latino.”</blockquote>

<h3>Autonomia estética</h3>
<p>Escrever 'O Protocolo Ômega' foi minha declaração de independência. Quis personagens que comessem comida de verdade, que falassem com nossas gírias e que enfrentassem dilemas éticos que nós vivemos todos os dias nos noticiários. A literatura de ação independente do BookShelf tem o compromisso de fincar raízes no nosso próprio chão. Quem ganha é o leitor, que finalmente se vê refletido no meio do fogo cruzado.</p>
""",
        "tags": ["Ação Nacional", "Manifesto Literário", "Literatura Policial", "Geopolítica"],
        "curtidas": 165,
        "comentarios": [
            {
                "autor": "Mariana Prado",
                "foto": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=500&q=80",
                "data": "Há 5 dias",
                "texto": "Assino embaixo com caneta de ferro, Carlos! O asfalto da BR-116 tem mais adrenalina e drama humano do que qualquer perseguição cenográfica importada.",
                "curtidas": 22
            }
        ]
    },
    {
        "id": 4,
        "titulo": "O riso como estratégia de sobrevivência: a comédia não é fuga, é diagnóstico",
        "subtitulo": "Quem não aprende a rir das pequenas humilhações da vida cotidiana acaba transformando qualquer boleto atrasado numa tragédia shakespeariana.",
        "autor_nome": "Tiago Fontes",
        "autor_foto": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=500&q=80",
        "autor_origem": "Rio de Janeiro, RJ",
        "categoria": "Opinião & Sociedade",
        "categoria_slug": "opiniao",
        "tempo_leitura": "4 min de leitura",
        "data_publicacao": "22 de Outubro de 2026",
        "resumo": "Na literatura, a comédia é frequentemente tratada como o parente pobre do drama. Um erro imperdoável: é preciso muito mais coragem para expor a própria palhaçada do que para posar de herói sofredor.",
        "conteudo_html": """
<p class="article-lead">Há um preconceito silencioso nos círculos literários: se uma história faz o leitor chorar, ela é considerada 'profunda'; se faz o leitor cuspir o café de rir no metrô, dizem que é apenas 'entretenimento ligeiro'. Pois eu discordo com todas as forças dos meus dois neurônios sobreviventes.</p>

<h3>A gravidade postiça das aparências</h3>
<p>A vida moderna exige que você seja um profissional impecável no LinkedIn, um atleta no Instagram, um investidor consciente e um monge zen nos momentos de trânsito. A verdade inconfessável? Todos nós estamos a apenas um zíper quebrado ou uma reunião mal interpretada de nos tornarmos o meme da semana.</p>

<blockquote class="pull-quote">“O humor não diminui a gravidade do mundo; ele apenas nos devolve a perspectiva de que ninguém aqui vai sair vivo desta história mesmo.”</blockquote>

<h3>A gargalhada que liberta</h3>
<p>Quando escrevi 'Manual do Caos Diário', meu maior objetivo era que o leitor fechasse a página pensando: 'Ufa, não sou só eu que sou esse desastre ambulante'. O riso cria uma cumplicidade instantânea entre desconhecidos. Rir das próprias misérias é a única vacina que conheço contra o veneno da soberba humana.</p>
""",
        "tags": ["Comédia", "Crônica", "Vida Cotidiana", "Saúde Mental"],
        "curtidas": 220,
        "comentarios": [
            {
                "autor": "Clarice Montenegro",
                "foto": "https://images.unsplash.com/photo-1580489944761-15a19d654956?auto=format&fit=crop&w=500&q=80",
                "data": "Há 4 dias",
                "texto": "Chorei de rir lendo isso! E acrescento: o maior perigo da vida adulta é quando a gente começa a se levar a sério demais. Parabéns pelo texto!",
                "curtidas": 31
            }
        ]
    },
    {
        "id": 5,
        "titulo": "Quem tem a licença para narrar o mundo? O poder revolucionário da escuta",
        "subtitulo": "Antes de escrever sobre as dores e lutas de um povo, o autor precisa aprender a arte de calar a própria voz para deixar ecoar o murmúrio da terra.",
        "autor_nome": "Helena Castro",
        "autor_foto": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=500&q=80",
        "autor_origem": "Juazeiro do Norte, CE",
        "categoria": "Processo Criativo",
        "categoria_slug": "processo",
        "tempo_leitura": "8 min de leitura",
        "data_publicacao": "16 de Outubro de 2026",
        "resumo": "O escritor não é um salvador que concede voz aos que não falam; é um mediador que precisa saber escutar com reverência e traduzir com fidelidade.",
        "conteudo_html": """
<p class="article-lead">Em quase todas as oficinas de escrita criativa ensina-se como falar, como estruturar diálogos e como descrever cenas. Quase ninguém ensina a virtude mais rara e necessária de um autor contemporâneo: a capacidade de calar a boca e escutar.</p>

<h3>A arrogância da autoria solitária</h3>
<p>Existe um mito romântico e ultrapassado de que o escritor é um gênio enclausurado em sua torre de marfim, inventando mundos a partir do próprio ego. Quando viajei pelo semiárido para compor 'Vozes do Sertão', percebi rapidamente que qualquer palavra minha seria pálida perto da poesia espontânea de uma agricultora que sobreviveu a quatro anos de estiagem sem perder o riso.</p>

<blockquote class="pull-quote">“O escritor não dá voz a ninguém. As pessoas já têm voz; o que lhes falta é o palco, a escuta e a recusa dos poderosos em tapar os ouvidos.”</blockquote>

<h3>Uma literatura descentralizada</h3>
<p>É por isso que plataformas abertas como o BookShelf são tão urgentes. Elas quebram o funil dos editores tradicionais que historicamente decidiram quem merecia e quem não merecia ter seu testemunho preservado. Toda memória importa. Todo relato sincero tem dignidade poética.</p>
""",
        "tags": ["Memória Oral", "Escuta Ativa", "Ética Literária", "Não-Ficção"],
        "curtidas": 312,
        "comentarios": [
            {
                "autor": "Beatriz Albuquerque",
                "foto": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=500&q=80",
                "data": "Há 1 semana",
                "texto": "Que texto comovente, Helena. A literatura sem escuta vira mero exercício de vaidade. Obrigada por nos lembrar de onde vem a matéria-prima do afeto.",
                "curtidas": 42
            }
        ]
    },
    {
        "id": 6,
        "titulo": "Além da donzela em perigo: a anatomia da adrenalina sob a ótica feminina",
        "subtitulo": "Mulheres que pilotam em alta velocidade, planejam estratégias sob fogo e sangram no asfalto não são exceção estética: são a realidade da coragem cotidiana.",
        "autor_nome": "Mariana Prado",
        "autor_foto": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=500&q=80",
        "autor_origem": "Belo Horizonte, MG",
        "categoria": "Crítica Cultural",
        "categoria_slug": "critica",
        "tempo_leitura": "5 min de leitura",
        "data_publicacao": "12 de Outubro de 2026",
        "resumo": "Durante anos fomos relegadas a ser a testemunha que grita no banco do carona. Quando escrevi meu livro autoral, a primeira regra foi: quem segura o volante sou eu.",
        "conteudo_html": """
<p class="article-lead">Se você abrir dez livros ou filmes de ação clássicos, em oito deles encontrará o mesmo roteiro previsível: a personagem feminina serve para ser resgatada, para chorar ao telefone ou para fornecer um pretexto moral que justifique a vingança do protagonista masculino. Cansei dessa fórmula aos quinze anos.</p>

<h3>Competência sem floreios</h3>
<p>Quando criei a protagonista de 'Alvo em Movimento: Rota 116', fiz questão de que ela fosse perita em traçado de curvas, mecânica pesada e tática de fuga defensiva. Não porque eu quisesse criar uma heroína invencível de quadrinhos, mas porque mulheres em funções de alta pressão tomam decisões pragmáticas e duras todos os dias sem esperar salva-vidas.</p>

<blockquote class="pull-quote">“Coragem não tem gênero. E a adrenalina é a mesma para quem sabe que hesitar na freada significa não chegar ao fim da estrada.”</blockquote>

<p>A nova literatura que construímos aqui no BookShelf tem espaço para mulheres que dominam o asfalto, a espada e a caneta. E não vamos pedir licença para acelerar.</p>
""",
        "tags": ["Representatividade", "Ação", "Personagens Femininas", "Ensaio"],
        "curtidas": 185,
        "comentarios": [
            {
                "autor": "Carlos Viana",
                "foto": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=500&q=80",
                "data": "Há 1 semana",
                "texto": "Perfeita colocação, Mariana. No treinamento tático real, precisão e controle emocional superam força bruta dez entre dez vezes.",
                "curtidas": 25
            }
        ]
    },
    {
        "id": 7,
        "titulo": "A tirania da perfeição nas redes e a libertadora beleza do vexame humano",
        "subtitulo": "Filtros e posts motivacionais criaram a ilusão de que errar é proibido. Na comédia e na vida real, são exatamente as nossas gafes que nos tornam inesquecíveis.",
        "autor_nome": "Clarice Montenegro",
        "autor_foto": "https://images.unsplash.com/photo-1580489944761-15a19d654956?auto=format&fit=crop&w=500&q=80",
        "autor_origem": "Recife, PE",
        "categoria": "Opinião & Sociedade",
        "categoria_slug": "opiniao",
        "tempo_leitura": "5 min de leitura",
        "data_publicacao": "08 de Outubro de 2026",
        "resumo": "Ninguém se apaixona por um currículo impecável ou por uma foto com iluminação de estúdio. Nós nos apaixonamos pela pessoa que derruba o guardanapo e ri de si mesma.",
        "conteudo_html": """
<p class="article-lead">Estamos vivendo na era mais engomada da história humana. Todo mundo tem uma opinião bem-formatada, uma rotina matinal impecável com suco verde às cinco da manhã e um conjunto de metas cumpridas antes do meio-dia. Se o leitor acreditar no que vê nas telas, achará que é o único ser desajustado do planeta Terra.</p>

<h3>O milagre do tropeço</h3>
<p>Como escritora de comédia, vivo à espreita das pequenas humilhações que todo mundo tenta varrer para baixo do tapete. A mensagem enviada para o grupo errado, a saia presa na porta do elevador, a tentativa desastrosa de impressionar o crush com um prato gourmet que terminou com o alarme de incêndio tocando.</p>

<blockquote class="pull-quote">“A perfeição é fria e afasta as pessoas. O vexame compartilhado com graça é a cola social mais resistente já inventada pela humanidade.”</blockquote>

<p>Em 'O Casamento da Minha Inimiga', usei e abusei do constrangimento como motor narrativo. E a resposta dos leitores foi unânime: 'Me senti aliviado de ver que a vida real também é cheia de docinhos amassados'. Que possamos tropeçar mais e nos julgar menos.</p>
""",
        "tags": ["Comportamento", "Comédia", "Redes Sociais", "Crônica"],
        "curtidas": 176,
        "comentarios": [
            {
                "autor": "Tiago Fontes",
                "foto": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=500&q=80",
                "data": "Há 2 semanas",
                "texto": "Clarice, você resumiu a tese de doutorado da minha vida! Se o vexame pagasse imposto, eu seria o maior contribuinte do país.",
                "curtidas": 38
            }
        ]
    },
    {
        "id": 8,
        "titulo": "Da utilidade secreta das ilusões: notas sobre a comédia moral da convivência",
        "subtitulo": "Se os homens despissem todas as suas vaidades na praça pública, a paz civil não duraria quinze minutos. Um elogio machadiano à conveniente hipocrisia das salas de visita.",
        "autor_nome": "Machado de Assis",
        "autor_foto": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cd/Machado_de_Assis_real.jpg/480px-Machado_de_Assis_real.jpg",
        "autor_origem": "Rio de Janeiro (1839 - 1908)",
        "categoria": "Ensaio Literário",
        "categoria_slug": "ensaio",
        "tempo_leitura": "6 min de leitura",
        "data_publicacao": "01 de Outubro de 2026",
        "resumo": "Uma reflexão cáustica e elegante sobre as convenções sociais, os elogios fingidos e o bálsamo necessário da vaidade para que a sociedade continue dançando suas quadrilhas.",
        "conteudo_html": """
<p class="article-lead">Costuma-se acusar a hipocrisia como o pior dos vícios humanos. Trata-se de uma ingratidão sem tamanho. Se cada cavalheiro dissesse ao seu vizinho o que realmente pensa do seu caráter, e se cada senhora expressasse em voz alta o que acha do penteado da amiga, o mundo se transformaria num campo de duelos sem trégua.</p>

<h3>O verniz da civilidade</h3>
<p>A ilusão mútua é o óleo que lubrifica as engrenagens pesadas da convivência. Fingimos que admiramos discursos enfadonhos para que outros finjam admirar os nossos; elogiamos a inteligência do anfitrião para que nos convidem novamente ao banquete. Esse comércio de pequenas mentiras não é maldade: é a caridade possível entre criaturas imperfeitas.</p>

<blockquote class="pull-quote">“A vaidade é o princípio de muitas boas ações que a virtude pura jamais teria a coragem ou a disposição de empreender.”</blockquote>

<p>Deixemos, pois, que os homens usem suas casacas e suas medalhas. O importante não é que sejam sinceros o tempo todo, mas que guardem a compostura necessária para que a comédia da vida prossiga com elegância e sem tiros de pistola.</p>
""",
        "tags": ["Ensaio Clássico", "Filosofia Moral", "Machado de Assis", "Ironia"],
        "curtidas": 410,
        "comentarios": [
            {
                "autor": "Eduardo Brandão",
                "foto": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=500&q=80",
                "data": "Há 3 semanas",
                "texto": "A ironia machadiana continua mais atual em 2026 do que quando foi escrita no século XIX. Um mestre absoluto que dissecou a alma humana.",
                "curtidas": 54
            }
        ]
    }
]


@app.route('/artigos')
def artigos():
    categoria_filtro = (request.args.get('categoria') or '').strip().lower()
    busca = (request.args.get('q') or '').strip().lower()

    artigos_base = ARTIGOS_MOCADOS
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM artigos")
        rows = cursor.fetchall()
        cursor.close()
        if rows:
            for r in rows:
                if 'id_artigo' in r:
                    r['id'] = r['id_artigo']
                if isinstance(r.get('tags_json'), str):
                    try:
                        r['tags'] = json.loads(r['tags_json'])
                    except Exception:
                        r['tags'] = []
                elif 'tags' not in r:
                    r['tags'] = []
                if isinstance(r.get('comentarios_json'), str):
                    try:
                        r['comentarios'] = json.loads(r['comentarios_json'])
                    except Exception:
                        r['comentarios'] = []
                elif 'comentarios' not in r:
                    r['comentarios'] = []
            artigos_base = rows
    except Exception:
        artigos_base = ARTIGOS_MOCADOS

    artigos_filtrados = artigos_base

    if categoria_filtro and categoria_filtro != 'todos':
        artigos_filtrados = [
            a for a in artigos_filtrados
            if a.get('categoria_slug', '').lower() == categoria_filtro
            or categoria_filtro in a.get('categoria', '').lower()
        ]

    if busca:
        artigos_filtrados = [
            a for a in artigos_filtrados
            if busca in a['titulo'].lower()
            or busca in (a.get('subtitulo') or '').lower()
            or busca in a['autor_nome'].lower()
            or busca in (a.get('resumo') or '').lower()
            or any(busca in t.lower() for t in a.get('tags', []))
        ]

    categorias_lista = [
        {'nome': 'Todos', 'slug': 'todos'},
        {'nome': 'Tecnologia & Escrita', 'slug': 'tecnologia'},
        {'nome': 'Crítica Cultural', 'slug': 'critica'},
        {'nome': 'Manifestos', 'slug': 'manifesto'},
        {'nome': 'Opinião & Sociedade', 'slug': 'opiniao'},
        {'nome': 'Processo Criativo', 'slug': 'processo'},
        {'nome': 'Ensaio Literário', 'slug': 'ensaio'}
    ]

    return render_template(
        'artigos.html',
        artigos=artigos_filtrados,
        categoria_ativa=categoria_filtro or 'todos',
        categorias=categorias_lista,
        busca=busca,
        total_artigos=len(artigos_base)
    )


@app.route('/artigo/<int:id_artigo>')
def detalhe_artigo(id_artigo):
    artigo = None
    for a in ARTIGOS_MOCADOS:
        if a['id'] == id_artigo:
            artigo = a
            break

    if not artigo:
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT * FROM artigos WHERE id_artigo = %s", (id_artigo,))
            row = cursor.fetchone()
            cursor.close()
            if row:
                row['id'] = row['id_artigo']
                if isinstance(row.get('tags_json'), str):
                    row['tags'] = json.loads(row['tags_json'])
                if isinstance(row.get('comentarios_json'), str):
                    row['comentarios'] = json.loads(row['comentarios_json'])
                artigo = row
        except Exception:
            pass

    if not artigo:
        flash("Artigo não encontrado.", "error")
        return redirect(url_for('artigos'))

    # Artigos relacionados sugeridos
    relacionados = [a for a in ARTIGOS_MOCADOS if a['id'] != artigo['id']][:3]

    return render_template('artigo_detalhe.html', artigo=artigo, relacionados=relacionados)


@app.route('/api/artigo/<int:id_artigo>/curtir', methods=['POST'])
def curtir_artigo(id_artigo):
    for a in ARTIGOS_MOCADOS:
        if a['id'] == id_artigo:
            a['curtidas'] = a.get('curtidas', 0) + 1
            return jsonify({'ok': True, 'curtidas': a['curtidas']})
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE artigos SET curtidas = curtidas + 1 WHERE id_artigo = %s", (id_artigo,))
        mysql.connection.commit()
        cursor.execute("SELECT curtidas FROM artigos WHERE id_artigo = %s", (id_artigo,))
        row = cursor.fetchone()
        cursor.close()
        curtidas = row['curtidas'] if row else 1
        return jsonify({'ok': True, 'curtidas': curtidas})
    except Exception:
        return jsonify({'ok': True, 'curtidas': 1})


@app.route('/api/artigo/<int:id_artigo>/comentar', methods=['POST'])
def comentar_artigo(id_artigo):
    dados = request.get_json(silent=True) or request.form
    texto = (dados.get('texto') or '').strip()
    if not texto:
        return jsonify({'ok': False, 'erro': 'O comentário não pode ficar vazio.'}), 400

    nome_autor = session.get('nome') or session.get('username') or 'Leitor Convidado'
    novo_comentario = {
        'autor': nome_autor,
        'foto': 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=500&q=80',
        'data': 'Agora mesmo',
        'texto': texto,
        'curtidas': 0
    }

    for a in ARTIGOS_MOCADOS:
        if a['id'] == id_artigo:
            a.setdefault('comentarios', []).insert(0, novo_comentario)
            break

    if request.is_json:
        return jsonify({'ok': True, 'comentario': novo_comentario})
    flash("Seu comentário foi publicado com sucesso no debate!", "success")
    return redirect(url_for('detalhe_artigo', id_artigo=id_artigo))


@app.route('/artigos/novo', methods=['POST'])
def novo_artigo():
    titulo = (request.form.get('titulo') or '').strip()
    subtitulo = (request.form.get('subtitulo') or '').strip()
    categoria = (request.form.get('categoria') or 'Opinião & Sociedade').strip()
    conteudo = (request.form.get('conteudo') or '').strip()

    if not titulo or not conteudo:
        flash("Título e conteúdo da opinião são obrigatórios.", "error")
        return redirect(url_for('artigos'))

    autor_nome = session.get('nome') or session.get('username') or 'Autor da Comunidade'
    novo_id = len(ARTIGOS_MOCADOS) + 1

    categoria_slug_map = {
        'Tecnologia & Escrita': 'tecnologia',
        'Crítica Cultural': 'critica',
        'Manifestos': 'manifesto',
        'Opinião & Sociedade': 'opiniao',
        'Processo Criativo': 'processo',
        'Ensaio Literário': 'ensaio'
    }

    artigo_obj = {
        'id': novo_id,
        'titulo': titulo,
        'subtitulo': subtitulo,
        'autor_nome': autor_nome,
        'autor_foto': 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=500&q=80',
        'autor_origem': 'Comunidade BookShelf',
        'categoria': categoria,
        'categoria_slug': categoria_slug_map.get(categoria, 'opiniao'),
        'tempo_leitura': '4 min de leitura',
        'data_publicacao': 'Hoje',
        'resumo': subtitulo or (conteudo[:180] + '...'),
        'conteudo_html': f"<p class='article-lead'>{conteudo.replace(chr(10), '<br>')}</p>",
        'tags': ["Opinião do Autor", "Comunidade", "Debate"],
        'curtidas': 1,
        'comentarios': []
    }

    ARTIGOS_MOCADOS.insert(0, artigo_obj)
    flash(f"Seu artigo de opinião '{titulo}' foi publicado no BookShelf!", "success")
    return redirect(url_for('detalhe_artigo', id_artigo=novo_id))


SUAS_LITERATURAS_MOCADAS = [
    {
        "id": 1,
        "titulo": "As Crônicas do Horizonte Vermelho",
        "autor": "Autor(a) BookShelf",
        "capa": "https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&w=600&q=80",
        "paginas_atuais": 120,
        "paginas_total": 300,
        "porcentagem": "100%",
        "avaliacao": 100,
        "tempo_leitura": "2h 45m",
        "curtido": False,
        "favorito": True,
        "likes": 342
    },
    {
        "id": 2,
        "titulo": "Dom Casmurro",
        "autor": "Machado de Assis",
        "capa": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&w=600&q=80",
        "paginas_atuais": 80,
        "paginas_total": 250,
        "porcentagem": "100%",
        "avaliacao": 100,
        "tempo_leitura": "1h 50m",
        "curtido": True,
        "favorito": True,
        "likes": 528
    },
    {
        "id": 3,
        "titulo": "O Cortiço",
        "autor": "Aluísio Azevedo",
        "capa": "https://images.unsplash.com/photo-1476275466078-4007374efbbe?auto=format&fit=crop&w=600&q=80",
        "paginas_atuais": 210,
        "paginas_total": 310,
        "porcentagem": "100%",
        "avaliacao": 100,
        "tempo_leitura": "3h 15m",
        "curtido": False,
        "favorito": False,
        "likes": 215
    },
    {
        "id": 4,
        "titulo": "Iracema",
        "autor": "José de Alencar",
        "capa": "https://images.unsplash.com/photo-1448375240586-882707db888b?auto=format&fit=crop&w=600&q=80",
        "paginas_atuais": 180,
        "paginas_total": 180,
        "porcentagem": "100%",
        "avaliacao": 100,
        "tempo_leitura": "2h 20m",
        "curtido": True,
        "favorito": False,
        "likes": 189
    },
    {
        "id": 5,
        "titulo": "Memórias Póstumas",
        "autor": "Machado de Assis",
        "capa": "https://images.unsplash.com/photo-1457369804613-52c61a468e7d?auto=format&fit=crop&w=600&q=80",
        "paginas_atuais": 45,
        "paginas_total": 220,
        "porcentagem": "100%",
        "avaliacao": 100,
        "tempo_leitura": "55m",
        "curtido": False,
        "favorito": True,
        "likes": 412
    },
    {
        "id": 6,
        "titulo": "Vidas Secas",
        "autor": "Graciliano Ramos",
        "capa": "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?auto=format&fit=crop&w=600&q=80",
        "paginas_atuais": 10,
        "paginas_total": 160,
        "porcentagem": "100%",
        "avaliacao": 100,
        "tempo_leitura": "35m",
        "curtido": False,
        "favorito": False,
        "likes": 304
    }
]


@app.route('/')
@app.route('/index')
@app.route('/home')
def index():
    busca = (request.args.get('q') or request.args.get('search') or '').strip()
    categoria = (request.args.get('category') or request.args.get('categoria') or 'todos').strip().lower()

    # Se o usuário escolheu uma categoria específica no dropdown, redireciona para a página correspondente
    if busca:
        if categoria == 'autores':
            return redirect(url_for('autores', q=busca))
        elif categoria == 'lancamentos':
            return redirect(url_for('lancamentos', q=busca))
        elif categoria == 'artigos':
            return redirect(url_for('artigos', q=busca))

    # 1. Filtrar Suas Literaturas (dados mocados da estante principal)
    suas_literaturas_filtradas = SUAS_LITERATURAS_MOCADAS
    if busca:
        busca_lower = busca.lower()
        suas_literaturas_filtradas = [
            l for l in SUAS_LITERATURAS_MOCADAS
            if busca_lower in l['titulo'].lower()
            or busca_lower in l['autor'].lower()
        ]

    # 2. Buscar Obras no Banco MySQL
    cursor = mysql.connection.cursor()
    if busca:
        query = "SELECT id_livro as id, titulo, autor, arquivo_epub as formato, 'Upload' as tamanho, capa_imagem FROM livros WHERE titulo LIKE %s OR autor LIKE %s"
        cursor.execute(query, (f"%{busca}%", f"%{busca}%"))
    else:
        query = "SELECT id_livro as id, titulo, autor, arquivo_epub as formato, 'Upload' as tamanho, capa_imagem FROM livros"
        cursor.execute(query)
    livros_db = list(cursor.fetchall() or [])
    cursor.close()

    # Complementar com obras mocadas de LANCAMENTOS_AUTORAIS
    tempos_mock = ["1h 15m", "2h 30m", "45m", "3h 05m", "1h 40m", "50m"]
    livros_mocados_extras = []
    for i, lanc in enumerate(LANCAMENTOS_AUTORAIS):
        match = True
        if busca:
            b_low = busca.lower()
            match = (
                b_low in lanc['titulo'].lower()
                or b_low in lanc['autor'].lower()
                or b_low in lanc.get('sinopse', '').lower()
                or b_low in lanc.get('genero_label', '').lower()
                or b_low in lanc.get('subtitulo', '').lower()
            )
        if match:
            livros_mocados_extras.append({
                "id": lanc['id'],
                "titulo": lanc['titulo'],
                "autor": lanc['autor'],
                "formato": "EPUB",
                "tamanho": f"{lanc.get('paginas', 200)} pág.",
                "capa_imagem": lanc.get('capa_imagem', ''),
                "tempo_leitura": lanc.get('tempo_leitura') or tempos_mock[i % len(tempos_mock)],
                "curtido": False,
                "favorito": False
            })

    if busca:
        livros_filtrados = livros_db + livros_mocados_extras
    else:
        for i, lv in enumerate(livros_db):
            if not lv.get('tempo_leitura'):
                lv['tempo_leitura'] = tempos_mock[i % len(tempos_mock)]
            if 'curtido' not in lv:
                lv['curtido'] = False
            if 'favorito' not in lv:
                lv['favorito'] = False
        livros_filtrados = livros_db + livros_mocados_extras[:3]

    # 3. Autores e Artigos mocados correspondentes à busca
    autores_encontrados = []
    artigos_encontrados = []
    if busca:
        b_low = busca.lower()
        autores_encontrados = [
            a for a in AUTORES_MOCADOS
            if b_low in a['nome'].lower() or any(b_low in l.get('titulo', '').lower() for l in a.get('livros', [])) or b_low in (a.get('origem') or '').lower()
        ][:4]
        artigos_encontrados = [
            art for art in ARTIGOS_MOCADOS
            if b_low in art['titulo'].lower() or b_low in art['autor_nome'].lower() or any(b_low in t.lower() for t in art.get('tags', []))
        ][:3]

    return render_template(
        'home.html',
        livros=livros_filtrados,
        suas_literaturas=suas_literaturas_filtradas,
        busca=busca,
        categoria_ativa=categoria,
        autores_encontrados=autores_encontrados,
        artigos_encontrados=artigos_encontrados
    )


@app.route('/descricao')
@app.route('/livro/<int:id_livro>')
def descricao_livro(id_livro=None):
    livro = None
    if id_livro is not None:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id_livro as id, titulo, autor, arquivo_epub as formato, capa_imagem FROM livros WHERE id_livro = %s", (id_livro,))
        livro = cursor.fetchone()
        cursor.close()
        if not livro:
            for s in SUAS_LITERATURAS_MOCADAS:
                if s['id'] == id_livro:
                    livro = {
                        "id": s['id'],
                        "titulo": s['titulo'],
                        "autor": s['autor'],
                        "formato": "EPUB",
                        "capa_imagem": s.get('capa')
                    }
                    break
        if not livro:
            for lanc in LANCAMENTOS_AUTORAIS:
                if lanc['id'] == id_livro:
                    livro = {
                        "id": lanc['id'],
                        "titulo": lanc['titulo'],
                        "autor": lanc['autor'],
                        "formato": "EPUB",
                        "capa_imagem": lanc.get('capa_imagem')
                    }
                    break
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
        usuario_input = (request.form.get('email') or '').strip()
        senha = request.form.get('senha')
        
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM usuario WHERE usuario = %s", (usuario_input,))
        user = cursor.fetchone()
        cursor.close()
        
        if user and check_password_hash(user['senha_hash'], senha):
            session['usuario_id'] = user['id_usuario']
            session['username'] = user['usuario']
            nome_cadastrado = (user.get('nome') or '').strip()
            # Se tiver nome cadastrado usa o nome, senão pega a parte antes do @ do email
            session['nome'] = nome_cadastrado if nome_cadastrado else user['usuario'].split('@')[0]
            flash(f"Bem-vindo(a) de volta, {session['nome']}!", "success")
            return redirect(url_for('perfil'))
        else:
            flash("Usuário ou senha incorretos.", "error")
            
    return render_template('cadastro_login.html')


@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = (request.form.get('nome') or '').strip()
        email = (request.form.get('email') or '').strip()
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
                "INSERT INTO usuario (nome, usuario, senha_hash, cpf) VALUES (%s, %s, %s, %s)",
                (nome, email, senha_hash, cpf)
            )
            mysql.connection.commit()
            cursor.close()
            
            flash("Cadastro realizado com sucesso! Faça login com suas credenciais.", "success")
            return redirect(url_for('login'))
            
    return render_template('cadastro_login.html')


@app.route('/biblioteca')
def biblioteca():
    busca = request.args.get('q', '') or request.args.get('search', '')
    categoria = request.args.get('category', '') or request.args.get('categoria', '')
    return redirect(url_for('index', q=busca, category=categoria))

@app.route('/perfil')
def perfil():
    if 'usuario_id' not in session:
        flash("Por favor, faça o login primeiro.", "error")
        return redirect(url_for('login'))
        
    busca = (request.args.get('q') or request.args.get('search') or '').strip()
    categoria = (request.args.get('category') or '').strip().lower()
    if busca and categoria == 'autores':
        return redirect(url_for('autores', q=busca))
    id_usuario = session['usuario_id']
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id_usuario, nome, usuario, cpf FROM usuario WHERE id_usuario = %s", (id_usuario,))
    db_user = cursor.fetchone()
    
    nome_exibicao = ""
    if db_user:
        nome_exibicao = (db_user.get('nome') or '').strip()
        if not nome_exibicao:
            nome_exibicao = db_user['usuario'].split('@')[0]
    if not nome_exibicao:
        nome_exibicao = session.get('nome') or "Escritor(a)"

    usuario_atual = {
        "nome": nome_exibicao,
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
    tempos_mock = ["1h 50m", "2h 15m", "40m", "3h 00m"]
    for i, lv in enumerate(livros_prateleira):
        if not lv.get('tempo_leitura'):
            lv['tempo_leitura'] = tempos_mock[i % len(tempos_mock)]
        if 'curtido' not in lv:
            lv['curtido'] = False
        if 'favorito' not in lv:
            lv['favorito'] = False

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
        autor_obra = session.get('nome') or session.get('username') or "Você (Autor Bookshelf)"
        cursor.execute(
            "INSERT INTO livros (titulo, arquivo_epub, autor, id_categoria) VALUES (%s, %s, %s, %s)",
            (titulo, 'EPUB', autor_obra, None)
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

def gerar_epub_de_modelo_grafica(caminho_destino, dados):
    import html as html_lib
    meta = dados.get('meta', {})
    titulo = (meta.get('titulo') or 'Livro sem Título').strip()
    subtitulo = (meta.get('subtitulo') or '').strip()
    autor = (meta.get('autor') or 'Autor Bookshelf').strip()
    editora = (meta.get('editora') or 'Editora BookShelf').strip()
    cidade = (meta.get('cidade') or 'Curitiba').strip()
    ano = (meta.get('ano') or '2026').strip()
    isbn = (meta.get('isbn') or '978-65-00-00000-0').strip()
    paginas = dados.get('paginas', [])

    def esc(val):
        return html_lib.escape(str(val or '')).replace('\n', '<br/>')

    capitulos_xhtml = []
    for idx, pag in enumerate(paginas):
        titulo_pag = (pag.get('titulo_exibicao') or pag.get('nome') or f'Página {idx + 1}').strip()
        conteudo_html = pag.get('html_formatado') or f"<p>{esc(pag.get('conteudo', ''))}</p>"
        xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <title>{html_lib.escape(titulo_pag)}</title>
</head>
<body>
  <h2>{html_lib.escape(titulo_pag)}</h2>
  {conteudo_html}
</body>
</html>"""
        capitulos_xhtml.append((f"pag_{idx + 1}.xhtml", titulo_pag, xhtml))

    if not capitulos_xhtml:
        capitulos_xhtml.append((
            "pag_1.xhtml",
            titulo,
            f'<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>{esc(titulo)}</title></head><body><h1>{esc(titulo)}</h1><p>{esc(subtitulo)}</p><p>{esc(autor)} — {esc(editora)}, {esc(cidade)} ({esc(ano)}) — ISBN {esc(isbn)}</p></body></html>'
        ))

    manifest_items = []
    spine_items = []
    nav_points = []
    for i, (fname, t_pag, _) in enumerate(capitulos_xhtml, start=1):
        item_id = f"item_{i}"
        manifest_items.append(f'    <item id="{item_id}" href="{fname}" media-type="application/xhtml+xml"/>')
        spine_items.append(f'    <itemref idref="{item_id}"/>')
        nav_points.append(f"""    <navPoint id="navPoint-{i}" playOrder="{i}">
      <navLabel><text>{html_lib.escape(t_pag)}</text></navLabel>
      <content src="{fname}"/>
    </navPoint>""")

    content_opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>{html_lib.escape(titulo)}</dc:title>
    <dc:creator>{html_lib.escape(autor)}</dc:creator>
    <dc:publisher>{html_lib.escape(editora)}</dc:publisher>
    <dc:language>pt-BR</dc:language>
    <dc:identifier id="BookId">{html_lib.escape(isbn)}</dc:identifier>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
{chr(10).join(manifest_items)}
  </manifest>
  <spine toc="ncx">
{chr(10).join(spine_items)}
  </spine>
</package>"""

    toc_ncx = f"""<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{html_lib.escape(isbn)}"/>
  </head>
  <docTitle><text>{html_lib.escape(titulo)}</text></docTitle>
  <navMap>
{chr(10).join(nav_points)}
  </navMap>
</ncx>"""

    container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""

    with zipfile.ZipFile(caminho_destino, 'w') as zf:
        zf.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
        zf.writestr('META-INF/container.xml', container_xml, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr('OEBPS/content.opf', content_opf, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr('OEBPS/toc.ncx', toc_ncx, compress_type=zipfile.ZIP_DEFLATED)
        for fname, _, xhtml in capitulos_xhtml:
            zf.writestr(f'OEBPS/{fname}', xhtml, compress_type=zipfile.ZIP_DEFLATED)


@app.route('/modelo-grafica')
@app.route('/escrever')
def modelo_grafica():
    dados_salvos = None
    nome_usuario = session.get('nome') or session.get('username', 'Autor(a) BookShelf')
    if 'usuario_id' in session:
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT dados_json FROM modelo_grafica WHERE id_usuario = %s",
                (session['usuario_id'],)
            )
            row = cursor.fetchone()
            cursor.close()
            if row and row.get('dados_json'):
                dados_salvos = row['dados_json']
        except Exception:
            dados_salvos = None
    return render_template(
        'modelo_grafica.html',
        dados_salvos=dados_salvos,
        nome_usuario=nome_usuario
    )


@app.route('/api/modelo-grafica/salvar', methods=['POST'])
def salvar_modelo_grafica():
    dados = request.get_json(silent=True) or {}
    if 'usuario_id' not in session:
        return jsonify({
            'ok': True,
            'local_only': True,
            'mensagem': 'Modelo salvo localmente no navegador (faça login para salvar também no MySQL).'
        })
    meta = dados.get('meta', {})
    titulo = (meta.get('titulo') or 'Livro em Elaboração').strip()[:255]
    autor = (meta.get('autor') or session.get('nome') or session.get('username', 'Autor')).strip()[:255]
    dados_str = json.dumps(dados, ensure_ascii=False)

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id_modelo FROM modelo_grafica WHERE id_usuario = %s", (session['usuario_id'],))
    existente = cursor.fetchone()
    if existente:
        cursor.execute(
            "UPDATE modelo_grafica SET titulo = %s, autor = %s, dados_json = %s WHERE id_usuario = %s",
            (titulo, autor, dados_str, session['usuario_id'])
        )
    else:
        cursor.execute(
            "INSERT INTO modelo_grafica (id_usuario, titulo, autor, dados_json) VALUES (%s, %s, %s, %s)",
            (session['usuario_id'], titulo, autor, dados_str)
        )
    mysql.connection.commit()
    cursor.close()
    return jsonify({'ok': True, 'mensagem': 'Todas as páginas do modelo foram salvas no banco de dados com sucesso!'})


@app.route('/api/modelo-grafica/publicar', methods=['POST'])
def publicar_modelo_grafica():
    dados = request.get_json(silent=True) or {}
    meta = dados.get('meta', {})
    titulo = (meta.get('titulo') or '').strip()[:255]
    autor = (meta.get('autor') or session.get('nome') or session.get('username') or 'Autor BookShelf').strip()[:255]

    if not titulo:
        return jsonify({'ok': False, 'erro': 'Preencha o título do livro na Capa / Folha de Rosto antes de publicar.'}), 400

    cursor = mysql.connection.cursor()
    cursor.execute(
        "INSERT INTO livros (titulo, arquivo_epub, autor, id_categoria) VALUES (%s, %s, %s, %s)",
        (titulo, 'EPUB', autor, None)
    )
    id_novo_livro = cursor.lastrowid
    destino = os.path.join(UPLOAD_FOLDER, f'{id_novo_livro}.epub')
    gerar_epub_de_modelo_grafica(destino, dados)

    if 'usuario_id' in session:
        cursor.execute(
            "INSERT INTO biblioteca_usuario (id_usuario, id_livro, progresso) VALUES (%s, %s, %s)",
            (session['usuario_id'], id_novo_livro, 0.00)
        )
    mysql.connection.commit()
    cursor.close()
    return jsonify({
        'ok': True,
        'id_livro': id_novo_livro,
        'url_leitura': url_for('ler_livro', id_livro=id_novo_livro),
        'mensagem': f"Livro '{titulo}' publicado com sucesso a partir do modelo de gráfica!"
    })


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# GATILHO: Executa a criação das tabelas antes de ligar o servidor de fato
inicializar_banco()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
