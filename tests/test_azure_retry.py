"""
Testes unitários para detecção de erros transitórios do Azure SQL Serverless.
Garante que o pipeline identifique o cold-start (código 40613) mesmo quando
a exceção estiver encapsulada em múltiplos níveis pelo dlt/SQLAlchemy.
"""

import pytest
from ingestion.pipeline_transparencia import is_azure_transient_error


class TestAzureTransientError:
    """Testes cobrindo inspeção de árvore de exceções para auto-resume do Azure SQL."""

    def test_detecta_erro_40613_direto(self):
        """Valida detecção direta na mensagem da exceção."""
        erro = Exception("Error 40613: Database 'sqldb-transparencia' is not currently available.")
        assert is_azure_transient_error(erro, ("40613",)) is True

    def test_detecta_erro_40613_aninhado_em_cause(self):
        """Simula o dlt encapsulando a falha do banco dentro de __cause__."""
        erro_banco = Exception("pyodbc.OperationalError: (40613, 'Database is resuming')")
        erro_dlt = RuntimeError("PipelineStepFailed: falha no step de load")
        erro_dlt.__cause__ = erro_banco  # Encadeamento real do Python

        assert is_azure_transient_error(erro_dlt, ("40613",)) is True

    def test_detecta_erro_40613_aninhado_em_context(self):
        """Simula exceção transitória associada via __context__."""
        erro_origem = Exception("40613: Service unavailable during auto-resume")
        erro_superior = Exception("Falha de conexão com Azure SQL")
        erro_superior.__context__ = erro_origem

        assert is_azure_transient_error(erro_superior, ("40613",)) is True

    def test_ignora_erros_permanentes_sem_retry(self):
        """Garante que erros de sintaxe ou coluna inválida NÃO sejam marcados como transitórios."""
        erro_sintaxe = Exception("Invalid column name 'valor_despesa'")
        assert is_azure_transient_error(erro_sintaxe, ("40613",)) is False

    def test_suporte_a_multiplos_codigos_transientes(self):
        """Valida que a função aceita outros códigos de erro transitórios conhecidos."""
        erro_timeout = Exception("40501: Service busy, try again later")
        codigos = ("40613", "40501", "40197")
        assert is_azure_transient_error(erro_timeout, codigos) is True