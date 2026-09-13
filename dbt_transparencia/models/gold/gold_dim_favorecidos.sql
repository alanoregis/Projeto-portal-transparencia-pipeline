{{ config(materialized='table', alias='dim_favorecidos') }}

SELECT 
    sk_favorecido,
    nome_favorecido
FROM {{ ref('dim_favorecidos') }}