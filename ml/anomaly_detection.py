"""
Módulo de Machine Learning — Detecção de Anomalias em Despesas com Cartão (CPGF).
Algoritmo: Isolation Forest (Não Supervisionado) com Escala Normalizada [0.0, 1.0].

Lê a tabela fato 'gold.fct_gastos_cartao' e dimensão 'gold.dim_data', gera features
comportamentais (desvio em relação ao órgão, gastos em fins de semana, raridade do favorecido)
e persiste os scores na tabela 'gold.score_anomalia_cartao' no Azure SQL Database.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Tuple, Dict, Any
import numpy as np
import pandas as pd
import pyodbc
from dotenv import load_dotenv
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import MinMaxScaler

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SCORE_TABLE = "gold.score_anomalia_cartao"
MODEL_VERSION = "isolation_forest_v1_cpgf"


def get_connection_string() -> str:
    """Monta a string de conexão ODBC para o Azure SQL Database com fallbacks seguros."""
    server = os.getenv("AZURE_SQL_SERVER")
    database = os.getenv("AZURE_SQL_DATABASE")
    user = os.getenv("AZURE_SQL_USER")
    password = os.getenv("AZURE_SQL_PASSWORD")
    driver = os.getenv("AZURE_SQL_DRIVER", "ODBC Driver 17 for SQL Server")

    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )


def extract_gold_features(conn: pyodbc.Connection) -> pd.DataFrame:
    """Extrai transações e atributos dimensionais da camada Gold."""
    query = """
    SELECT
        f.id_transacao,
        f.sk_data,
        f.sk_orgao,
        f.sk_favorecido,
        f.sk_portador,
        CAST(f.vl_transacao AS FLOAT) AS vl_transacao,
        CAST(f.media_orgao AS FLOAT) AS media_orgao,
        CAST(f.z_score AS FLOAT) AS z_score,
        COALESCE(d.dia_semana, 1) AS dia_semana,
        COALESCE(d.fl_fim_semana, 0) AS fl_fim_semana
    FROM gold.fct_gastos_cartao f
    LEFT JOIN gold.dim_data d ON f.sk_data = d.sk_data
    WHERE f.vl_transacao IS NOT NULL
    """
    logger.info("Extraindo features da camada Gold (Azure SQL)...")
    return pd.read_sql(query, conn)


def build_feature_matrix(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Realiza Engenharia de Atributos (Feature Engineering) para o Isolation Forest.
    Gera features contextuais e trata ausências.
    """
    df = df.copy()

    # 1. Razão do valor em relação à média do órgão
    media_segura = df["media_orgao"].replace(0, np.nan).fillna(df["vl_transacao"].mean())
    df["razao_media_orgao"] = (df["vl_transacao"] / media_segura).fillna(1.0)

    # 2. Frequência do favorecido no histórico (compras em fornecedores raros são mais atípicas)
    df["freq_favorecido"] = df.groupby("sk_favorecido")["id_transacao"].transform("count")

    # 3. Frequência de uso pelo portador
    df["freq_portador"] = df.groupby("sk_portador")["id_transacao"].transform("count")

    # Matriz numérica de treino (sem NaNs)
    feature_cols = [
        "vl_transacao",
        "z_score",
        "razao_media_orgao",
        "dia_semana",
        "fl_fim_semana",
        "freq_favorecido",
        "freq_portador",
    ]

    X = df[feature_cols].copy()
    for col in feature_cols:
        X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0.0)

    return df, X


