"""
Testes unitários para o cliente HTTP da CGU e funções de normalização.
Utiliza mocks para simular respostas da API sem efetuar chamadas de rede reais.
"""

from unittest.mock import patch, MagicMock
import requests
from ingestion.cgu_client import CGUClient, normalize_to_mm_aaaa, normalize_record


class TestNormalizacoesCGU:
    """Testes para garantir que datas e dicionários sejam padronizados corretamente."""

    def test_normalize_to_mm_aaaa_com_barra(self):
        assert normalize_to_mm_aaaa("1/2026", default_month=1) == "01/2026"
        assert normalize_to_mm_aaaa("12/2024", default_month=1) == "12/2024"

    def test_normalize_to_mm_aaaa_com_seis_digitos(self):
        assert normalize_to_mm_aaaa("202603", default_month=1) == "03/2026"

    def test_normalize_record_com_campos_faltantes(self):
        """Garante que um registro incompleto seja preenchido com fallbacks seguros."""
        raw_incompleto = {
            "id": 12345,
            "mesExtrato": "01/2026",
            "valorTransacao": "150,00",
            # Repare: sem portador, sem estabelecimento e sem unidadeGestora
        }
        resultado = normalize_record(raw_incompleto)

        assert resultado["id"] == 12345
        assert resultado["estabelecimento"]["nome"] == "NAO INFORMADO"
        assert resultado["portador"]["nome"] == "NAO INFORMADO"
        assert resultado["unidadeGestora"]["codigo"] == "00000"


class TestCGUClientMock:
    """Testes de resiliência e paginação simulando a API via Mock."""

    @patch("requests.Session.get")
    def test_request_sucesso_retorna_lista(self, mock_get):
        """Simula resposta HTTP 200 de sucesso."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": 1, "valorTransacao": "50,00"}]
        mock_get.return_value = mock_response

        client = CGUClient(api_key="chave_teste")
        dados = client._request_with_retry("/cartoes")

        assert len(dados) == 1
        assert dados[0]["id"] == 1

    @patch("time.sleep")  # Mock do sleep para o teste não esperar segundos reais!
    @patch("requests.Session.get")
    def test_request_retry_em_rate_limit_429(self, mock_get, mock_sleep):
        """Simula que a API deu 429 na 1ª tentativa e 200 na 2ª tentativa."""
        resp_429 = MagicMock()
        resp_429.status_code = 429

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = [{"id": 99}]

        mock_get.side_effect = [resp_429, resp_200]

        client = CGUClient(api_key="chave_teste")
        dados = client._request_with_retry("/cartoes", max_retries=2, backoff_factor=1.0)

        assert len(dados) == 1
        assert dados[0]["id"] == 99
        assert mock_get.call_count == 2
        assert mock_sleep.called