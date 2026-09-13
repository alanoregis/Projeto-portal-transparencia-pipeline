/*
Dimensão Calendário/Tempo compatível com Azure SQL Database (T-SQL).
Padrão Kimball com ordenação ISO (YYYY-MM) e Membro Desconhecido (19000101).
*/

{{ config(materialized='table') }}

WITH e1(n) AS (
    SELECT 1 FROM (VALUES (1),(1),(1),(1),(1),(1),(1),(1),(1),(1)) AS t(n) -- 10 linhas
),
e2(n) AS (
    SELECT 1 FROM e1 a CROSS JOIN e1 b -- 100 linhas
),
e3(n) AS (
    SELECT 1 FROM e2 a CROSS JOIN e2 b -- 10.000 números gerados instantaneamente
),
tally(n) AS (
    SELECT ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 FROM e3
),
dates AS (
    SELECT DATEADD(DAY, n, CAST('2023-01-01' AS DATE)) AS data_dia
    FROM tally
    WHERE n <= DATEDIFF(DAY, '2023-01-01', '2026-12-31')
),

calendario AS (
    SELECT
        CAST(CONVERT(VARCHAR(8), data_dia, 112) AS INT) AS sk_data,
        data_dia AS dt_data,
        DATEPART(YEAR, data_dia) AS ano,
        DATEPART(QUARTER, data_dia) AS trimestre,
        DATEPART(MONTH, data_dia) AS mes,
        -- Padrão ISO: ordena naturalmente no tempo (ex: 2026-01)
        CONVERT(VARCHAR(7), data_dia, 120) AS ano_mes,
        FORMAT(data_dia, 'MM/yyyy') AS mes_ano,
        DATENAME(MONTH, data_dia) AS nome_mes,
        DATEPART(DAY, data_dia) AS dia,
        DATEPART(WEEKDAY, data_dia) AS dia_semana,
        CASE WHEN DATEPART(WEEKDAY, data_dia) IN (1, 7) THEN 1 ELSE 0 END AS fl_fim_semana
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