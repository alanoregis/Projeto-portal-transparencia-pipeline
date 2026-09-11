{{ config(materialized='table') }}

SELECT 
    sk_favorecido,
    nome_favorecido
FROM {{ ref('dim_favorecidos') }}