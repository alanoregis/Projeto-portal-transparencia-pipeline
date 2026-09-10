/*
  Camada Gold — Fato de Gastos com Cartão de Pagamento.
  Star Schema puro com Z-score e classificação de alerta por órgão.
  Referencia as dims da própria Gold (não da Silver diretamente).
*/

{{ config(materialized='table') }}

WITH base AS (
    SELECT
        f.id_transacao,
        f.sk_data,
        f.sk_orgao,
        f.sk_favorecido,
        f.sk_portador,
        f.vl_transacao,
        o.nome_orgao_superior
    FROM {{ ref('fct_gastos_cartao') }} f          -- silver.fct_gastos_cartao
    JOIN {{ ref('dim_orgaos') }} o ON f.sk_orgao = o.sk_orgao
),

stats_por_orgao AS (
    SELECT
        nome_orgao_superior,
        AVG(vl_transacao)    AS media_gasto_orgao,
        STDDEV(vl_transacao) AS stddev_gasto_orgao
    FROM base
    GROUP BY nome_orgao_superior
),

scored AS (
    SELECT
        b.id_transacao,
        b.sk_data,
        b.sk_orgao,
        b.sk_favorecido,
        b.sk_portador,
        b.vl_transacao::DECIMAL(18,2)                        AS vl_transacao,
        s.media_gasto_orgao::DECIMAL(18,2)                   AS media_orgao,
        CASE
            WHEN COALESCE(s.stddev_gasto_orgao, 0) = 0 THEN 0.0
            ELSE ROUND(
                (b.vl_transacao - s.media_gasto_orgao) / s.stddev_gasto_orgao,
                2
            )
        END AS z_score
    FROM base b
    JOIN stats_por_orgao s ON b.nome_orgao_superior = s.nome_orgao_superior
)

SELECT
    id_transacao,
    sk_data,
    sk_orgao,
    sk_favorecido,
    sk_portador,
    vl_transacao,
    media_orgao,
    z_score,
    CASE
        WHEN z_score >= 2.5 OR vl_transacao >= 40000.0 THEN 3
        WHEN z_score >= 1.8 OR vl_transacao >= 15000.0 THEN 2
        ELSE 1
    END AS ordem_severidade
FROM scored