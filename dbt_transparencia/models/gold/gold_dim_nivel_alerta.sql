/*
  Camada Gold — Dimensão de Nível de Alerta.
  Tabela estática com ordem de severidade para ordenação correta no Power BI.
*/

{{ config(materialized='table') }}

SELECT
    1                                                              AS ordem_severidade,
    'NORMAL'                                                       AS nivel_alerta,
    'Transacao dentro da variacao esperada'                        AS motivo_alerta
UNION ALL
SELECT
    2,
    'MODERADO',
    'Gasto moderadamente acima da media do orgao (> 1.8 sigma ou > R$ 15k)'
UNION ALL
SELECT
    3,
    'CRITICO',
    'Gasto significativamente acima do desvio padrao do orgao (> 2.5 sigma ou > R$ 40k)'