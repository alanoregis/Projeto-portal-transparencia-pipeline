/*
Dimensão Calendário/Tempo.
Cobre o histórico das transações e gera hierarquias temporais completas para o Power BI.
*/

{{ config(materialized='table') }}

WITH dates AS (
    -- Gera todos os dias entre 2023 e 2026
    SELECT UNNEST(GENERATE_SERIES(DATE '2023-01-01', DATE '2026-12-31', INTERVAL 1 DAY)) AS data_dia
),

calendario AS (
    SELECT
        -- Chave inteira no padrão universal Kimball (ex: 20260115)
        CAST(strftime(data_dia, '%Y%m%d') AS INTEGER) AS sk_data,
        data_dia::DATE AS dt_data,
        EXTRACT(year FROM data_dia)::INTEGER AS ano,
        EXTRACT(quarter FROM data_dia)::INTEGER AS trimestre,
        EXTRACT(month FROM data_dia)::INTEGER AS mes,
        strftime(data_dia, '%m/%Y') AS mes_ano,
        -- Nome do mês em português, mapeado manualmente (strftime '%B' retorna em inglês no DuckDB)
        CASE EXTRACT(month FROM data_dia)
            WHEN 1  THEN 'Janeiro'
            WHEN 2  THEN 'Fevereiro'
            WHEN 3  THEN 'Março'
            WHEN 4  THEN 'Abril'
            WHEN 5  THEN 'Maio'
            WHEN 6  THEN 'Junho'
            WHEN 7  THEN 'Julho'
            WHEN 8  THEN 'Agosto'
            WHEN 9  THEN 'Setembro'
            WHEN 10 THEN 'Outubro'
            WHEN 11 THEN 'Novembro'
            WHEN 12 THEN 'Dezembro'
        END AS nome_mes,
        EXTRACT(day FROM data_dia)::INTEGER AS dia,
        EXTRACT(dayofweek FROM data_dia)::INTEGER AS dia_semana,
        CASE WHEN EXTRACT(dayofweek FROM data_dia) IN (0, 6) THEN TRUE ELSE FALSE END AS fl_fim_semana
    FROM dates
),

-- Linha sentinela: representa transações sem data válida/conhecida (FK 19000101 na fato)
linha_desconhecida AS (
    SELECT
        19000101 AS sk_data,
        CAST(NULL AS DATE) AS dt_data,
        CAST(NULL AS INTEGER) AS ano,
        CAST(NULL AS INTEGER) AS trimestre,
        CAST(NULL AS INTEGER) AS mes,
        'Desconhecido' AS mes_ano,
        'Desconhecido' AS nome_mes,
        CAST(NULL AS INTEGER) AS dia,
        CAST(NULL AS INTEGER) AS dia_semana,
        CAST(NULL AS BOOLEAN) AS fl_fim_semana
)

SELECT * FROM calendario
UNION ALL
SELECT * FROM linha_desconhecida