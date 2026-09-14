"""
Pipeline de Ingestão com dlthub (dlt) -> DuckDB (Camada Bronze).
Este script orquestra a extração da API do Portal da Transparência (ou modo amostra)
e o carregamento resiliente no DuckDB sob o schema 'bronze'.

"""

import os
import sys
import logging
from pathlib import Path
from typing import Generator, Dict, Any

from dotenv import load_dotenv
import dlt
import urllib.parse
import time
import pyodbc
from dlt.pipeline.exceptions import PipelineStepFailed

# Adiciona a raiz do projeto ao sys.path para garantir os imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.cgu_client import CGUClient
from ingestion.sample_data import get_sample_cartoes

# Carrega variáveis do arquivo .env
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)


@dlt.resource(
    name="cartoes_pagamento",
    write_disposition="replace",
    primary_key="id",
)
def cartoes_pagamento_resource() -> Generator[Dict[str, Any], None, None]:
    """
    Recurso dlt para extrair dados de Cartões de Pagamento (CPGF).
    Detecta automaticamente se deve usar a API real da CGU ou dados de amostra.
    """

    mode = os.getenv("INGESTION_MODE", "sample").strip().lower()
    api_key = os.getenv("CGU_API_KEY", "").strip()

    if mode == "api":
        if not api_key:
            logger.warning(
                "Modo 'api' configurado, mas CGU_API_KEY está vazia! "
                "Alternando automaticamente para modo 'sample' para garantir a execução."
            )

            data = get_sample_cartoes()

            for record in data:
                yield record

            return

        inicio = os.getenv(
            "EXTRACT_MES_EXTRATO_INICIO",
            "01/2026"
        ).strip()

        fim = os.getenv(
            "EXTRACT_MES_EXTRATO_FIM",
            "07/2026"
        ).strip()

        max_pages = int(
            os.getenv(
                "MAX_PAGES_PER_MONTH",
                "2"
            )
        )

        client = CGUClient(api_key=api_key)

        yield from client.get_cartoes_pagamento(
            mes_extrato_inicio=inicio,
            mes_extrato_fim=fim,
            max_pages=max_pages,
        )

    else:
        logger.info(
            "Executando ingestão em modo 'sample' (dados de amostra)..."
        )

        data = get_sample_cartoes()

        for record in data:
            yield record


@dlt.source(name="portal_transparencia")
def transparencia_source():
    """Fonte dlt agrupando recursos do Portal da Transparência."""
    return cartoes_pagamento_resource


def is_azure_transient_error(
    exc: Exception,
    error_codes: tuple[str, ...],
) -> bool:
    """
    Percorre a cadeia de exceções procurando códigos de erro
    transitórios do Azure SQL.

    Isso evita depender exclusivamente de exc.__cause__,
    já que o dlt pode encapsular a exceção original.
    """

    current = exc

    while current:
        if any(code in str(current) for code in error_codes):
            return True

        current = current.__cause__ or current.__context__

    return False


def run_ingestion(
    max_retries: int = 4,
    backoff_factor: float = 2.0,
):
    """
    Executa o pipeline dlt carregando os dados brutos
    no Azure SQL Database (Schema Bronze).

    Possui retry específico para o erro 40613,
    comum quando o Azure SQL Serverless está em auto-pause
    e precisa realizar o auto-resume.
    """

    logger.info(
        "=== Iniciando Pipeline de Ingestão com dlt -> Azure SQL ==="
    )

    server = os.getenv("AZURE_SQL_SERVER", "").strip()
    database = os.getenv("AZURE_SQL_DATABASE", "").strip()
    user = os.getenv("AZURE_SQL_USER", "").strip()
    password = os.getenv("AZURE_SQL_PASSWORD", "").strip()

    driver = os.getenv(
        "AZURE_SQL_DRIVER",
        "ODBC Driver 17 for SQL Server"
    ).strip()

    if not server or not database or not user or not password:
        raise ValueError(
            f"Credenciais do Azure SQL incompletas! "
            f"server='{server}', database='{database}', user='{user}'"
        )

    # Codifica usuário e senha caso tenham caracteres especiais
    user_encoded = urllib.parse.quote_plus(user)
    pwd_encoded = urllib.parse.quote_plus(password)
    driver_encoded = urllib.parse.quote_plus(driver)

    # URL padrão SQLAlchemy para MSSQL com pyodbc
    # Connect Timeout de 60s para dar tempo do Azure SQL Serverless
    # realizar o auto-resume.
    connection_url = (
        f"mssql+pyodbc://{user_encoded}:{pwd_encoded}@{server}:1433/{database}"
        f"?driver={driver_encoded}"
        f"&Encrypt=yes"
        f"&TrustServerCertificate=no"
        f"&Connect+Timeout=60"
    )

    # Configura o pipeline dlt com destino MSSQL
    pipeline = dlt.pipeline(
        pipeline_name="transparencia_azure",
        destination=dlt.destinations.mssql(
            credentials=connection_url
        ),
        dataset_name="bronze",
    )

    logger.info(
        f"Destino configurado: Azure SQL Database "
        f"[{database}] no schema [bronze]"
    )

    for attempt in range(1, max_retries + 1):

        try:
            logger.info(
                f"Executando tentativa {attempt}/{max_retries}..."
            )

            load_info = pipeline.run(
                transparencia_source()
            )

            logger.info(
                "=== Ingestão dlt Concluída com Sucesso! ==="
            )

            logger.info(
                f"Informações de Carga:\n{load_info}"
            )

            return load_info

        except PipelineStepFailed as exc:

            # 40613 = Azure SQL Database indisponível
            # normalmente relacionado ao auto-pause/auto-resume
            banco_pausado = is_azure_transient_error(
                exc,
                ("40613",)
            )

            if banco_pausado and attempt < max_retries:

                # 10s -> 20s -> 40s
                sleep_time = 10 * (
                    backoff_factor ** (attempt - 1)
                )

                logger.warning(
                    f"Azure SQL retornou erro 40613 "
                    f"(possível auto-pause/auto-resume). "
                    f"Aguardando {sleep_time:.0f}s antes "
                    f"da tentativa {attempt + 1}/{max_retries}..."
                )

                time.sleep(sleep_time)

                continue

            if banco_pausado:

                logger.error(
                    f"Falha definitiva após {max_retries} tentativas: "
                    f"Azure SQL não retomou a tempo. {exc}"
                )

            else:

                logger.error(
                    "Falha no pipeline dlt que não parece estar "
                    f"relacionada ao auto-pause do Azure SQL: {exc}"
                )

            raise


if __name__ == "__main__":
    run_ingestion()