{{ config(materialized='table') }}

WITH staging AS (
    SELECT * FROM {{ ref('stg_cpgf_despesas') }}
),

distinct_portadores AS (
    SELECT
        nome_portador,
        cpf_portador,
        _dlt_load_id,
        ROW_NUMBER() OVER (
            PARTITION BY COALESCE(NULLIF(cpf_portador, 'NAO INFORMADO'), nome_portador)
            ORDER BY _dlt_load_id DESC
        ) AS rn
    FROM staging
)

SELECT
    {{ dbt_utils.generate_surrogate_key(["COALESCE(NULLIF(cpf_portador, 'NAO INFORMADO'), nome_portador)"]) }} AS sk_portador,
    nome_portador,
    cpf_portador
FROM distinct_portadores
WHERE rn = 1