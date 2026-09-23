# Changelog

Todas as alterações notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

---

## [1.2.0] - 2026-09-23

### Added
- **Suíte de Testes Unitários com pytest**: 33 testes automatizados cobrindo sanitização de dados, resiliência HTTP com mocks (timeout e erro 429) e detecção de erros transitórios de cold-start no Azure SQL Serverless (`test_azure_retry.py`).
- **CI Quality Gate**: Workflow do GitHub Actions (`ci_quality_gate.yml`) que bloqueia Pull Requests automaticamente em caso de falha de testes.

### Security
- **Sanitização de PII (LGPD)**: Pipeline de Expressões Regulares (`re.sub`) na ingestão para remover vazamentos de CPF e CNPJ no campo `nome_favorecido`, preservando a integridade de empresas que iniciam com dígitos (ex: *100 FRONTEIRA*, *3M*).

---

## [1.1.0] - 2026-09-17

### Added
- **Azure SQL Serverless**: Migração do storage analítico para nuvem com auto-pause de 1 hora para otimização de custos (FinOps).
- **Star Schema com Z-Score**: Camada Gold com tabela fato central (`fct_gastos_cartao`) e 5 dimensões com detecção estatística de anomalias particionada por Órgão Superior.
- **Governança RBAC**: Role `db_analista_gold` com permissão restrita de leitura na Gold para usuários do Power BI.
- **Orquestração Noturna**: Agendamento diário às 01:00 (horário de Fortaleza) via GitHub Actions com alertas por e-mail via Gmail SMTP.

### Changed
- Reescrita completa dos modelos dbt para dialeto T-SQL puro (Azure SQL).
- Implementação de Tally Table (Cross Join cartesiano) para a dimensão calendário `dim_data` contornando limites de recursão do SQL Server.

---

## [1.0.0] - 2026-09-04

### Added
- Pipeline inicial de extração da API da CGU com `dlt` (dlthub).
- Armazenamento inicial em banco colunar local com DuckDB.
- Modelagem inicial em camadas Staging e Silver com `dbt-duckdb`.
- Orquestrador local em Python (`run_pipeline.py`).