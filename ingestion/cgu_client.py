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

def normalize_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Padroniza a estrutura do registro retornado pela API da CGU para o schema do pipeline.
    Garante compatibilidade de nomes e colunas para a camada Bronze.
    
    """
    unidade_gestora = raw.get("unidadeGestora") or {}
    orgao_vinculado = unidade_gestora.get("orgaoVinculado") or raw.get("orgaoVinculado") or {}
    orgao_superior = unidade_gestora.get("orgaoMaximo") or raw.get("orgaoSuperior") or {}
    estabelecimento = raw.get("estabelecimento") or {}
    portador = raw.get("portador") or {}
    tipo_cartao = raw.get("tipoCartao") or {}

    cgc = (
        estabelecimento.get("cnpjFormatado")
        or estabelecimento.get("cpfFormatado")
        or estabelecimento.get("cgc")
        or "NAO INFORMADO"
    )
    nome_est = (
        estabelecimento.get("nome")
        or estabelecimento.get("razaoSocialReceita")
        or estabelecimento.get("nomeFantasiaReceita")
        or "NAO INFORMADO"
    )

    cpf_portador = portador.get("cpfFormatado") or portador.get("cpf") or "NAO INFORMADO"
    nome_portador = portador.get("nome") or "NAO INFORMADO"

    return {
        "id": raw.get("id"),
        "mesExtrato": raw.get("mesExtrato"),
        "dataTransacao": raw.get("dataTransacao"),
        "valorTransacao": raw.get("valorTransacao"),
        "tipoCartao": {
            "codigo": tipo_cartao.get("codigo") or tipo_cartao.get("id") or 1,
            "descricao": tipo_cartao.get("descricao") or "CPGF - Cartão de Pagamento do Governo Federal",
        },
        "estabelecimento": {
            "nome": nome_est,
            "cgc": cgc,
        },
        "portador": {
            "nome": nome_portador,
            "cpf": cpf_portador,
        },
        "unidadeGestora": {
            "codigo": unidade_gestora.get("codigo") or "00000",
            "nome": unidade_gestora.get("nome") or "NAO INFORMADO",
        },
        "orgaoVinculado": {
            "codigo": orgao_vinculado.get("codigoSIAFI") or orgao_vinculado.get("codigo") or "00000",
            "nome": orgao_vinculado.get("nome") or "NAO INFORMADO",
        },
        "orgaoSuperior": {
            "codigo": orgao_superior.get("codigo") or "00000",
            "nome": orgao_superior.get("nome") or "NAO INFORMADO",
        },
    }