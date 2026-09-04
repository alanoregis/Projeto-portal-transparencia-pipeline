import os
import requests
import duckdb
import subprocess
from dotenv import load_dotenv

# 1. Configurações Iniciais
load_dotenv()
DB_PATH = os.getenv("DB_PATH", "transparencia.duckdb")
DATA_DIR = "data"
CSV_FILENAME = "despesas_cpgf.csv"
CSV_PATH = os.path.join(DATA_DIR, CSV_FILENAME)

# (A URL abaixo é um exemplo didático para baixar um CSV de dados abertos. 
# Caso o projeto original use outro link ou API, adaptaremos depois)
URL_DADOS = "https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/cpgf/202301_CPGF.csv"

def extract_data():
    """Baixa os dados brutos e salva localmente."""
    print("Iniciando extração de dados...")
    os.makedirs(DATA_DIR, exist_ok=True)
    
    if not os.path.exists(CSV_PATH):
        response = requests.get(URL_DADOS, stream=True)
        response.encoding = 'latin-1' # Padrão comum do Governo Federal
        
        with open(CSV_PATH, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        print(f"Download concluído: {CSV_PATH}")
    else:
        print(f"Arquivo já existe: {CSV_PATH}")

def load_to_duckdb():
    """Carrega o CSV bruto para o DuckDB (Camada Bronze)."""
    print("Carregando dados para o DuckDB...")
    conn = duckdb.connect(DB_PATH)
    
    # Cria um schema isolado para os dados brutos
    conn.execute("CREATE SCHEMA IF NOT EXISTS bronze;")
    
    # Ingestão direta do CSV para a tabela
    # O auto_detect do DuckDB tenta inferir os tipos de dados
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS bronze.cpgf_raw AS 
        SELECT * FROM read_csv_auto('{CSV_PATH}', encoding='latin-1', header=True, normalize_names=True);
    """)
    
    print("Dados carregados com sucesso no schema 'bronze'!")
    conn.close()

if __name__ == "__main__":
    extract_data()
    load_to_duckdb()
    # A chamada para o dbt será adicionada aqui nos próximos passos