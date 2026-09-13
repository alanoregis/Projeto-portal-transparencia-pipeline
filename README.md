# 🏛️ Pipeline de Engenharia de Dados: Gastos com Cartão Corporativo (CPGF - CGU)

[![Pipeline Portal da Transparência (Diário)](https://github.com/alanoregis/Projeto-portal-transparencia-pipeline/actions/workflows/pipeline_transparencia.yml/badge.svg)](https://github.com/alanoregis/Projeto-portal-transparencia-pipeline/actions/workflows/pipeline_transparencia.yml)
[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![dbt Version](https://img.shields.io/badge/dbt-1.12-orange.svg)](https://www.getdbt.com/)
[![Cloud Provider](https://img.shields.io/badge/cloud-Microsoft%20Azure-0078D4.svg)](https://azure.microsoft.com/)
[![Database](https://img.shields.io/badge/database-Azure%20SQL%20Serverless-blue.svg)](https://azure.microsoft.com/products/azure-sql/database/)
[![BI Tool](https://img.shields.io/badge/BI-Power%20BI-F2C811.svg)](https://powerbi.microsoft.com/)

Pipeline moderno de Engenharia de Dados ponta a ponta (End-to-End) para extração, tratamento, modelagem dimensional e detecção de anomalias nas despesas efetuadas com o **Cartão de Pagamento do Governo Federal (CPGF)**, utilizando dados públicos oficiais da **Controladoria-Geral da União (CGU)**.

O projeto adota os princípios da **Modern Data Stack** e **DataOps**, integrando ingestão declarativa com **dlthub (dlt)**, modelagem e testes de integridade com **dbt-sqlserver**, armazenamento analítico em nuvem no **Azure SQL Database (Serverless)** e esteira de automação diária via **GitHub Actions CI/CD**.

---

## 📐 1. Arquitetura da Solução

O fluxo foi concebido sob a premissa de desacoplamento, resiliência a falhas de API, garantia de qualidade antes da disponibilização analítica e custo operacional reduzido (FinOps):

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   ORQUESTRAÇÃO & CI/CD                                 │
│                   GitHub Actions Runner (Execução Diária às 01:00 BRT)                 │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
         ┌──────────────────────────────────┴──────────────────────────────────┐
         ▼                                                                     ▼
┌─────────────────────────────────┐                       ┌─────────────────────────────────┐
│        1. INGESTÃO (dlt)        │                       │       2. TRANSFORMAÇÃO (dbt)    │
│  - API Portal da Transparência  │                       │  - Limpeza e Padronização       │
│  - Paginação & Retry/Backoff    │                       │  - Modelagem Star Schema        │
│  - Carga Idempotente (Bronze)   │                       │  - Z-Score Estatístico (Anomalia│
└────────────────┬────────────────┘                       └────────────────┬────────────────┘
                 │                                                         │
                 ▼                                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        DATA WAREHOUSE: Azure SQL Database (Serverless)                 │
│                                                                                        │
│   [bronze]  ──►  [silver] (Staging + Dims/Fct)  ──►  [gold] (Star Schema Pronto para BI│
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                             CONSUMO ANALÍTICO & GOVERNANÇA                             │
│       Power BI Desktop / Service (Camada Semântica consumida pela role db_analista_gold)
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🏛️ 2. Arquitetura Medalhão e Modelagem Dimensional (Kimball)

A segregação dos dados segue o padrão medalhão dentro do mesmo catálogo lógico do Azure SQL Database, garantindo linhagem transparente:

### 🥉 Camada Bronze (`bronze`)
- **Tabela**: `bronze.cartoes_pagamento`
- **Responsabilidade**: Armazenamento bruto dos payloads JSON normalizados extraídos da API da CGU pelo `dlt`.
- **Características**: Schema evolution automático, preservação da granularidade original e inclusão de metadados técnicos de carga (`_dlt_load_id`, `_dlt_id`).

### 🥈 Camada Silver (`silver`)
- **Staging (`stg_cpgf_despesas`)**:
  - Padronização de tipos de dados (datas no padrão ANSI, valores monetários brasileiros convertidos para `DECIMAL(18,2)`).
  - Deduplicação determinística via `ROW_NUMBER() OVER (PARTITION BY id_transacao ORDER BY _dlt_load_id DESC)`.
  - Tratamento de valores ausentes/nulos e anonimização de dados sensíveis (PII).
- **Dimensões e Fato Intermediárias**:
  - `dim_data`: Calendário contínuo (2023–2026) gerado dinamicamente com nomes de meses em pt-BR e registro para datas não mapeadas (*Unknown Member - 19000101*).
  - `dim_orgaos`: Hierarquia governamental (Órgão Superior, Órgão Vinculado e Unidade Gestora).
  - `dim_favorecidos`: Estabelecimentos comerciais/fornecedores.
  - `dim_portadores`: Servidores públicos portadores do cartão.
  - `fct_gastos_cartao`: Tabela fato estrita contendo apenas chaves substitutas (`sk_*`) geradas via hash MD5 (`dbt_utils.generate_surrogate_key`) e métricas aditivas.

### 🥇 Camada Gold (`gold` - Star Schema Puro)
Camada final otimizada para o motor analítico do **Power BI** (VertiPaq) e consultas SQL de alta performance:

```
                      ┌───────────────────────┐
                      │     gold.dim_data     │
                      └───────────┬───────────┘
                                  │ (sk_data)
                                  ▼
┌────────────────────────┐  (sk_orgao)  ┌─────────────────────────────┐  (sk_favorecido)  ┌─────────────────────────────┐
│    gold.dim_orgaos     ├─────────────►│  gold.fct_gastos_cartao     │◄─────────────────┤    gold.dim_favorecidos     │
└────────────────────────┘              │                             │                   └─────────────────────────────┘
                                        │  - vl_transacao (DECIMAL)   │
┌────────────────────────┐  (sk_portador)  - media_orgao (DECIMAL)    │  (ordem_severidade)┌─────────────────────────────┐
│  gold.dim_portadores   ├─────────────►│  - z_score (FLOAT)          │◄─────────────────┤   gold.dim_nivel_alerta     │
└────────────────────────┘              │  - ordem_severidade (FK)    │                   └─────────────────────────────┘
                                        └─────────────────────────────┘
```

#### 🔍 Detecção Estatística de Anomalias (Z-Score)
Na tabela `fct_gastos_cartao`, cada transação é comparada contra o comportamento de despesas do respectivo ministério/órgão superior:
$$\text{Z-Score} = \frac{X - \mu_{\text{orgao}}}{\sigma_{\text{orgao}}}$$
- **CRÍTICO (`ordem_severidade = 3`)**: Transações com $\text{Z-Score} \ge 2.5$ ou valor absoluto $\ge \text{R\$} 40.000,00$.
- **MODERADO (`ordem_severidade = 2`)**: Transações com $\text{Z-Score} \ge 1.8$ ou valor absoluto $\ge \text{R\$} 15.000,00$.
- **NORMAL (`ordem_severidade = 1`)**: Transações dentro da variabilidade esperada do órgão.

---

## ⚖️ 3. Decisões de Arquitetura & Trade-offs de Engenharia

| Decisão Tomada | Alternativa Considerada | Racional Técnico & Trade-off |
| :--- | :--- | :--- |
| **Azure SQL Database (Serverless)** | VMs IaaS com SQL Server / Instâncias Provisionadas | **FinOps & Escalabilidade**: O modo Serverless com Auto-pause (1h) reduz o custo de vCore a zero quando inativo. Evita custo fixo mensal de instâncias 24/7 para um pipeline que executa em segundos de madrugada. |
| **GitHub Actions para Orquestração** | Apache Airflow gerenciado (Cloud Composer / ADF Managed) | **Custo & Simplicidade Operacional**: Um cluster gerenciado de Airflow custaria mais de US$ 100/mês. O GitHub Actions é gratuito (2.000 min/mês), versionado com o código (GitOps) e roda em menos de 1 minuto diário. |
| **dlthub (`dlt`) para Ingestão** | Scripts manuais com `requests` + `to_sql` do Pandas | **Resiliência e Idempotência**: O `dlt` gerencia paginação, schema inference, tipos nativos e carregamento transacional sem necessidade de criar tabelas DDL na mão. |
| **Consolidação de Favorecidos por Marca / Nome Fantasia** | Grão por CNPJ Completo de Filial | **Análise Executiva vs Detalhe Operacional**: Empresas como redes varejistas possuem múltiplos CNPJs para filiais distintas. Consolidar por marca/nome permite ao gestor de compras enxergar a exposição financeira total do governo perante um único grupo econômico. |
| **Foreign Key Numérica para Alertas (`ordem_severidade`)** | Strings de texto soltas na Fato | **Otimização de Armazenamento e Star Schema Puro**: Strings repetidas em milhões de linhas aumentam o tamanho da fato. A dimensão `dim_nivel_alerta` resolve a ordenação no Power BI (`NORMAL ➔ MODERADO ➔ CRÍTICO`) sem DAX complexo. |

---

## 🛡️ 4. Governança, Segurança & Qualidade de Dados (DataOps)

### Data Quality Gates (48 Testes Automatizados via `dbt test`)
O pipeline implementa barreiras automáticas de qualidade antes de qualquer consumo:
- **Testes de Unicidade (`unique`)**: Chaves primárias de todas as dimensões e identificador de transação da fato.
- **Testes de Não-Nulos (`not_null`)**: Chaves substitutas, métricas de transação e classificadores de alerta.
- **Testes de Integridade Referencial (`relationships`)**: Validação de chaves estrangeiras da `fct_gastos_cartao` contra todas as dimensões (`dim_data`, `dim_orgaos`, `dim_favorecidos`, `dim_portadores`, `dim_nivel_alerta`), impedindo registros órfãos.
- **Testes de Valores Aceitos (`accepted_values`)**: Garantia de integridade do domínio de severidade.

### Segurança Baseada em Funções (RBAC) & Menor Privilégio
O acesso analítico ao banco em nuvem é segregado:
- **Pipeline de Carga (`adminuser`)**: Acesso total para criação e atualização das camadas.
- **Analistas de BI (`db_analista_gold`)**: Role de banco com permissão estrita de `SELECT` apenas no schema `gold`. Os analistas não visualizam dados intermediários (`bronze`/`silver`) e não possuem permissão de escrita/exclusão.

---

## ⏱️ 5. Automação Diária e Notificações (GitHub Actions)

A esteira de dados executa diariamente através do workflow agendado:
- **Horário**: `04:00 UTC` (**01:00 da manhã no Horário de Brasília / Fortaleza - CE**).
- **Segurança**: Todas as credenciais de banco, chaves de API da CGU e senhas de app são gerenciadas via **GitHub Encrypted Secrets**.
- **Observabilidade**: 
  - ✅ **Sucesso**: Disparo de e-mail informativo com métricas da execução para a equipe de dados.
  - ❌ **Falha**: Alerta imediato com logs de rastreabilidade para intervenção rápida.

---

## 📁 6. Estrutura do Repositório

```text
Projeto-portal-transparencia-pipeline/
├── .github/
│   └── workflows/
│       └── pipeline_transparencia.yml   # Workflow agendado (CI/CD)
├── dbt_transparencia/                   # Projeto dbt-sqlserver
│   ├── dbt_project.yml                 # Configuração geral e flags do dbt
│   ├── packages.yml                    # Pacotes externos (dbt_utils)
│   ├── profiles.yml                    # Conexão parametrizada via env vars
│   ├── macros/
│   │   └── generate_schema_name.sql    # Macro de isolamento de schemas
│   └── models/
│       ├── bronze/
│       │   └── sources.yml             # Mapeamento da camada de ingestão
│       ├── silver/
│       │   ├── schema.yml              # Testes de integridade da Silver
│       │   ├── stg_cpgf_despesas.sql   # Tratamento, limpeza e deduplicação
│       │   ├── dim_data.sql            # Calendário padrão Kimball
│       │   ├── dim_orgaos.sql          # Hierarquia governamental
│       │   ├── dim_favorecidos.sql     # Favorecidos e fornecedores
│       │   ├── dim_portadores.sql      # Portadores de cartão
│       │   └── fct_gastos_cartao.sql   # Fato com surrogate keys
│       └── gold/
│           ├── schema.yml              # Testes relacionais da Gold
│           ├── gold_dim_data.sql       # Dimensão Data promovida
│           ├── gold_dim_orgaos.sql     # Dimensão Órgãos promovida
│           ├── gold_dim_favorecidos.sql# Estabelecimentos consolidados
│           ├── gold_dim_portadores.sql # Portadores autorizados
│           ├── gold_dim_nivel_alerta.sql# Matriz de criticidade de anomalia
│           └── gold_fct_gastos_cartao.sql# Fato final com Z-Score
├── ingestion/
│   ├── cgu_client.py                   # Cliente HTTP com paginação e backoff
│   ├── pipeline_transparencia.py       # Pipeline de ingestão declarativa dlt
│   └── sample_data.py                  # Gerador de dados para testes locais
├── Dockerfile                          # Container Linux Debian com driver ODBC
├── .dockerignore                       # Exclusão de artefatos no build
├── requirements.txt                    # Dependências do projeto Python
└── run_pipeline.py                     # Orquestrador local e em container
```

---

## 🚀 7. Como Executar Localmente

### Pré-requisitos
- Python 3.11+
- [Microsoft ODBC Driver 17 for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server)
- Gerenciador de pacotes `uv` ou `pip`

### Passo a Passo

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/alanoregis/Projeto-portal-transparencia-pipeline.git
   cd Projeto-portal-transparencia-pipeline
   ```

2. **Crie e ative o ambiente virtual:**
   ```bash
   uv venv
   .venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # Linux/macOS
   ```

3. **Instale as dependências:**
   ```bash
   uv pip install -r requirements.txt
   ```

4. **Configure o arquivo `.env` na raiz do projeto:**
   ```env
   AZURE_SQL_SERVER=seu-servidor.database.windows.net
   AZURE_SQL_DATABASE=sqldb-transparencia
   AZURE_SQL_USER=seu_usuario
   AZURE_SQL_PASSWORD=sua_senha
   AZURE_SQL_DRIVER=ODBC Driver 17 for SQL Server
   CGU_API_KEY=sua_chave_cgu
   INGESTION_MODE=api  # ou sample para testes offline
   EXTRACT_MES_EXTRATO_INICIO=01/2024
   EXTRACT_MES_EXTRATO_FIM=08/2026
   MAX_PAGES_PER_MONTH=50
   ```

5. **Execute a esteira completa:**
   ```bash
   python run_pipeline.py
   ```

---

## 👨‍💻 Autor
**Alano Regis**  
*Estudante de Engenharia de Dados & Cloud Computing*  
- LinkedIn: [linkedin.com/in/alanoregis](https://www.linkedin.com/in/alanoregis/)  
- GitHub: [@alanoregis](https://github.com/alanoregis)
