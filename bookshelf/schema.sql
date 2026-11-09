-- ====================================================================
-- BANCO DE DADOS OFICIAL BOOKSHELF (MySQL 8.0+)
-- Arquivo: schema.sql
-- ====================================================================

-- 1. Criação do Banco de Dados
CREATE DATABASE IF NOT EXISTS `epub` 
  DEFAULT CHARACTER SET utf8mb4 
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `epub`;

-- 2. Tabela de Usuários
CREATE TABLE IF NOT EXISTS `usuario` (
  `id_usuario` INT AUTO_INCREMENT PRIMARY KEY,
  `nome` VARCHAR(255),
  `usuario` VARCHAR(255) NOT NULL UNIQUE,
  `senha_hash` VARCHAR(255) NOT NULL,
  `cpf` VARCHAR(14) NOT NULL UNIQUE,
  `bio` TEXT DEFAULT NULL,
  `generos_favoritos` TEXT DEFAULT NULL,
  `interesses` TEXT DEFAULT NULL,
  `autores_favoritos` TEXT DEFAULT NULL,
  `criado_em` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Tabela de Livros da Biblioteca Geral
CREATE TABLE IF NOT EXISTS `livros` (
  `id_livro` INT AUTO_INCREMENT PRIMARY KEY,
  `titulo` VARCHAR(255) NOT NULL,
  `autor` VARCHAR(255),
  `arquivo_epub` VARCHAR(10) DEFAULT 'EPUB',
  `id_categoria` INT DEFAULT NULL,
  `capa_imagem` VARCHAR(500) DEFAULT NULL,
  `criado_em` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Tabela de Relacionamento: Biblioteca do Usuário (Prateleira e Progresso)
CREATE TABLE IF NOT EXISTS `biblioteca_usuario` (
  `id_usuario` INT NOT NULL,
  `id_livro` INT NOT NULL,
  `progresso` DECIMAL(5,2) DEFAULT 0.00,
  `atualizado_em` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_usuario`, `id_livro`),
  CONSTRAINT `fk_bib_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`id_usuario`) ON DELETE CASCADE,
  CONSTRAINT `fk_bib_livro` FOREIGN KEY (`id_livro`) REFERENCES `livros` (`id_livro`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Tabela do Modelo de Gráfica (Editor de Livros A4 do Autor)
CREATE TABLE IF NOT EXISTS `modelo_grafica` (
  `id_modelo` INT AUTO_INCREMENT PRIMARY KEY,
  `id_usuario` INT UNIQUE,
  `titulo` VARCHAR(255),
  `autor` VARCHAR(255),
  `dados_json` LONGTEXT,
  `atualizado_em` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_modelo_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`id_usuario`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Tabela de Lançamentos de Própria Autoria
CREATE TABLE IF NOT EXISTS `lancamentos_autorais` (
  `id_lancamento` INT AUTO_INCREMENT PRIMARY KEY,
  `titulo` VARCHAR(255) NOT NULL,
  `subtitulo` VARCHAR(255),
  `autor` VARCHAR(255) NOT NULL,
  `autor_cidade` VARCHAR(100),
  `autor_bio` TEXT,
  `genero` VARCHAR(50) NOT NULL,
  `genero_label` VARCHAR(50) NOT NULL,
  `cor_tema` VARCHAR(20) DEFAULT '#5E0B15',
  `capa_imagem` VARCHAR(500) DEFAULT NULL,
  `ano` INT DEFAULT 2026,
  `data_lancamento` VARCHAR(20),
  `paginas` INT DEFAULT 200,
  `tempo_leitura` VARCHAR(50),
  `avaliacao` DECIMAL(3,1) DEFAULT 5.0,
  `total_avaliacoes` INT DEFAULT 0,
  `formato` VARCHAR(50) DEFAULT 'EPUB Digital',
  `sinopse` TEXT,
  `nota_autor` TEXT,
  `badges_json` TEXT,
  `criado_em` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_genero` (`genero`),
  INDEX `idx_autor` (`autor`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Tabela de Autores
CREATE TABLE IF NOT EXISTS `autores` (
  `id_autor` INT AUTO_INCREMENT PRIMARY KEY,
  `nome` VARCHAR(255) NOT NULL,
  `tipo` VARCHAR(50) NOT NULL,
  `tipo_badge` VARCHAR(100) NOT NULL,
  `foto` VARCHAR(500),
  `origem` VARCHAR(100),
  `bio_curta` TEXT,
  `bio_completa` LONGTEXT,
  `generos_json` TEXT,
  `livros_json` LONGTEXT,
  `total_leitores` VARCHAR(50) DEFAULT '1.2k',
  `total_livros` INT DEFAULT 1,
  `citacao` TEXT,
  `criado_em` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_autor_tipo` (`tipo`),
  INDEX `idx_autor_nome` (`nome`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. Tabela de Artigos de Opinião e Ensaios Literários
CREATE TABLE IF NOT EXISTS `artigos` (
  `id_artigo` INT AUTO_INCREMENT PRIMARY KEY,
  `titulo` VARCHAR(255) NOT NULL,
  `subtitulo` VARCHAR(255),
  `autor_nome` VARCHAR(255) NOT NULL,
  `autor_foto` VARCHAR(500),
  `autor_origem` VARCHAR(100),
  `categoria` VARCHAR(100) NOT NULL,
  `tempo_leitura` VARCHAR(50) DEFAULT '5 min de leitura',
  `data_publicacao` VARCHAR(50),
  `resumo` TEXT,
  `conteudo_html` LONGTEXT NOT NULL,
  `tags_json` TEXT,
  `curtidas` INT DEFAULT 0,
  `comentarios_json` LONGTEXT,
  `criado_em` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_artigo_cat` (`categoria`),
  INDEX `idx_artigo_autor` (`autor_nome`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ====================================================================
-- CARGA INICIAL (SEED) DE LIVROS PADRÃO
-- ====================================================================
INSERT INTO `livros` (`id_livro`, `titulo`, `autor`, `arquivo_epub`, `id_categoria`)
VALUES 
  (1, '5minutos', 'José de Alencar', 'EPUB', NULL),
  (2, 'A Dádiva do Lobo', 'Anne Rice', 'EPUB', NULL)
ON DUPLICATE KEY UPDATE `titulo` = VALUES(`titulo`), `autor` = VALUES(`autor`);
