{{ config(materialized='table', alias='dim_portadores') }}

SELECT
    sk_portador,
    nome_portador
FROM {{ ref('dim_portadores') }}