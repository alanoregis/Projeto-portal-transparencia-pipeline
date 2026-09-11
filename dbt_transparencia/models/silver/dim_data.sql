/*
Dimensão Calendário/Tempo.
Padrão Kimball com ordenação ISO (YYYY-MM) e Membro Desconhecido (19000101).
*/

{{ config(materialized='table') }}

WITH dates AS (
    SELECT UNNEST(GENERATE_SERIES(DATE '2020-01-01', DATE '2030-12-31', INTERVAL 1 DAY)) AS data_dia
),

calendario AS (
    SELECT
        CAST(strftime(data_dia, '%Y%m%d') AS INTEGER) AS sk_data,
        data_dia::DATE AS dt_data,
        EXTRACT(year FROM data_dia)::INTEGER AS ano,
        EXTRACT(quarter FROM data_dia)::INTEGER AS trimestre,
        EXTRACT(month FROM data_dia)::INTEGER AS mes,
        -- Padrão ISO: ordena naturalmente no tempo (ex: 2026-01)
        strftime(data_dia, '%Y-%m') AS ano_mes,
        strftime(data_dia, '%m/%Y') AS mes_ano,
        strftime(data_dia, '%B') AS nome_mes,
        EXTRACT(day FROM data_dia)::INTEGER AS dia,
        EXTRACT(dayofweek FROM data_dia)::INTEGER AS dia_semana,
        CASE WHEN EXTRACT(dayofweek FROM data_dia) IN (0, 6) THEN TRUE ELSE FALSE END AS fl_fim_semana
    FROM dates
)

SELECT * FROM calendario

UNION ALL

-- Registro Padrão Kimball para datas não mapeadas (Unknown Member)
SELECT
    19000101 AS sk_data,
    DATE '1900-01-01' AS dt_data,
    1900 AS ano,
    0 AS trimestre,
    0 AS mes,
    '1900-00' AS ano_mes,
    'Desconhecido' AS mes_ano,
    'Desconhecido' AS nome_mes,
    0 AS dia,
    0 AS dia_semana,
    FALSE AS fl_fim_semana