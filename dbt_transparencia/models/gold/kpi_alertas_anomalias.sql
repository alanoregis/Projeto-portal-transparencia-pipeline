{{ config(materialized='table') }}

WITH base AS (
    SELECT
        f.id_transacao,
        d.dt_data AS dt_transacao,
        d.mes_ano AS ano_mes_extrato,
        o.nome_orgao_superior,
        o.nome_unidade_gestora,
        fav.nome_favorecido,
        fav.cnpj_raiz AS cgc_favorecido,
        p.nome_portador,
        f.vl_transacao
    FROM {{ ref('fct_gastos_cartao') }} f
    JOIN {{ ref('dim_data') }} d ON f.sk_data = d.sk_data
    JOIN {{ ref('dim_orgaos') }} o ON f.sk_orgao = o.sk_orgao
    JOIN {{ ref('dim_favorecidos') }} fav ON f.sk_favorecido = fav.sk_favorecido
    JOIN {{ ref('dim_portadores') }} p ON f.sk_portador = p.sk_portador
),

stats_por_orgao AS (
    SELECT
        nome_orgao_superior,
        AVG(vl_transacao) AS media_gasto_orgao,
        STDDEV(vl_transacao) AS stddev_gasto_orgao
    FROM base
    GROUP BY nome_orgao_superior
),

scored AS (
    SELECT
        b.*,
        s.media_gasto_orgao,
        s.stddev_gasto_orgao,
        CASE
            WHEN COALESCE(s.stddev_gasto_orgao, 0) = 0 THEN 0.0
            ELSE ROUND((b.vl_transacao - s.media_gasto_orgao) / s.stddev_gasto_orgao, 2)
        END AS z_score
    FROM base b
    JOIN stats_por_orgao s ON b.nome_orgao_superior = s.nome_orgao_superior
)

SELECT
    id_transacao,
    dt_transacao,
    ano_mes_extrato,
    nome_orgao_superior,
    nome_unidade_gestora,
    nome_favorecido,
    cgc_favorecido,
    nome_portador,
    vl_transacao,
    media_gasto_orgao::DECIMAL(18, 2) AS media_orgao,
    z_score,
    CASE
        WHEN z_score >= 2.5 OR vl_transacao >= 40000.0 THEN 'CRITICO'
        WHEN z_score >= 1.8 OR vl_transacao >= 15000.0 THEN 'MODERADO'
        ELSE 'NORMAL'
    END AS nivel_alerta,
    CASE
        WHEN z_score >= 2.5 OR vl_transacao >= 40000.0 THEN 'Gasto significativamente acima do desvio padrao do orgao (> 2.5 sigma ou > R$ 40k)'
        WHEN z_score >= 1.8 OR vl_transacao >= 15000.0 THEN 'Gasto moderadamente acima da media do orgao (> 1.8 sigma ou > R$ 15k)'
        ELSE 'Transacao dentro da variacao esperada'
    END AS motivo_alerta
FROM scored
ORDER BY vl_transacao DESC