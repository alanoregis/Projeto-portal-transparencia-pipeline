"""
Testes unitários para a função de sanitização de PII / nomes de favorecidos.
Garante a conformidade com LGPD sem comprometer a integridade de empresas legítimas.
"""

import pytest
from ingestion.cgu_client import sanitize_nome_favorecido


class TestSanitizeNomeFavorecido:
    """Testes cobrindo remoção de documentos e preservação de nomes comerciais."""

    @pytest.mark.parametrize(
        "entrada, esperado",
        [
            # 1. CNPJ formatado ou Raiz no início
            ("00.110.647 SILVIO LUIZ DE SOUZA", "SILVIO LUIZ DE SOUZA"),
            ("00.110.647/0001-76 - SILVIO LUIZ DE SOUZA", "SILVIO LUIZ DE SOUZA"),
            ("02.221.937 LTDA", "LTDA"),
            ("08.508.546/0001-60 MAXICARD CONSULTORIA", "MAXICARD CONSULTORIA"),

            # 2. CNPJ puro de 14 dígitos no início
            ("34637195000288 CURINGA PNEUMATICOS LTDA", "CURINGA PNEUMATICOS LTDA"),

            # 3. Sufixo explícito "- CPF ...", "CPF: ...", "- CNPJ ..." no final
            ("ANDERSON ROGERIO DE RESENDE - CPF 055.677.156-76", "ANDERSON ROGERIO DE RESENDE"),
            ("JOAO DA SILVA - CPF: 123.456.789-00", "JOAO DA SILVA"),
            ("MARIA DE SOUZA CPF: ***123456**", "MARIA DE SOUZA"),
            ("EMPRESA ABC - CNPJ: 12.345.678/0001-90", "EMPRESA ABC"),

            # 4. CPF numérico puro de 11 dígitos no final (sem máscara)
            ("ANDERSON COELHO DO NASCIMENTO 07776785431", "ANDERSON COELHO DO NASCIMENTO"),
            ("ANDERSON DA SILVA BENEDITO 09212478778", "ANDERSON DA SILVA BENEDITO"),

            # 5. CNPJ numérico puro de 14 dígitos no final
            ("POSTO COMERCIO DE COMBUSTIVEIS 12345678000199", "POSTO COMERCIO DE COMBUSTIVEIS"),
        ],
    )
    def test_deve_remover_documentos_vazados(self, entrada: str, esperado: str):
        """Valida que documentos de CPF e CNPJ são removidos em diferentes posições."""
        resultado = sanitize_nome_favorecido(entrada)
        assert resultado == esperado

    @pytest.mark.parametrize(
        "empresa_legitima",
        [
            "100 FRONTEIRA - COMERCIO LTDA",
            "3M DO BRASIL LTDA",
            "1000 GRAUS LANCHES E REFEICOES",
            "7 DE SETEMBRO COMERCIO",
            "2001 MATERIAIS DE CONSTRUCAO",
            "POSTO 1000 GRAUS",
        ],
    )
    def test_deve_preservar_nomes_legitimos_iniciados_por_numeros(self, empresa_legitima: str):
        """Garante que números legítimos de nomes comerciais NÃO sejam cortados erroneamente."""
        resultado = sanitize_nome_favorecido(empresa_legitima)
        assert resultado == empresa_legitima

    @pytest.mark.parametrize(
        "entrada_vazia",
        [
            "",
            None,
            "   ",
        ],
    )
    def test_deve_tratar_entradas_vazias_ou_nulas(self, entrada_vazia):
        """Garante que valores nulos ou vazios retornem 'NAO INFORMADO' sem quebrar."""
        resultado = sanitize_nome_favorecido(entrada_vazia)
        assert resultado == "NAO INFORMADO"