/*
Dimensão Calendário/Tempo compatível com Azure SQL Database (T-SQL).
Gerada de forma limpa e padronizada usando a macro dbt_utils.date_spine.
Padrão Kimball com ordenação ISO (YYYY-MM) e Membro Desconhecido (19000101).
*/

{{ config(materialized='table') }}

WITH dates AS (
    -- Gera uma sequência diária de 2023-01-01 até 2026-12-31 de forma nativa e elegante
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2023-01-01' as date)",
        end_date="cast('2027-01-01' as date)"
    ) }}
),

calendario AS (
    SELECT
        CAST(CONVERT(VARCHAR(8), date_day, 112) AS INT) AS sk_data,
        CAST(date_day AS DATE) AS dt_data,
        DATEPART(YEAR, date_day) AS ano,
        DATEPART(QUARTER, date_day) AS trimestre,
        DATEPART(MONTH, date_day) AS mes,
        -- Padrão ISO: ordena naturalmente no tempo (ex: 2026-01)
        CONVERT(VARCHAR(7), date_day, 120) AS ano_mes,
        FORMAT(date_day, 'MM/yyyy') AS mes_ano,
        DATENAME(MONTH, date_day) AS nome_mes,
        DATEPART(DAY, date_day) AS dia,
        DATEPART(WEEKDAY, date_day) AS dia_semana,
        CASE WHEN DATEPART(WEEKDAY, date_day) IN (1, 7) THEN 1 ELSE 0 END AS fl_fim_semana
    FROM dates
)

SELECT * FROM calendario

UNION ALL

-- Registro Padrão Kimball para datas não mapeadas (Unknown Member)
SELECT
    19000101 AS sk_data,
    CAST('1900-01-01' AS DATE) AS dt_data,
    1900 AS ano,
    0 AS trimestre,
    0 AS mes,
    '1900-00' AS ano_mes,
    'Desconhecido' AS mes_ano,
    'Desconhecido' AS nome_mes,
    0 AS dia,
    0 AS dia_semana,
    0 AS fl_fim_semana