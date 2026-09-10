{{ config(materialized='table') }}

WITH base AS (
    SELECT
        o.nome_orgao_superior,
        f.vl_transacao,
        f.sk_portador,
        f.sk_favorecido
    FROM {{ ref('fct_gastos_cartao') }} f
    JOIN {{ ref('dim_orgaos') }} o ON f.sk_orgao = o.sk_orgao
),

orgao_agg AS (
    SELECT
        nome_orgao_superior,
        SUM(vl_transacao)::DECIMAL(18, 2) AS total_gasto,
        COUNT(*) AS total_transacoes,
        AVG(vl_transacao)::DECIMAL(18, 2) AS ticket_medio,
        COUNT(DISTINCT sk_portador) AS qtd_portadores,
        COUNT(DISTINCT sk_favorecido) AS qtd_favorecidos
    FROM base
    GROUP BY nome_orgao_superior
),

total_geral AS (
    SELECT SUM(total_gasto) AS grand_total FROM orgao_agg
)

SELECT
    a.nome_orgao_superior,
    a.total_gasto,
    a.total_transacoes,
    a.ticket_medio,
    a.qtd_portadores,
    a.qtd_favorecidos,
    ROUND((a.total_gasto / t.grand_total) * 100, 2) AS pct_gasto_nacional
FROM orgao_agg a
CROSS JOIN total_geral t
ORDER BY a.total_gasto DESC