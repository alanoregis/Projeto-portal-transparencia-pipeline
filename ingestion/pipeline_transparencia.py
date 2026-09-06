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

# Adiciona a raiz do projeto ao sys.path para garantir os imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.cgu_client import CGUClient
from ingestion.sample_data import get_sample_cartoes

# Carrega variáveis do arquivo .env
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
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

        inicio = os.getenv("EXTRACT_MES_EXTRATO_INICIO", "01/2026").strip()
        fim = os.getenv("EXTRACT_MES_EXTRATO_FIM", "07/2026").strip()
        max_pages = int(os.getenv("MAX_PAGES_PER_MONTH", "2"))

        client = CGUClient(api_key=api_key)
        yield from client.get_cartoes_pagamento(
            mes_extrato_inicio=inicio,
            mes_extrato_fim=fim,
            max_pages=max_pages,
        )
    else:
        logger.info("Executando ingestão em modo 'sample' (dados de amostra)...")
        data = get_sample_cartoes()
        for record in data:
            yield record

@dlt.source(name="portal_transparencia")
def transparencia_source():
    """Fonte dlt agrupando recursos do Portal da Transparência."""
    return cartoes_pagamento_resource