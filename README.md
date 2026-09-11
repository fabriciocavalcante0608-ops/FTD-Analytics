# FTD Analytics

Pipeline de validação e análise de lançamentos fiscais (Fatura/Título/Documento), construído para substituir uma conferência manual em Excel por um processo automatizado de ponta a ponta: **Python → SQL → Power BI**.

## O problema

O processo fiscal recebia mensalmente uma planilha com centenas de lançamentos (notas de obras, fornecedores, valores) e precisava:

- Identificar divergências (CNPJ, data de emissão, valor, número de documento)
- Consolidar indicadores de erro por obra e por tipo
- Repetir esse trabalho manualmente todo mês, em uma planilha que crescia sem controle de versão dos dados

A conferência manual também tinha erros de contagem — na base de referência, dois tipos de erro estavam trocados (CNPJ e Data) por conta de um lançamento com erro combinado ("Data de emissão / CNPJ divergente") contado apenas uma vez em vez de nas duas categorias.

## O que este projeto faz

1. **Python (`python/`)** — lê a exportação mensal, classifica cada lançamento (`com erro` / `sem erro`) e o tipo de erro (inclusive combinações como "Data+CNPJ"), acumula num histórico mês a mês sem duplicar registros, e gera indicadores (taxa de erro, erros por obra, evolução mensal).
2. **SQL (`sql/`)** — modela os dados num esquema estrela (`Fato_Lancamentos` + dimensões `Obra`, `Credor`, `Mês`, `Tipo_Erro`), com uma tabela-ponte para lançamentos com múltiplos tipos de erro simultâneos, sem duplicar a linha financeira.
3. **Power BI** — dashboard com KPIs (total de lançamentos, taxa de acurácia, valor em divergência) e dois gráficos com destaque visual automático (escala de cor) para as obras e tipos de erro mais críticos. O arquivo `.pbix` não é publicado (ver nota sobre dados); o resultado fica documentado abaixo.

![Dashboard FTD Analytics](docs/screenshots/Analytics.png)
![Painel de erros por obra e tipo](docs/screenshots/Painel.png)

## Arquitetura

```
Excel (exportação mensal)
        │
        ▼
  Python + pandas
  (classificação, dedup, acumulação)
        │
        ├──► FTD_Historico.xlsx (base acumulada)
        │
        ▼
  SQLite (schema.sql + etl_sql.py)
  (modelo estrela: fato + dimensões)
        │
        ▼
  Excel de saída (uma aba por tabela)
        │
        ▼
    Power BI
  (relacionamentos + medidas DAX + dashboard)
```

## Estrutura do repositório

```
FTD-Analytics/
├── python/
│   └── Automatizacao.py        # ETL mensal: classificação, dedup, histórico acumulado
├── sql/
│   ├── schema.sql               # DDL do modelo dimensional (esquema estrela)
│   └── etl_sql.py                # Popula o SQLite a partir do histórico e roda consultas
├── docs/
│   └── screenshots/              # Prints do dashboard Power BI
└── README.md
```

## Modelo de dados

- `Dim_Obra`, `Dim_Credor`, `Dim_Mes`, `Dim_Tipo_Erro` — dimensões
- `Fato_Lancamentos` — um registro por lançamento fiscal
- `Fato_Lancamento_Erro` — tabela-ponte: permite que um lançamento tenha 0, 1 ou vários tipos de erro sem duplicar a linha financeira na fato

## Principais indicadores

| Indicador | Cálculo |
|---|---|
| Taxa de acurácia | `(Total - Com erro) / Total` |
| Valor em divergência | Soma do valor de lançamentos com erro |
| Erros por tipo | Contagem via tabela-ponte, não via fato (evita subcontagem em erros combinados) |

## Como rodar

```bash
# 1. Ambiente
uv venv
uv pip install pandas openpyxl

# 2. Gerar o histórico acumulado a partir da exportação do mês
uv run python python/Automatizacao.py

# 3. Popular o modelo SQL e rodar as consultas de análise
uv run python sql/etl_sql.py

# 4. Importar o Excel gerado (uma aba por tabela) no Power BI e recriar
#    os relacionamentos e medidas descritos abaixo
```

## Nota sobre os dados

Este repositório contém apenas **código**. Nenhum dado real (exportações fiscais, histórico acumulado, banco populado, ou o arquivo `.pbix`) é versionado — veja `.gitignore`. O `.pbix` não é publicado porque o Power BI embute o banco de dados inteiro dentro do arquivo, incluindo nomes reais de obras e fornecedores; por isso o dashboard é documentado aqui só via capturas de tela (`docs/screenshots/`), com identificadores anonimizados.

## Roadmap

- [ ] Score de qualidade de dados por dimensão (CNPJ, Data, Valor, Documento)
- [ ] Dashboard de eficiência do processo fiscal (tempo de conferência, retrabalho)
- [ ] Migrar o SQLite local para um banco compartilhado (Postgres) quando o histórico crescer

## Stack

`Python` · `pandas` · `SQL (SQLite)` · `Power BI` · `DAX`

---

Projeto pessoal de portfólio, construído a partir de um processo real de conferência fiscal, com dados anonimizados para publicação.
