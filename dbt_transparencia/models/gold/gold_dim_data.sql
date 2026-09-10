{{ config(materialized='table') }}

SELECT * FROM {{ ref('dim_data') }}