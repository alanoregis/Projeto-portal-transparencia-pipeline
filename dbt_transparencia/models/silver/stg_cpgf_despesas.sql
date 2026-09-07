/*
Modelo Staging: Limpeza, padronização de tipos e tratamento da camada Bronze.
Filtro de período: 2024-01 a 2026-12.
*/

{{ config(materialized='view') }}

WITH source_data AS (
    SELECT * FROM {{ source('bronze', 'cartoes_pagamento') }}
),

parsed AS (
    SELECT
        id AS id_transacao,

        -- Padronização de Ano-Mês para formato YYYY-MM (ex: 2026-01)
        CASE 
            WHEN mes_extrato::VARCHAR LIKE '%/%' THEN 
                SPLIT_PART(mes_extrato::VARCHAR, '/', 2) || '-' || LPAD(SPLIT_PART(mes_extrato::VARCHAR, '/', 1), 2, '0')
            WHEN LENGTH(mes_extrato::VARCHAR) = 6 THEN
                SUBSTRING(mes_extrato::VARCHAR, 1, 4) || '-' || SUBSTRING(mes_extrato::VARCHAR, 5, 2)
            ELSE mes_extrato::VARCHAR
        END AS ano_mes_extrato,

        -- Conversão robusta de data (suporta 'DD/MM/YYYY' ou 'YYYY-MM-DD')
        COALESCE(
            TRY_STRPTIME(data_transacao::VARCHAR, '%d/%m/%Y')::DATE,
            TRY_CAST(data_transacao::VARCHAR AS DATE)
        ) AS dt_transacao,

        -- Conversão robusta de valor monetário (formato brasileiro '1.250,50' para numérico)
        TRY_CAST(
            REPLACE(REPLACE(valor_transacao::VARCHAR, '.', ''), ',', '.') AS DECIMAL(18,2)
        ) AS vl_transacao,

        -- Dados do Estabelecimento / Favorecido
        UPPER(TRIM(COALESCE(estabelecimento__nome, 'NAO INFORMADO'))) AS nome_favorecido,
        TRIM(COALESCE(estabelecimento__cgc, 'NAO INFORMADO')) AS cgc_favorecido,

        -- Dados do Portador do Cartão
        UPPER(TRIM(COALESCE(portador__nome, 'NAO INFORMADO'))) AS nome_portador,
        TRIM(COALESCE(portador__cpf, 'NAO INFORMADO')) AS cpf_portador,

        -- Estrutura Governamental
        TRIM(COALESCE(orgao_superior__codigo::VARCHAR, '00000')) AS cod_orgao_superior,
        UPPER(TRIM(COALESCE(orgao_superior__nome, 'OUTROS / NAO IDENTIFICADO'))) AS nome_orgao_superior,

        TRIM(COALESCE(orgao_vinculado__codigo::VARCHAR, '00000')) AS cod_orgao_vinculado,
        UPPER(TRIM(COALESCE(orgao_vinculado__nome, 'OUTROS / NAO IDENTIFICADO'))) AS nome_orgao_vinculado,

        TRIM(COALESCE(unidade_gestora__codigo::VARCHAR, '00000')) AS cod_unidade_gestora,
        UPPER(TRIM(COALESCE(unidade_gestora__nome, 'OUTROS / NAO IDENTIFICADO'))) AS nome_unidade_gestora,

        -- Tipo de Cartão
        UPPER(TRIM(COALESCE(tipo_cartao__descricao, 'CPGF - CARTAO DE PAGAMENTO'))) AS desc_tipo_cartao,

        -- Metadados de linhagem do dlt
        _dlt_load_id,
        _dlt_id

    FROM source_data
    WHERE id IS NOT NULL
),

cleaned AS (
    SELECT *
    FROM parsed
    -- Filtro de período: 2024-01 até 2026-12 (comparação lexicográfica funciona em YYYY-MM)
    WHERE ano_mes_extrato BETWEEN '2024-01' AND '2026-12'
)

SELECT * FROM cleaned
QUALIFY ROW_NUMBER() OVER (PARTITION BY id_transacao ORDER BY _dlt_load_id DESC) = 1