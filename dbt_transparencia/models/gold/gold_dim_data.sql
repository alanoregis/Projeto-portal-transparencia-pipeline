{{ config(materialized='table', alias='dim_data') }}

SELECT * FROM {{ ref('dim_data') }}