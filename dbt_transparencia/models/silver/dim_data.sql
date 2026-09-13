/*
Dimensão Calendário/Tempo compatível com Azure SQL Database (T-SQL).
Padrão Kimball com ordenação ISO (YYYY-MM), nomes em Português e Membro Desconhecido (19000101).
*/

{{ config(materialized='table') }}

WITH n1(n) AS (
    SELECT 1 FROM (VALUES (1),(1),(1),(1),(1),(1),(1),(1),(1),(1)) v(n)
),
n2(n) AS (
    SELECT 1 FROM n1 a CROSS JOIN n1 b
),
n3(n) AS (
    SELECT 1 FROM n2 a CROSS JOIN n2 b
),
numbers AS (
    SELECT ROW_NUMBER() OVER (ORDER BY (SELECT 1)) - 1 AS num
    FROM n3
),
dates AS (
    SELECT DATEADD(DAY, num, CAST('2023-01-01' AS DATE)) AS dt_data
    FROM numbers
    WHERE num <= DATEDIFF(DAY, '2023-01-01', '2026-12-31')
),

calendario AS (
    SELECT
        CAST(CONVERT(VARCHAR(8), dt_data, 112) AS INT) AS sk_data,
        dt_data,
        DATEPART(YEAR, dt_data) AS ano,
        DATEPART(QUARTER, dt_data) AS trimestre,
        DATEPART(MONTH, dt_data) AS mes,
        CONVERT(VARCHAR(7), dt_data, 120) AS ano_mes,
        FORMAT(dt_data, 'MM/yyyy') AS mes_ano,
        -- Nome do mês em Português brasileiro com inicial maiúscula
        UPPER(LEFT(FORMAT(dt_data, 'MMMM', 'pt-BR'), 1)) + SUBSTRING(FORMAT(dt_data, 'MMMM', 'pt-BR'), 2, 50) AS nome_mes,
        DATEPART(DAY, dt_data) AS dia,
        DATEPART(WEEKDAY, dt_data) AS dia_semana,
        CASE WHEN DATEPART(WEEKDAY, dt_data) IN (1, 7) THEN 1 ELSE 0 END AS fl_fim_semana
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