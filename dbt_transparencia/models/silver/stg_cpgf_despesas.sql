/*
Modelo Staging: Limpeza, padronização de tipos e tratamento da camada Bronze.
Compatível com Azure SQL Database (T-SQL).
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
            WHEN CAST(mes_extrato AS VARCHAR(20)) LIKE '%/%' THEN 
                SUBSTRING(CAST(mes_extrato AS VARCHAR(20)), CHARINDEX('/', CAST(mes_extrato AS VARCHAR(20))) + 1, 4)
                + '-' 
                + RIGHT('00' + SUBSTRING(CAST(mes_extrato AS VARCHAR(20)), 1, CHARINDEX('/', CAST(mes_extrato AS VARCHAR(20))) - 1), 2)
            WHEN LEN(CAST(mes_extrato AS VARCHAR(20))) = 6 THEN
                SUBSTRING(CAST(mes_extrato AS VARCHAR(20)), 1, 4) + '-' + SUBSTRING(CAST(mes_extrato AS VARCHAR(20)), 5, 2)
            ELSE CAST(mes_extrato AS VARCHAR(20))
        END AS ano_mes_extrato,

        -- Conversão robusta de data no T-SQL (103 = DD/MM/YYYY, 120/23 = YYYY-MM-DD)
        COALESCE(
            TRY_CONVERT(DATE, CAST(data_transacao AS VARCHAR(20)), 103),
            TRY_CONVERT(DATE, CAST(data_transacao AS VARCHAR(20)), 120),
            TRY_CONVERT(DATE, '01/' + CAST(mes_extrato AS VARCHAR(20)), 103),
            CAST('1900-01-01' AS DATE)
        ) AS dt_transacao,

        -- Conversão robusta de valor monetário (formato brasileiro '1.250,50' para numérico)
        TRY_CAST(
            REPLACE(REPLACE(CAST(valor_transacao AS VARCHAR(50)), '.', ''), ',', '.') AS DECIMAL(18,2)
        ) AS vl_transacao,

        -- Dados do Estabelecimento / Favorecido
        UPPER(LTRIM(RTRIM(COALESCE(estabelecimento__nome, 'NAO INFORMADO')))) AS nome_favorecido,
        LTRIM(RTRIM(COALESCE(estabelecimento__cgc, 'NAO INFORMADO'))) AS cgc_favorecido,

        -- Dados do Portador do Cartão
        UPPER(LTRIM(RTRIM(COALESCE(portador__nome, 'NAO INFORMADO')))) AS nome_portador,
        LTRIM(RTRIM(COALESCE(portador__cpf, 'NAO INFORMADO'))) AS cpf_portador,

        -- Estrutura Governamental
        LTRIM(RTRIM(COALESCE(CAST(orgao_superior__codigo AS VARCHAR(20)), '00000'))) AS cod_orgao_superior,
        UPPER(LTRIM(RTRIM(COALESCE(orgao_superior__nome, 'OUTROS / NAO IDENTIFICADO')))) AS nome_orgao_superior,

        LTRIM(RTRIM(COALESCE(CAST(orgao_vinculado__codigo AS VARCHAR(20)), '00000'))) AS cod_orgao_vinculado,
        UPPER(LTRIM(RTRIM(COALESCE(orgao_vinculado__nome, 'OUTROS / NAO IDENTIFICADO')))) AS nome_orgao_vinculado,

        LTRIM(RTRIM(COALESCE(CAST(unidade_gestora__codigo AS VARCHAR(20)), '00000'))) AS cod_unidade_gestora,
        UPPER(LTRIM(RTRIM(COALESCE(unidade_gestora__nome, 'OUTROS / NAO IDENTIFICADO')))) AS nome_unidade_gestora,

        -- Tipo de Cartão
        UPPER(LTRIM(RTRIM(COALESCE(tipo_cartao__descricao, 'CPGF - CARTAO DE PAGAMENTO')))) AS desc_tipo_cartao,

        -- Metadados de linhagem do dlt
        _dlt_load_id,
        _dlt_id

    FROM source_data
    WHERE id IS NOT NULL
),

cleaned AS (
    SELECT *
    FROM parsed
    WHERE ano_mes_extrato BETWEEN '2024-01' AND '2026-12'
),

ranked AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (PARTITION BY id_transacao ORDER BY _dlt_load_id DESC) AS rn
    FROM cleaned
)

SELECT 
    id_transacao,
    ano_mes_extrato,
    dt_transacao,
    vl_transacao,
    nome_favorecido,
    cgc_favorecido,
    nome_portador,
    cpf_portador,
    cod_orgao_superior,
    nome_orgao_superior,
    cod_orgao_vinculado,
    nome_orgao_vinculado,
    cod_unidade_gestora,
    nome_unidade_gestora,
    desc_tipo_cartao,
    _dlt_load_id,
    _dlt_id
FROM ranked
WHERE rn = 1