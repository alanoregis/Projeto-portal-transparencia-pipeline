"""
Orquestrador Principal do Pipeline de Engenharia de Dados:
Portal da Transparência (dlthub + dbt-duckdb + DuckDB)
Arquitetura Medalhão: Bronze -> Silver -> Gold

"""
import os
import sys
import subprocess
import time
from pathlib import Path
import duckdb

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON_EXE = PROJECT_ROOT / ".venv" / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
DBT_EXE = PROJECT_ROOT / ".venv" / ("Scripts" if os.name == "nt" else "bin") / ("dbt.exe" if os.name == "nt" else "dbt")
DB_PATH = PROJECT_ROOT / os.getenv("DUCKDB_PATH", "data/portal_transparencia.duckdb")

def log_step(step_number: int, title: str):
    print("\n" + "=" * 70)
    print(f" ETAPA {step_number}: {title}")
    print("=" * 70)

def run_command(cmd: list, cwd: Path = PROJECT_ROOT, status_hint: str = ""):
    """Executa um comando e monitora seu código de retorno."""
    cmd_str = " ".join(str(c) for c in cmd)
    print(f"Executando: {cmd_str}")
    if status_hint:
        print(f" {status_hint}")
    start = time.time()
    try:
        result = subprocess.run(cmd, cwd=str(cwd))
    except KeyboardInterrupt:
        print("\n Execucao cancelada pelo usuario (Ctrl+C).")
        sys.exit(130)
    duration = time.time() - start

    if result.returncode != 0:
        print(f" Erro na execucao do comando (codigo {result.returncode}) apos {duration:.1f}s")
        sys.exit(result.returncode)
    else:
        print(f" Concluido com sucesso em {duration:.1f}s")

def print_gold_summary():
    """Exibe resumo das tabelas Gold prontas para consumo no Power BI."""
    if not DB_PATH.exists():
        print("\n Banco DuckDB nao encontrado. Execute a ingestion primeiro.")
        return

    con = duckdb.connet(str(DB_PATH), read_only=True)
    try:
        print("\n" + "-" * 70)
        print(" CAMADA GOLD — STAR SCHEMA (PRONTO PARA POWER BI):")
        print("-" * 70)

        # Tabela Fato
        fato_tables = [
            ("gold.gold_fct_gastos_cartao", "Fato principal - gastos com Z-score e nivel de alerta"),
        ]

        # Dimensoes
        dim_tables = [
            ("gold.gold_dim_data",         "Dimensao calendario 2023-2026"),
            ("gold.gold_dim_orgaos",        "Dimensao de orgaos superiores e unidades gestoras"),
            ("gold.gold_dim_favorecidos",   "Dimensao de favorecidos"),
            ("gold.gold_dim_portadores",    "Dimensao de portadores"),
            ("gold.gold_dim_nivel_alerta",  "Dimensao de alertas: NORMAL / MODERADO / CRITICO"),
        ]

        print("\n  FATO:")
        for table, desc in fato_tables:
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"   {table:<38} {count:>6} registros | {desc}")

        print("\n  DIMENSOES:")
        for table, desc in dim_tables:
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"   {table:<38} {count:>6} registros | {desc}")
        print("-" * 70)

    except Exception as e:
        print(f" Nao foi possivel consultar o DuckDB {e}")
    finally:
        con.close()

def main():
    start_total = time.time()
    print("\n" + "#" * 70)
    print(" PIPELINE DE ENGENHARIA DE DADOS - PORTAL DA TRANSPARENCIA (CGU)")
    print("   Arquitetura Medalhao: Ingestion dlt -> DuckDB -> Modelagem dbt")
    print("#" * 70)

    # Etapa 1 - Ingestion com dlt
    log_step(1, "Ingestao de Dados com dlthub (Camada Bronze)")
    run_command(
        [str(PYTHON_EXE), "ingestion/pipeline_transparencia.py"],
        status_hint="Extraindo dados da API CGU e carregando no DUCKDB (bronze)..."
    )

    # Etapa 2 - Transformacao com dbt (Silver + Gold)
    log_step(2, "Transformacao com dbt-duckdb (Silver + Gold)")
    run_command(
        [str(DBT_EXE), "run",
         "--project-dir", "dbt_transparencia",
         "--profiles-dir", "dbt_tranparencia"],
         status_hint="Compilando e executando modelos Silver e Gold..."
    )

    # Etapa 3 - Testes de qualidade
    log_step(3, "Validacao e Teste de Qualidade (dbt test)")
    run_command(
        [str(DBT_EXE), "test",
         "--project-dir", "dbt_transparencia",
         "--profiles-dir", "dbt_transparencia"],
        status_hint="Executando testes de unicidade, not_null e integridade referencial..."
    )

    # Etapa 4 - Resumo Gold
    print_gold_summary()

    total_duration = time.time() - start_total
    print("\n" + "#" * 70)
    print(f" PIPELINE EXECUTADO COM SUCESSO EM {total_duration:.1f} SEGUNDOS!")
    print(f" Banco DuckDB disponivel em: {DB_PATH}")
    print("#" * 70 + "\n")

if __name__ == "__main__":
    main()