"""
Testes unitários para o módulo de Machine Learning (Isolation Forest).
Utiliza dados sintéticos em memória para validar o pipeline de ML sem chamadas de rede.
"""

import pytest
import numpy as np
import pandas as pd
from ml.anomaly_detection import build_feature_matrix, train_and_score, MODEL_VERSION


@pytest.fixture
def sample_gold_dataframe() -> pd.DataFrame:
    """Gera massa sintética representativa de transações da camada Gold."""
    np.random.seed(42)
    n = 100

    # 98 transações comuns de rotina em dias úteis
    ids = list(range(1, n + 1))
    valores = np.random.uniform(50, 400, n).tolist()
    medias = [200.0] * n
    z_scores = np.random.uniform(-1.0, 1.0, n).tolist()
    dias_semana = np.random.choice([2, 3, 4, 5, 6], n).tolist()
    fins_semana = [0] * n
    favorecidos = [101] * (n - 10) + [102] * 10
    portadores = [501] * (n - 20) + [502] * 20

    # Injeta 2 anomalias propositais
    # Caso 1: Gasto absurdo de R$ 35.000 em um domingo
    valores[0] = 35000.0
    z_scores[0] = 5.2
    dias_semana[0] = 1  # Domingo
    fins_semana[0] = 1
    favorecidos[0] = 999  # Fornecedor único/inédito

    # Caso 2: Gasto de R$ 18.000 em um sábado
    valores[1] = 18000.0
    z_scores[1] = 3.8
    dias_semana[1] = 7  # Sábado
    fins_semana[1] = 1

    return pd.DataFrame({
        "id_transacao": ids,
        "sk_data": [20260101 + i for i in range(n)],
        "sk_orgao": [10] * n,
        "sk_favorecido": favorecidos,
        "sk_portador": portadores,
        "vl_transacao": valores,
        "media_orgao": medias,
        "z_score": z_scores,
        "dia_semana": dias_semana,
        "fl_fim_semana": fins_semana,
    })


class TestAnomalyDetectionPipeline:
    """Valida engenharia de features, treino e atribuição de scores."""

    def test_build_feature_matrix_sem_nans(self, sample_gold_dataframe):
        df_meta, X = build_feature_matrix(sample_gold_dataframe)

        assert len(X) == len(sample_gold_dataframe)
        assert X.isna().sum().sum() == 0
        assert "razao_media_orgao" in X.columns
        assert "freq_favorecido" in X.columns
        assert "freq_portador" in X.columns

    def test_scores_normalizados_entre_zero_e_um(self, sample_gold_dataframe):
        df_meta, X = build_feature_matrix(sample_gold_dataframe)
        df_scores = train_and_score(df_meta, X, n_estimators=50, random_state=42)

        assert len(df_scores) == len(sample_gold_dataframe)
        assert df_scores["anomaly_score"].min() >= 0.0
        assert df_scores["anomaly_score"].max() <= 1.0
        assert "is_anomaly_p95" in df_scores.columns
        assert "is_anomaly_p99" in df_scores.columns
        assert "motivo_anomalia" in df_scores.columns
        assert "model_version" in df_scores.columns

    def test_anomalia_extrema_recebe_maior_score_e_flag(self, sample_gold_dataframe):
        """A transação de R$ 35.000 em domingo deve receber o maior score e ser classificada como anomalia P99."""
        df_meta, X = build_feature_matrix(sample_gold_dataframe)
        df_scores = train_and_score(df_meta, X, n_estimators=100, random_state=42)

        # Transação anômala injetada no id 1
        anomalia_1 = df_scores[df_scores["id_transacao"] == 1].iloc[0]
        score_anomalo = anomalia_1["anomaly_score"]
        score_mediano = df_scores["anomaly_score"].median()

        assert score_anomalo > score_mediano
        assert anomalia_1["is_anomaly_p99"] == 1
        assert "fim de semana" in anomalia_1["motivo_anomalia"].lower()

    def test_model_version_persistida_em_todos_os_registros(self, sample_gold_dataframe):
        """Garante que todos os registros recebem a versão do modelo e que ela bate com a constante MODEL_VERSION."""
        df_meta, X = build_feature_matrix(sample_gold_dataframe)
        df_scores = train_and_score(df_meta, X, n_estimators=50, random_state=42)

        assert "model_version" in df_scores.columns
        # Todos os registros devem ter o mesmo valor — sem mistura de versões
        assert df_scores["model_version"].nunique() == 1
        assert df_scores["model_version"].iloc[0] == MODEL_VERSION

    def test_matriz_vazia_retorna_dataframe_vazio(self):
        vazio = pd.DataFrame(columns=["id_transacao", "vl_transacao", "media_orgao", "z_score", "dia_semana", "fl_fim_semana", "sk_favorecido", "sk_portador"])
        df_meta, X = build_feature_matrix(vazio)
        df_scores = train_and_score(df_meta, X)

        assert df_scores.empty