def train_and_score(
    df_meta: pd.DataFrame,
    X: pd.DataFrame,
    n_estimators: int = 150,
    random_state: int = 42
) -> pd.DataFrame:
    """
    Treina o Isolation Forest e normaliza o score de anomalia entre [0.0, 1.0].
    Valores próximos de 1.0 representam anomalias severas; próximos de 0.0 representam gastos rotineiros.
    """
    if len(X) == 0:
        logger.warning("Matriz de features vazia. Pulando inferência.")
        return pd.DataFrame()

    logger.info(f"Treinando Isolation Forest com {n_estimators} árvores sobre {len(X)} transações...")
    model = IsolationForest(
        n_estimators=n_estimators,
        contamination="auto",
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(X)

    # decision_function: números mais baixos/negativos são anomalias.
    raw_scores = model.decision_function(X)

    # Inverte e normaliza em [0.0, 1.0] para que scores MAIORES indiquem MAIOR anomalia.
    inverted_scores = -raw_scores
    scaler = MinMaxScaler(feature_range=(0.0, 1.0))
    normalized_scores = scaler.fit_transform(inverted_scores.reshape(-1, 1)).flatten()

    df_result = pd.DataFrame({
        "id_transacao": df_meta["id_transacao"],
        "anomaly_score": np.round(normalized_scores, 4),
    })

    # Calibra limiares estatísticos (Top 5% e Top 1% mais atípicos)
    p95 = np.percentile(df_result["anomaly_score"], 95)
    p99 = np.percentile(df_result["anomaly_score"], 99)

    df_result["is_anomaly_p95"] = (df_result["anomaly_score"] >= p95).astype(int)
    df_result["is_anomaly_p99"] = (df_result["anomaly_score"] >= p99).astype(int)

    # Atribui justificativa analítica interpretável
    def explain_anomaly(row, orig):
        reasons = []
        if orig.get("fl_fim_semana") == 1:
            reasons.append("Transação em fim de semana")
        if orig.get("z_score", 0) >= 2.0:
            reasons.append("Alto desvio da média do órgão")
        if orig.get("freq_favorecido", 10) <= 2 and orig.get("vl_transacao", 0) > 1000:
            reasons.append("Fornecedor esporádico com valor alto")

        if row["is_anomaly_p99"] == 1:
            return " | ".join(reasons) if reasons else "Anomalia severa multivariada"
        elif row["is_anomaly_p95"] == 1:
            return " | ".join(reasons) if reasons else "Transação com padrão atípico moderado"
        return "Padrão regular"

    reasons_list = [
        explain_anomaly(df_result.iloc[i], df_meta.iloc[i].to_dict())
        for i in range(len(df_result))
    ]
    df_result["motivo_anomalia"] = reasons_list
    df_result["dt_processamento"] = pd.Timestamp.now("UTC")

    logger.info(
        f"Distribuição de Scores: Mín={df_result['anomaly_score'].min():.4f}, "
        f"Mediana={df_result['anomaly_score'].median():.4f}, "
        f"P95={p95:.4f}, P99={p99:.4f}, Máx={df_result['anomaly_score'].max():.4f}"
    )
    logger.info(
        f"Total de Anomalias Sinalizadas: P95={df_result['is_anomaly_p95'].sum()} transações | "
        f"P99 (Críticas)={df_result['is_anomaly_p99'].sum()} transações."
    )

    return df_result


def save_scores_to_azure(df_scores: pd.DataFrame, conn: pyodbc.Connection):
    """
    Cria a tabela 'gold.score_anomalia_cartao' se não existir e persiste os scores gerados.
    Utiliza transação atômica (TRUNCATE + INSERT em batch) para idempotência no pipeline.
    """
    if df_scores.empty:
        logger.warning("Nenhum score para salvar.")
        return

    cursor = conn.cursor()

    # Garante existência da tabela
    create_table_ddl = """
    IF NOT EXISTS (
        SELECT * FROM sys.tables t
        JOIN sys.schemas s ON t.schema_id = s.schema_id
        WHERE s.name = 'gold' AND t.name = 'score_anomalia_cartao'
    )
    BEGIN
        CREATE TABLE gold.score_anomalia_cartao (
            id_transacao BIGINT NOT NULL PRIMARY KEY,
            anomaly_score FLOAT NOT NULL,
            is_anomaly_p95 INT NOT NULL,
            is_anomaly_p99 INT NOT NULL,
            motivo_anomalia NVARCHAR(255) NOT NULL,
            dt_processamento DATETIME2 NOT NULL
        );
    END;
    """
    cursor.execute(create_table_ddl)
    conn.commit()

    logger.info(f"Gravando {len(df_scores)} registros na tabela {SCORE_TABLE}...")
    cursor.execute(f"TRUNCATE TABLE {SCORE_TABLE}")

    insert_sql = f"""
    INSERT INTO {SCORE_TABLE} (
        id_transacao, anomaly_score, is_anomaly_p95, is_anomaly_p99, motivo_anomalia, dt_processamento
    ) VALUES (?, ?, ?, ?, ?, ?)
    """

    records = [
        (
            int(r.id_transacao),
            float(r.anomaly_score),
            int(r.is_anomaly_p95),
            int(r.is_anomaly_p99),
            str(r.motivo_anomalia),
            r.dt_processamento.to_pydatetime()
        )
        for r in df_scores.itertuples(index=False)
    ]

    cursor.fast_executemany = True
    cursor.executemany(insert_sql, records)
    conn.commit()
    logger.info(f"✅ Tabela {SCORE_TABLE} atualizada com sucesso no Azure SQL Database!")


def run_pipeline_anomaly_detection() -> Dict[str, Any]:
    """Ponto de entrada orquestrado pelo run_pipeline.py."""
    conn_str = get_connection_string()
    with pyodbc.connect(conn_str) as conn:
        df_raw = extract_gold_features(conn)
        if df_raw.empty:
            logger.warning("Tabela gold.fct_gastos_cartao está vazia. Pulando detecção de anomalias.")
            return {"status": "skipped", "count": 0}

        df_meta, X = build_feature_matrix(df_raw)
        df_scores = train_and_score(df_meta, X)
        save_scores_to_azure(df_scores, conn)

        return {
            "status": "success",
            "total_processado": len(df_scores),
            "anomalias_p95": int(df_scores["is_anomaly_p95"].sum()),
            "anomalias_p99": int(df_scores["is_anomaly_p99"].sum()),
        }


if __name__ == "__main__":
    run_pipeline_anomaly_detection()
