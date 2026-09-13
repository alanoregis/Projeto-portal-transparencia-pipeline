{{ config(materialized='table') }}

WITH staging AS (
    SELECT * FROM {{ ref('stg_cpgf_despesas') }}
),

distinct_orgaos AS (
    SELECT
        cod_orgao_superior,
        nome_orgao_superior,
        cod_orgao_vinculado,
        nome_orgao_vinculado,
        cod_unidade_gestora,
        nome_unidade_gestora,
        _dlt_load_id,
        ROW_NUMBER() OVER (
            PARTITION BY cod_orgao_superior, cod_orgao_vinculado, cod_unidade_gestora
            ORDER BY _dlt_load_id DESC
        ) AS rn
    FROM staging
)

SELECT
    {{ dbt_utils.generate_surrogate_key([
        'cod_orgao_superior',
        'cod_orgao_vinculado',
        'cod_unidade_gestora'
    ]) }} AS sk_orgao,
    cod_orgao_superior,
    nome_orgao_superior,
    cod_orgao_vinculado,
    nome_orgao_vinculado,
    cod_unidade_gestora,
    nome_unidade_gestora
FROM distinct_orgaos
WHERE rn = 1