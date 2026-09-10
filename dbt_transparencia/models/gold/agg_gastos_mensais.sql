/*
Camada Gold: Agregação temporal de gastos mensais por órgão.
Ordenação cronológica estrita por ano e mês.
*/

{{ config(materialized='table') }}

WITH base AS (
    SELECT
        d.ano,
        d.mes,
        d.ano_mes,
        d.mes_ano,
        o.nome_orgao_superior,
        f.vl_transacao
    FROM {{ ref('fct_gastos_cartao') }} f
    JOIN {{ ref('dim_data') }} d ON f.sk_data = d.sk_data
    JOIN {{ ref('dim_orgaos') }} o ON f.sk_orgao = o.sk_orgao
)

SELECT
    ano_mes,
    mes_ano,
    nome_orgao_superior,
    SUM(vl_transacao)::DECIMAL(18, 2) AS total_gasto_mes,
    COUNT(*) AS total_transacoes_mes,
    AVG(vl_transacao)::DECIMAL(18, 2) AS ticket_medio_mes
FROM base
GROUP BY ano, mes, ano_mes, mes_ano, nome_orgao_superior
ORDER BY ano ASC, mes ASC, total_gasto_mes DESC