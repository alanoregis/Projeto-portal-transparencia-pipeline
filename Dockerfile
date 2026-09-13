# Imagem base oficial do Python (Debian Slim - leve e segura)
FROM python:3.11-slim

# Evita que o Python gere arquivos .pyc e força flush imediato dos prints
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Define diretório de trabalho dentro do container
WORKDIR /app

# Instala dependências do sistema e o Microsoft ODBC Driver 17 for SQL Server para Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg2 \
    apt-transport-https \
    ca-certificates \
    build-essential \
    unixodbc \
    unixodbc-dev \
    && curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copia os arquivos de dependências
COPY requirements.txt .

# Instala as bibliotecas Python
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir pyodbc sqlalchemy "dlt[sql_database]" dbt-sqlserver

# Copia todo o código do projeto para o container
COPY . .

# Garante que as dependências do dbt (dbt_utils) estejam instaladas
RUN cd dbt_transparencia && dbt deps --profiles-dir .

# Comando padrão de execução do container: rodar o orquestrador principal
CMD ["python", "run_pipeline.py"]