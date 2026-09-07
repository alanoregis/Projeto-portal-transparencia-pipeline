/*
Tabela Fato de Gastos com Cartão de Pagamento (CPGF).
Padrão Industrial com dbt_utils e blindagem de integridade referencial.
*/

{{ config(materialized='table') }}

WITH staging AS (
    SELECT * FROM {{ ref('stg_cpgf_despesas') }}
),

prep AS (
    SELECT
        *,
        -- Mesma chave_dedup usada na dimensão para garantir junção 100% perfeita
        COALESCE(
            NULLIF(TRIM(cgc_favorecido), 'NAO INFORMADO'),
            NULLIF(TRIM(nome_favorecido), 'NAO INFORMADO'),
            'FAVORECIDO_NAO_IDENTIFICADO'
        ) AS chave_dedup_favorecido
    FROM staging
)

SELECT
    id_transacao,
    {{ dbt_utils.generate_surrogate_key([
        'cod_orgao_superior',
        'cod_orgao_vinculado',
        'cod_unidade_gestora'
    ]) }} AS sk_orgao,
    {{ dbt_utils.generate_surrogate_key(['chave_dedup_favorecido']) }} AS sk_favorecido,
    dt_transacao,
    ano_mes_extrato,
    vl_transacao,
    nome_portador,
    cpf_portador,
    desc_tipo_cartao,
    _dlt_load_id
FROM prep