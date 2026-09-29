"""
Testes unitários para o cliente HTTP da CGU e funções de normalização.
Utiliza mocks para simular respostas da API sem efetuar chamadas de rede reais.
"""

from unittest.mock import patch, MagicMock
import pytest
import requests
from ingestion.cgu_client import CGUClient, CGUAPIError, normalize_to_mm_aaaa, normalize_record
from ingestion.pipeline_transparencia import get_default_rolling_window


class TestNormalizacoesCGU:
    """Testes para garantir que datas e dicionários sejam padronizados corretamente."""

    def test_rolling_window_retorna_formato_e_ordem_corretos(self):
        """Garante que a janela móvel incremental retorne datas válidas MM/AAAA."""
        inicio, fim = get_default_rolling_window(months_back=2)
        assert len(inicio.split("/")) == 2
        assert len(fim.split("/")) == 2
        m_ini, a_ini = int(inicio.split("/")[0]), int(inicio.split("/")[1])
        m_fim, a_fim = int(fim.split("/")[0]), int(fim.split("/")[1])
        assert 1 <= m_ini <= 12
        assert 1 <= m_fim <= 12
        assert a_fim >= a_ini

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

    def test_normalize_record_preserva_campos_completos_da_api(self):
        """Garante que dados ricos da API (siglas, nomes fantasia, poder) sejam preservados na Bronze."""
        raw_completo = {
            "id": 478909949,
            "mesExtrato": "01/2026",
            "dataTransacao": "28/11/2025",
            "valorTransacao": "1.252,55",
            "tipoCartao": {
                "id": 1,
                "codigo": "1",
                "descricao": "Cartão de Pagamento do Governo Federal - CPGF"
            },
            "estabelecimento": {
                "id": 92756983,
                "cpfFormatado": "",
                "cnpjFormatado": "32.428.740/0001-10",
                "numeroInscricaoSocial": "",
                "nome": "32.428.740 A F CARDOSO",
                "razaoSocialReceita": "A F CARDOSO",
                "nomeFantasiaReceita": "CARDOSO MATERIAL DE CONSTRUCAO",
                "tipo": "Entidades Empresariais Privadas"
            },
            "unidadeGestora": {
                "codigo": "795140",
                "nome": "3.BATALHAO DE INFANTARIA DE FUZILEIROS NAVAIS",
                "descricaoPoder": "EXECUTIVO",
                "orgaoVinculado": {
                    "codigoSIAFI": "52131",
                    "cnpj": "00394502000144",
                    "sigla": "CMDO MARINHA",
                    "nome": "Comando da Marinha"
                },
                "orgaoMaximo": {
                    "codigo": "52000",
                    "sigla": "DEFESA",
                    "nome": "Ministério da Defesa"
                }
            },
            "portador": {
                "cpfFormatado": "***.317.637-**",
                "nis": "",
                "nome": "CARLOS MOZART RODRIGUES DOS SANTOS ISMERIM"
            }
        }
        res = normalize_record(raw_completo)

        assert res["estabelecimento"]["nome"] == "A F CARDOSO"
        assert res["estabelecimento"]["nomeFantasiaReceita"] == "CARDOSO MATERIAL DE CONSTRUCAO"
        assert res["estabelecimento"]["cnpjFormatado"] == "32.428.740/0001-10"
        assert res["estabelecimento"]["tipo"] == "Entidades Empresariais Privadas"
        assert res["unidadeGestora"]["descricaoPoder"] == "EXECUTIVO"
        assert res["orgaoSuperior"]["sigla"] == "DEFESA"
        assert res["orgaoVinculado"]["sigla"] == "CMDO MARINHA"


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

    @patch("time.sleep")
    @patch("requests.Session.get")
    def test_504_esgotado_levanta_cgu_api_error(self, mock_get, mock_sleep):
        """Regressão do Incidente: 504 persistente em todas as tentativas DEVE levantar CGUAPIError, nunca retornar []."""
        resp_504 = MagicMock()
        resp_504.status_code = 504
        mock_get.return_value = resp_504

        client = CGUClient(api_key="chave_teste")
        with pytest.raises(CGUAPIError, match="Falha irrecuperável na API da CGU.*504"):
            client._request_with_retry("/cartoes", max_retries=4, backoff_factor=1.0)

        assert mock_get.call_count == 4
        assert mock_sleep.call_count == 3

    def test_headers_simulam_navegador_legitimo(self):
        """Garante que a sessão inicializa com headers que mimetizam navegador comum e pt-BR contra WAF."""
        client = CGUClient(api_key="chave_teste")
        headers = client.session.headers

        assert "Mozilla" in headers["User-Agent"]
        assert "Chrome" in headers["User-Agent"]
        assert "pt-BR" in headers["Accept-Language"]
        assert headers["chave-api-dados"] == "chave_teste"

    def test_proxy_customizado_fallback(self, monkeypatch):
        """Garante que CGU_PROXY ativa proxy padrão quando configurado."""
        monkeypatch.delenv("CGU_GATEWAY_URL", raising=False)
        monkeypatch.setenv("CGU_PROXY", "http://meu-proxy-br:8080")
        client = CGUClient(api_key="chave_cgu")

        assert client.session.proxies == {
            "http": "http://meu-proxy-br:8080",
            "https": "http://meu-proxy-br:8080",
        }

    @patch("requests.Session.get")
    def test_gateway_azure_function_roteamento_correto(self, mock_get, monkeypatch):
        """Garante que CGU_GATEWAY_URL roteia as requisições para a Azure Function com o endpoint nos parâmetros."""
        monkeypatch.setenv("CGU_GATEWAY_URL", "https://func-cgu-proxy-alano.azurewebsites.net/api/cgu_proxy")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": 123}]
        mock_get.return_value = mock_response

        client = CGUClient(api_key="chave_cgu")
        dados = client._request_with_retry("/cartoes", params={"pagina": 1})

        assert len(dados) == 1
        assert dados[0]["id"] == 123
        # Valida que chamou a URL da Function e passou endpoint nos params
        chamada_url = mock_get.call_args[0][0]
        chamada_params = mock_get.call_args[1]["params"]
        assert chamada_url == "https://func-cgu-proxy-alano.azurewebsites.net/api/cgu_proxy"
        assert chamada_params["endpoint"] == "/cartoes"
        assert chamada_params["pagina"] == 1