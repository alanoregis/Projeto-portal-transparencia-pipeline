"""
Cliente HTTP resiliente para a API do Portal da Transparência (CGU).
Documentação: https://api.portaldatransparencia.gov.br/swagger-ui/index.html

"""

import time
import logging
import re
import os
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

def sanitize_nome_favorecido(nome: str) -> str:
    """
    Higieniza o nome do favorecido removendo documentos (CPF/CNPJ) vazados pela API,
    preservando nomes legítimos de empresas que iniciam com números (ex: '100 FRONTEIRA').
    """
    if not nome:
        return "NAO INFORMADO"
    
    texto = str(nome).strip()

    # 1. CNPJ ou Raiz no início: ex "00.110.647 NOME" ou "00.110.647/0001-00 - NOME"
    texto = re.sub(r'^\d{2}\.\d{3}\.\d{3}(/\d{4}-\d{2})?\s*[-–]?\s*', '', texto)

    # 2. CNPJ puro de 14 dígitos no início
    texto = re.sub(r'^\d{14}\s*[-–]?\s*', '', texto)

    # 3. Sufixo explícito "- CPF ...", "CPF: ...", "- CNPJ ..." no final
    texto = re.sub(r'\s*[-–]?\s*(CPF|CNPJ)[:\s]*[\d\.\-\*\/]+$', '', texto, flags=re.IGNORECASE)

    # 4. CPF numérico puro de 11 dígitos no final
    texto = re.sub(r'\s+\d{11}$', '', texto)

    # 5. CNPJ numérico puro de 14 dígitos no final
    texto = re.sub(r'\s+\d{14}$', '', texto)

    return texto.strip().upper() or "NAO INFORMADO"

