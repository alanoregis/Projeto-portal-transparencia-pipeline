{{ config(materialized='table', alias='dim_orgaos') }}

SELECT * FROM {{ ref('dim_orgaos') }}