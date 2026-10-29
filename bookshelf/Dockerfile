# 1. Usa uma imagem oficial do Python estável e leve
FROM python:3.11-slim

# 2. Instala dependências do sistema necessárias para o MySQL
# (Essa parte quase nunca muda, então o Docker vai pular ela direto usando cache)
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 3. Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# 4. PASSO DA VELOCIDADE: Instala as bibliotecas ANTES de copiar o seu código
# Como as versões não mudam toda hora, o Docker salva isso no cache.
RUN pip install --no-cache-dir Flask==3.0.3 Flask-MySQLdb==2.0.0 cryptography==43.0.1 Werkzeug

# 5. Só agora copia o restante do código do seu projeto
# Quando você alterar o app.py na escola, o Docker começa a trabalhar a partir DAQUI,
# ignorando o download das bibliotecas acima porque já estão salvas!
COPY . .

# 6. Informa a porta que o Flask vai expor
EXPOSE 5000

# 7. Comando para rodar a aplicação
CMD ["python", "app.py"]
