{{ config(materialized='table') }}

WITH staging AS (
    SELECT * FROM {{ ref('stg_cpgf_despesas') }}
),

distinct_favorecidos AS (
    SELECT
        nome_favorecido,
        cgc_favorecido,
        -- Extrai a raiz do CNPJ (8 primeiros dígitos antes da barra de filial)
        CASE 
            WHEN cgc_favorecido LIKE '%/%' THEN 
                SUBSTRING(cgc_favorecido, 1, CHARINDEX('/', cgc_favorecido) - 1)
            ELSE cgc_favorecido 
        END AS cnpj_raiz,
        _dlt_load_id,
        ROW_NUMBER() OVER (
            PARTITION BY nome_favorecido 
            ORDER BY _dlt_load_id DESC
        ) AS rn
    FROM staging
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['nome_favorecido']) }} AS sk_favorecido,
    nome_favorecido,
    cnpj_raiz,
    cgc_favorecido AS cgc_exemplo_filial
FROM distinct_favorecidos
WHERE rn = 1