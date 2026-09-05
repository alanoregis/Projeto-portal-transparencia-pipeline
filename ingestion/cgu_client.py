"""
Cliente HTTP resiliente para a API do Portal da Transparência (CGU).
Documentação: https://api.portaldatransparencia.gov.br/swagger-ui/index.html

"""

import time
import logging
from typing import Dict, Any, Generator, Optional
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

class CGUClient:
    """Cliente HTTP com suporte a autenticação, paginação e retry com backoff exponencial."""

    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        self.api_key = api_key or ""
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "chave-api-dados": self.api_key,
            "Accept": "application/json",
            "User-Agent": "PortalTransparencia-DataPipeline/1.0",
        })

    def _request_with_retry(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 4,
        backoff_factor: float = 2.0,
    ) -> list:
        """Executa uma requisição GET com retry em caso de rate limit ou falhas transitórias."""
        url = f"{BASE_URL}{endpoint}" if not endpoint.startswith("http") else endpoint
        params = params or {}

        for attempt in range(1, max_retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)

                if response.status_code == 200:
                    data = response.json()
                    return data if isinstance(data, list) else [data]

                if response.status_code == 429:
                    sleep_time = backoff_factor ** attempt
                    logger.warning(
                        f"Rate limit atingido (429). Aguardando {sleep_time:.1f}s antes da tentativa {attempt}/{max_retries}..."
                    )
                    time.sleep(sleep_time)
                    continue

                if response.status_code in (500, 502, 503, 504):
                    sleep_time = backoff_factor ** attempt
                    logger.warning(
                        f"Erro de servidor ({response.status_code}). Aguardando {sleep_time:.1f}s antes da tentativa {attempt}/{max_retries}..."
                    )
                    time.sleep(sleep_time)
                    continue

                if response.status_code in (401, 403):
                    logger.error(
                        f"Erro de autenticação ({response.status_code}). "
                        "verifique se a chave 'chave-api-dados' é válida em https://portaldatransparencia.gov.br/api-de-dados/cadastrar-chave"
                    )
                    response.raise_for_status()

                response.raise_for_status()

            except requests.exceptions.RequestException as exc:
                if attempt == max_retries:
                    logger.error(f"Falha definida após {max_retries} tentativas na URL {url}: {exc}")
                    raise
                sleep_time = backoff_factor ** attempt
                logger.warning(f"Erro na requisição ({exc}). Tentando novamente em {sleep_time:.1f}s...")
                time.sleep(sleep_time)

        return []

    def get_cartoes_pagamento(
            self,
            mes_extrato_inicio: str = "01/2026",
            mes_extrato_fim: str = "07/2026",
            max_pages: int = 2,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Consome o endpoint /cartoes paginado mês a mês para o período especificado.

        """
        inicio_str = normalize_to_mm_aaaa(mes_extrato_inicio, default_month=1, default_year=2026)
        fim_str = normalize_to_mm_aaaa(mes_extrato_fim, default_month=7, default_year=2026)

        m_inicio, a_inicio = int(inicio_str.split("/")[0]), int(inicio_str.split("/")[1])
        m_fim, a_fim = int(fim_str.split("/")[0]), int(fim_str.split("/")[1])

        endpoint = "/cartoes"
        logger.info(f"Iniciando extração de Cartões de Pagamento: {inicio_str} a {fim_str} (ano 2026, Máx {max_pages} págs/mês)")

        for ano in range(a_inicio, a_fim + 1):
            start_m = m_inicio if ano == a_inicio else 1
            end_m = m_fim if ano == a_fim else 12

            for mes in range(start_m, end_m + 1):
                mes_param = f"{mes:02d}/{ano}"
                logger.info(f"Consultando despesas do mês {mes_param}...")

                for pagina in range(1, max_pages + 1):
                    params = {
                        "mesExtratoInicio": mes_param,
                        "mesExtratoFim": mes_param,
                        "pagina": pagina,
                    }

                    records = self._request_with_retry(endpoint, params=params)

                    if not records:
                        break

                    for raw_rec in records:
                        yield normalize_record(raw_rec)