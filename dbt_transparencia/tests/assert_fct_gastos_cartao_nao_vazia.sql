/*
  Teste de Volume Mínimo (Data Contract)
  Falha se a tabela fato gold_fct_gastos_cartao estiver vazia (0 registros).
  Retorna 1 linha caso esteja vazia, fazendo o dbt test falhar.
*/
SELECT 
    1 AS falha,
    'gold_fct_gastos_cartao vazia (0 registros)' AS motivo
FROM (
    SELECT COUNT(*) AS total 
    FROM {{ ref('gold_fct_gastos_cartao') }}
) t
WHERE t.total = 0