def normalize_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Higieniza dados sensíveis (LGPD) e preserva a totalidade das informações da API da CGU para a Camada Bronze.
    Garante que todos os atributos de negócio cheguem ao Data Warehouse sem descarte precoce.
    """
    unidade_gestora = raw.get("unidadeGestora") or {}
    orgao_vinculado = unidade_gestora.get("orgaoVinculado") or raw.get("orgaoVinculado") or {}
    orgao_superior = unidade_gestora.get("orgaoMaximo") or raw.get("orgaoSuperior") or {}
    estabelecimento = raw.get("estabelecimento") or {}
    portador = raw.get("portador") or {}
    tipo_cartao = raw.get("tipoCartao") or {}

    # 1. Higienização por Regex apenas em campos textuais de nome (Proteção LGPD na borda)
    nome_raw = estabelecimento.get("nome") or ""
    razao_social_raw = estabelecimento.get("razaoSocialReceita") or ""
    nome_fantasia_raw = estabelecimento.get("nomeFantasiaReceita") or ""

    nome_est = sanitize_nome_favorecido(nome_raw) if nome_raw else "NAO INFORMADO"
    razao_social = sanitize_nome_favorecido(razao_social_raw) if razao_social_raw else nome_est
    nome_fantasia = sanitize_nome_favorecido(nome_fantasia_raw) if nome_fantasia_raw else "NAO INFORMADO"

    # 2. Documentos do Estabelecimento (preservando distinção CNPJ / CPF / CGC)
    cnpj = estabelecimento.get("cnpjFormatado") or ""
    cpf_est = estabelecimento.get("cpfFormatado") or ""
    cgc_fallback = cnpj or cpf_est or estabelecimento.get("cgc") or "NAO INFORMADO"

    # 3. Portador
    cpf_portador = portador.get("cpfFormatado") or portador.get("cpf") or "NAO INFORMADO"
    nome_portador = portador.get("nome") or "NAO INFORMADO"
    nis_portador = portador.get("nis") or ""

    return {
        "id": raw.get("id"),
        "mesExtrato": raw.get("mesExtrato"),
        "dataTransacao": raw.get("dataTransacao"),
        "valorTransacao": raw.get("valorTransacao"),
        "tipoCartao": {
            "id": tipo_cartao.get("id") or 1,
            "codigo": tipo_cartao.get("codigo") or str(tipo_cartao.get("id") or 1),
            "descricao": tipo_cartao.get("descricao") or "CPGF - Cartão de Pagamento do Governo Federal",
        },
        "estabelecimento": {
            "id": estabelecimento.get("id"),
            "nome": nome_est,
            "razaoSocialReceita": razao_social,
            "nomeFantasiaReceita": nome_fantasia,
            "cnpjFormatado": cnpj,
            "cpfFormatado": cpf_est,
            "cgc": cgc_fallback,
            "tipo": estabelecimento.get("tipo") or "NAO INFORMADO",
            "numeroInscricaoSocial": estabelecimento.get("numeroInscricaoSocial") or "",
        },
        "portador": {
            "nome": nome_portador,
            "cpf": cpf_portador,
            "cpfFormatado": cpf_portador,
            "nis": nis_portador,
        },
        "unidadeGestora": {
            "codigo": unidade_gestora.get("codigo") or "00000",
            "nome": unidade_gestora.get("nome") or "NAO INFORMADO",
            "descricaoPoder": unidade_gestora.get("descricaoPoder") or "EXECUTIVO",
        },
        "orgaoVinculado": {
            "codigo": orgao_vinculado.get("codigoSIAFI") or orgao_vinculado.get("codigo") or "00000",
            "nome": orgao_vinculado.get("nome") or "NAO INFORMADO",
            "sigla": orgao_vinculado.get("sigla") or "",
            "cnpj": orgao_vinculado.get("cnpj") or "",
        },
        "orgaoSuperior": {
            "codigo": orgao_superior.get("codigo") or "00000",
            "nome": orgao_superior.get("nome") or "NAO INFORMADO",
            "sigla": orgao_superior.get("sigla") or "",
        },
    }

class CGUAPIError(Exception):
    """Exceção levantada quando a API da CGU falha de forma irrecuperável."""
    pass


class CGUClient:
    """Cliente HTTP com suporte a autenticação, paginação, proxy e retry com backoff exponencial."""

    def __init__(self, api_key: Optional[str] = None, timeout: int = 60, proxy: Optional[str] = None):
        self.api_key = api_key or ""
        self.timeout = timeout
        self.proxy = proxy or os.getenv("CGU_PROXY")
        self.session = requests.Session()

        self.gateway_url = os.getenv("CGU_GATEWAY_URL")
        self.gateway_secret = os.getenv("GATEWAY_SECRET", "")
        if self.gateway_url:
            logger.info("Gateway Serverless ativo: requisições CGU roteadas via Azure Function (São Paulo).")
            if not self.gateway_secret:
                logger.warning("GATEWAY_SECRET não configurado. A Function pode rejeitar a requisição com 401.")
        elif self.proxy:
            self.session.proxies = {
                "http": self.proxy,
                "https": self.proxy,
            }
            logger.info(f"Proxy CGU customizado ativo: {self.proxy}")

        self.session.headers.update({
            "chave-api-dados": self.api_key,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
        })

    def _request_with_retry(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 4,
        backoff_factor: float = 2.0,
    ) -> list:
        """Executa uma requisição GET com retry em caso de rate limit ou falhas transitórias."""
        if self.gateway_url:
            url = self.gateway_url
            params = params.copy() if params else {}
            params["endpoint"] = endpoint
            # Autentica o pipeline como chamador autorizado da Azure Function
            if self.gateway_secret:
                self.session.headers.update({"X-Gateway-Secret": self.gateway_secret})
        else:
            url = f"{BASE_URL}{endpoint}" if not endpoint.startswith("http") else endpoint
            params = params or {}
        last_status = None

        for attempt in range(1, max_retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                last_status = response.status_code

                if response.status_code == 200:
                    data = response.json()
                    return data if isinstance(data, list) else [data]

                if response.status_code == 429:
                    if attempt == max_retries:
                        break
                    sleep_time = backoff_factor ** attempt
                    logger.warning(
                        f"Rate limit atingido (429). Aguardando {sleep_time:.1f}s antes da tentativa {attempt + 1}/{max_retries}..."
                    )
                    time.sleep(sleep_time)
                    continue

                if response.status_code in (500, 502, 503, 504):
                    if attempt == max_retries:
                        break
                    sleep_time = backoff_factor ** attempt
                    logger.warning(
                        f"Erro de servidor ({response.status_code}). Aguardando {sleep_time:.1f}s antes da tentativa {attempt + 1}/{max_retries}..."
                    )
                    time.sleep(sleep_time)
                    continue

                if response.status_code in (401, 403):
                    msg = (
                        f"Erro de autenticação ({response.status_code}). "
                        "Verifique se a chave 'chave-api-dados' é válida em https://portaldatransparencia.gov.br/api-de-dados/cadastrar-chave"
                    )
                    logger.error(msg)
                    raise CGUAPIError(msg)

                response.raise_for_status()

            except requests.exceptions.RequestException as exc:
                if attempt == max_retries:
                    logger.error(f"Falha de conexão/rede após {max_retries} tentativas na URL {url}: {exc}")
                    raise CGUAPIError(f"Falha de rede após {max_retries} tentativas na URL {url}: {exc}") from exc
                sleep_time = backoff_factor ** attempt
                logger.warning(f"Erro na requisição ({exc}). Tentando novamente em {sleep_time:.1f}s...")
                time.sleep(sleep_time)

        # Se saiu do loop sem retorno 200, significa que todas as tentativas falharam
        raise CGUAPIError(
            f"Falha irrecuperável na API da CGU ({url}) após {max_retries} tentativas. "
            f"Último status HTTP: {last_status}. Abortando para evitar ingestão com dados vazios."
        )

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