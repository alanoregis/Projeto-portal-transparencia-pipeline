/*
Tabela Fato de Gastos com Cartão de Pagamento (CPGF).
Star Schema Puro (Kimball).
*/

{{ config(materialized='table') }}

WITH staging AS (
    SELECT * FROM {{ ref('stg_cpgf_despesas') }}
)

SELECT
    s.id_transacao,
    -- FK para dim_data (formato YYYYMMDD)
    COALESCE(CAST(strftime(s.dt_transacao, '%Y%m%d') AS INTEGER), 19000101) AS sk_data,
    -- FK para dim_orgaos
    {{ dbt_utils.generate_surrogate_key([
        's.cod_orgao_superior',
        's.cod_orgao_vinculado',
        's.cod_unidade_gestora'
    ]) }} AS sk_orgao,
    -- FK para dim_favorecidos
    {{ dbt_utils.generate_surrogate_key(['s.nome_favorecido']) }} AS sk_favorecido,
    -- FK para dim_portadores
    {{ dbt_utils.generate_surrogate_key([
        "COALESCE(NULLIF(s.cpf_portador, 'NAO INFORMADO'), s.nome_portador)"
    ]) }} AS sk_portador,
    -- Métrica Numérica
    s.vl_transacao,
    s.desc_tipo_cartao,
    s._dlt_load_id
FROM staging s