"""
Pipeline de Ingestão com dlthub (dlt) -> Azure SQL Database (Camada Bronze).
Este script orquestra a extração da API do Portal da Transparência (ou modo amostra)
e o carregamento resiliente no Azure SQL Database sob o schema 'bronze'.
"""

import os
import sys
import logging
import datetime
from pathlib import Path
from typing import Generator, Dict, Any, Tuple

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


def get_default_rolling_window(months_back: int = 2) -> Tuple[str, str]:
    """
    Calcula dinamicamente a janela móvel (Rolling Window) cobrindo os últimos N meses
    a partir da data atual (D-60 até D-0 por padrão).
    Exemplo: em Setembro/2026 com months_back=2 -> retorna ('07/2026', '09/2026').
    Permite capturar despesas retroativas e lançamentos tardios da CGU com consumo mínimo de API.
    """
    today = datetime.date.today()
    mes_fim = f"{today.month:02d}/{today.year}"

    mes_calc = today.month - months_back
    ano_calc = today.year
    while mes_calc <= 0:
        mes_calc += 12
        ano_calc -= 1

    mes_inicio = f"{mes_calc:02d}/{ano_calc}"
    return mes_inicio, mes_fim


@dlt.resource(
    name="cartoes_pagamento",
    write_disposition="merge",
    primary_key="id",
)
def cartoes_pagamento_resource() -> Generator[Dict[str, Any], None, None]:
    """
    Recurso dlt para extrair dados de Cartões de Pagamento (CPGF).
    Usa carga incremental com Upsert (write_disposition='merge') e janela móvel recente,
    preservando o histórico consolidado de anos anteriores sem reprocessamento redundante.
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

        # Janela Móvel: Se houver período explícito no .env ou GitHub Actions, respeita.
        # Caso contrário, calcula automaticamente os últimos meses a partir da data de hoje.
        inicio_env = os.getenv("EXTRACT_MES_EXTRATO_INICIO", "").strip()
        fim_env = os.getenv("EXTRACT_MES_EXTRATO_FIM", "").strip()

        if inicio_env and fim_env:
            inicio = inicio_env
            fim = fim_env
            logger.info(f"Usando período explícito configurado: {inicio} a {fim}")
        else:
            window_months = int(os.getenv("EXTRACT_WINDOW_MONTHS", "2"))
            inicio, fim = get_default_rolling_window(months_back=window_months)
            logger.info(
                f"Janela Móvel Incremental Ativa (Rolling Window de {window_months + 1} meses): {inicio} a {fim}"
            )

        max_pages = int(
            os.getenv(
                "MAX_PAGES_PER_MONTH",
                "5"
            )
        )

        timeout = int(os.getenv("CGU_TIMEOUT", "60"))
        client = CGUClient(api_key=api_key, timeout=timeout)
        total_extraido = 0

        for record in client.get_cartoes_pagamento(
            mes_extrato_inicio=inicio,
            mes_extrato_fim=fim,
            max_pages=max_pages,
        ):
            total_extraido += 1
            yield record

        if total_extraido == 0:
            raise RuntimeError(
                f"Contrato de Volume Violado: 0 registros extraídos da API da CGU no período {inicio} a {fim}. "
                "Abortando ingestão para evitar contaminação da camada Bronze com dados vazios."
            )

        logger.info(
            f"Extração da API CGU concluída com sucesso: {total_extraido} registros coletados."
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