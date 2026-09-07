/*
Dimensão de Favorecidos / Estabelecimentos Comerciais.
Padrão Industrial com blindagem total contra NULLs (COALESCE + NULLIF).
*/

{{ config(materialized='table') }}

WITH staging AS (
    SELECT * FROM {{ ref('stg_cpgf_despesas') }}
),

prep AS (
    SELECT
        cgc_favorecido,
        nome_favorecido,
        -- Chave natural à prova de falhas: se CGC e Nome forem nulos ou 'NAO INFORMADO', cai no membro padronizado
        COALESCE(
            NULLIF(TRIM(cgc_favorecido), 'NAO INFORMADO'),
            NULLIF(TRIM(nome_favorecido), 'NAO INFORMADO'),
            'FAVORECIDO_NAO_IDENTIFICADO'
        ) AS chave_dedup,
        _dlt_load_id
    FROM staging
),

distinct_favorecidos AS (
    SELECT
        cgc_favorecido,
        nome_favorecido,
        chave_dedup
    FROM prep
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY chave_dedup 
        ORDER BY _dlt_load_id DESC
    ) = 1
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['chave_dedup']) }} AS sk_favorecido,
    cgc_favorecido,
    nome_favorecido
FROM distinct_favorecidos