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
        result = subprocess.run(cmd, swd=str(cwd))
    except KeyboardInterrupt:
        print("\n Execucao cancelada pelo usuario (Ctrl+C).")
        sys.exit(130)
    duration = time.time() - start

    if result.returncode != 0:
        print(f" Erro na execucao do comando (codigo {result.returncode}) apos {duration:.1f}s")
        sys.exit(result.returncode)
    else:
        print(f" Concluido com sucesso em {duration:.1f}s")