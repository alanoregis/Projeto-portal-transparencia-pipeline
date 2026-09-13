"""
Orquestrador Principal do Pipeline de Engenharia de Dados:
Portal da Transparência (dlthub + dbt-sqlserver + Azure SQL Database)
Arquitetura Medalhão: Bronze -> Silver -> Gold (Star Schema)
"""

import os
import sys
import subprocess
import time
from pathlib import Path
import pyodbc
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

# Detecta dinamicamente se está rodando local (.venv) ou dentro de um Container Docker Linux (/usr/local/bin)
def get_executable(name: str) -> str:
    venv_path = PROJECT_ROOT / ".venv" / ("Scripts" if os.name == "nt" else "bin") / (f"{name}.exe" if os.name == "nt" else name)
    if venv_path.exists():
        return str(venv_path)
    return name  # Usa o binário global do PATH no container Docker

PYTHON_EXE = get_executable("python")
DBT_EXE = get_executable("dbt")


def log_step(step_number: int, title: str):
    print("\n" + "=" * 70)
    print(f"🚀 ETAPA {step_number}: {title}")
    print("=" * 70)


def run_command(cmd: list, cwd: Path = PROJECT_ROOT, status_hint: str = ""):
    """Executa um comando e monitora seu código de retorno."""
    cmd_str = " ".join(str(c) for c in cmd)
    print(f"Executando: {cmd_str}")
    if status_hint:
        print(f"⏳ {status_hint}")
    start = time.time()
    try:
        result = subprocess.run(cmd, cwd=str(cwd))
    except KeyboardInterrupt:
        print("\n⚠️ Execução cancelada pelo usuário (Ctrl+C).")
        sys.exit(130)
    duration = time.time() - start

    if result.returncode != 0:
        print(f"❌ Erro na execução do comando (código {result.returncode}) após {duration:.1f}s")
        sys.exit(result.returncode)
    else:
        print(f"✅ Concluído com sucesso em {duration:.1f}s")


def print_gold_summary():
    """Exibe resumo das tabelas Gold prontas para consumo no Power BI via Azure SQL."""
    server = os.getenv("AZURE_SQL_SERVER")
    database = os.getenv("AZURE_SQL_DATABASE")
    user = os.getenv("AZURE_SQL_USER")
    password = os.getenv("AZURE_SQL_PASSWORD")
    driver = os.getenv("AZURE_SQL_DRIVER", "ODBC Driver 17 for SQL Server")

    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )

    try:
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            print("\n" + "-" * 70)
            print("🥇 CAMADA GOLD — STAR SCHEMA (AZURE SQL DATABASE - PRONTO PARA POWER BI):")
            print("-" * 70)

            # Tabela fato
            fato_tables = [
                ("gold.gold_fct_gastos_cartao", "Fato principal — gastos com Z-score e nível de alerta"),
            ]

            # Dimensões
            dim_tables = [
                ("gold.gold_dim_data",         "Dimensão calendário 2023-2026 + Unknown Member"),
                ("gold.gold_dim_orgaos",        "Dimensão de órgãos superiores e unidades gestoras"),
                ("gold.gold_dim_favorecidos",   "Dimensão de favorecidos (grão por marca/nome)"),
                ("gold.gold_dim_portadores",    "Dimensão de portadores do cartão"),
                ("gold.gold_dim_nivel_alerta",  "Dimensão de alertas: NORMAL / MODERADO / CRITICO"),
            ]

            print("\n📊 FATO:")
            for table, desc in fato_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   • {table:<32} ➔ {count:>6} registros | {desc}")

            print("\n📐 DIMENSÕES:")
            for table, desc in dim_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   • {table:<32} ➔ {count:>6} registros | {desc}")

            print("-" * 70)

    except Exception as e:
        print(f"⚠️ Não foi possível consultar o resumo do Azure SQL: {e}")


def main():
    start_total = time.time()
    print("\n" + "#" * 70)
    print("🏛️  PIPELINE DE ENGENHARIA DE DADOS - PORTAL DA TRANSPARÊNCIA (CGU)")
    print("    Arquitetura Medalhão: Ingestão dlt -> Azure SQL Database -> dbt")
    print("#" * 70)

    # Etapa 1 — Ingestão com dlt
    log_step(1, "Ingestão de Dados com dlthub (Camada Bronze no Azure SQL)")
    run_command(
        [str(PYTHON_EXE), "ingestion/pipeline_transparencia.py"],
        status_hint="Extraindo dados da API CGU e carregando no Azure SQL (bronze)..."
    )

    # Etapa 2 — Transformação com dbt (Silver + Gold)
    log_step(2, "Transformação e Modelagem com dbt-sqlserver (Silver + Gold)")
    run_command(
        [str(DBT_EXE), "run",
         "--project-dir", "dbt_transparencia",
         "--profiles-dir", "dbt_transparencia"],
        status_hint="Compilando e executando modelos Silver e Gold..."
    )

    # Etapa 3 — Testes de qualidade
    log_step(3, "Validação e Testes de Qualidade de Dados (dbt test)")
    run_command(
        [str(DBT_EXE), "test",
         "--project-dir", "dbt_transparencia",
         "--profiles-dir", "dbt_transparencia"],
        status_hint="Executando testes de integridade referencial, unicidade e não-nulos..."
    )

    # Etapa 4 — Resumo Gold
    print_gold_summary()

    total_duration = time.time() - start_total
    print("\n" + "#" * 70)
    print(f"🎉 PIPELINE EXECUTADO COM SUCESSO EM {total_duration:.1f} SEGUNDOS!")
    print(f"💾 Dados prontos no Azure SQL Database: {os.getenv('AZURE_SQL_DATABASE')}")
    print("#" * 70 + "\n")


if __name__ == "__main__":
    main()