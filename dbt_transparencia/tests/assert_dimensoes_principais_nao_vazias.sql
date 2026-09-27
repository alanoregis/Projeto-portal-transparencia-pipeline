/*
  Teste de Volume Mínimo nas Dimensões
  Falha se qualquer uma das dimensões principais de negócio estiver com 0 registros.
  Retorna as dimensões que falharam.
*/
SELECT 'gold_dim_orgaos' AS dimensao_vazia
WHERE (SELECT COUNT(*) FROM {{ ref('gold_dim_orgaos') }}) = 0

UNION ALL

SELECT 'gold_dim_favorecidos' AS dimensao_vazia
WHERE (SELECT COUNT(*) FROM {{ ref('gold_dim_favorecidos') }}) = 0

UNION ALL

SELECT 'gold_dim_portadores' AS dimensao_vazia
WHERE (SELECT COUNT(*) FROM {{ ref('gold_dim_portadores') }}) = 0
