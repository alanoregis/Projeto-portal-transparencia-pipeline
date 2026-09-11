{{ config(materialized='table') }}

SELECT
    sk_portador,
    nome_portador
FROM {{ ref('dim_portadores') }}