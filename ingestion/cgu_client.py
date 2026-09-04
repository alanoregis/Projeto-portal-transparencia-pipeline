"""
Cliente HTTP resiliente para a API do Portal da Transparência (CGU).
Documentação: https://api.portaldatransparencia.gov.br/swagger-ui/index.html

"""

import time
import logging
from typing import Any, Dict, Optional
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://api.portaldatransparencia.gov.br/api-de-dados"


def normalize_to_mm_aaaa(val: str, default_month: int, default_year: int = 2026) -> str:
    val = str(val).strip()
    if "/" in val:
        parts = val.split("/")
        if len(parts) == 2:
            return f"{int(parts[0]):02d}/{parts[1]}"
    if len(val) == 6 and val.isdigit():
        return f"{val[4:6]}/{val[0:4]}"
    if len(val) == 4 and val.isdigit():
        return f"{default_month:02d}/{val}"
    return f"{default_month:02d}/{default_year}"

def normalize_record():