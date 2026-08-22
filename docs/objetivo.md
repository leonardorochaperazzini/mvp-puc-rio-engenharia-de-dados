# Objetivo do MVP — Engenharia de Dados

> **Documento append-only.** Escrito e versionado **antes** de qualquer coleta ou
> transformação de dados, conforme exigido pela disciplina. Nenhuma pergunta é removida
> ao longo do trabalho, mesmo que não seja respondida — o atingimento é discutido na
> **Autoavaliação** (ver `README.md`).

---

## 1. Problema

A cidade de Chicago disponibiliza publicamente o registro de todas as ocorrências
criminais. Esses dados brutos, porém, chegam num formato transacional (uma linha por
ocorrência, com 22 atributos heterogêneos) que **não é adequado para análise**: não há
dimensões consolidadas de tempo/local/tipo, há duplicidades e valores inválidos, e não há
enriquecimento com o contexto socioeconômico dos bairros.

**Este MVP constrói um pipeline de dados na nuvem** (Databricks) que coleta, limpa, modela
(esquema estrela) e carrega esses dados num Data Warehouse, permitindo responder perguntas
de negócio sobre **padrões de criminalidade e de prisão em Chicago** via SQL e dashboards.

O objetivo **não é** treinar modelos de Machine Learning (isso foi feito nos MVPs 1 e 2);
é entregar uma **plataforma analítica confiável, documentada e consultável**.

---

## 2. Perguntas de negócio

As quatro primeiras dão continuidade às hipóteses (H1–H4) investigadas nos MVPs anteriores,
agora respondidas sobre um Data Warehouse dimensional. As três últimas são **novas**,
habilitadas pelo enriquecimento com fontes externas (join).

| #    | Pergunta | Origem |
|------|----------|--------|
| BQ1  | Quais são os tipos de crime mais frequentes e qual a **taxa de prisão por tipo**? | H1 |
| BQ2  | **Crimes domésticos** têm taxa de prisão diferente dos não domésticos? | H2 |
| BQ3  | Existe **padrão temporal** (hora do dia, turno, dia da semana) na criminalidade e na taxa de prisão? | H3 |
| BQ4  | Como a criminalidade **evoluiu ao longo dos anos (2012–2017)** e há **sazonalidade mensal**? | H4 |
| BQ5  | Quais **community areas** (bairros) concentram mais crimes? | Novo (espacial) |
| BQ6  | A taxa de crime/prisão está associada a **indicadores socioeconômicos** (renda per capita, % pobreza, hardship index) da community area? | Novo (join socioeconômico) |
| BQ7  | Crimes **index** (graves/violentos, classificação FBI/IUCR) vs **non-index**: como se distribuem e diferem na taxa de prisão? | Novo (join IUCR) |

---

## 3. Fontes de dados escolhidas

| Fonte | Descrição | Papel | Licença |
|-------|-----------|-------|---------|
| **Chicago Crimes 2012–2017** | Ocorrências criminais (Kaggle, `currie32/crimes-in-chicago`). Mesma base dos MVPs 1 e 2. | Fato (principal) | Uso público / open data |
| **Selected Socioeconomic Indicators in Chicago 2008–2012** | 77 community areas: renda per capita, % pobreza, % desemprego, % sem ensino médio, hardship index. City of Chicago Data Portal. | Enriquece `dim_community_area` | Open Data (City of Chicago) |
| **Chicago Police IUCR Codes** | Tabela de referência: código IUCR → descrição, primary type, **index/non-index**. City of Chicago Data Portal. | Enriquece `dim_crime_type` | Open Data (City of Chicago) |

Chave de junção crimes ↔ socioeconômico: **Community Area** (1–77).
Chave de junção crimes ↔ IUCR: **código IUCR**.

---

## 4. Critérios de sucesso

- Pipeline **Bronze → Silver → Gold** (medallion) reprodutível no Databricks Free Edition.
- **Esquema estrela** na camada Gold, com fato e dimensões consolidadas.
- **Catálogo de dados** completo (domínios, categorias, min/max) + **linhagem** documentada.
- **Análise de qualidade** por atributo, com problemas identificados e tratados.
- **BQ1–BQ7** respondidas por SQL, com discussão que conecta os números ao problema.
- Evidências (screenshots do Volume, do Catalog e do Dashboard) no repositório público.

---

## 5. Limitações conhecidas (declaradas desde o início)

- **Descasamento temporal:** os indicadores socioeconômicos referem-se a **2008–2012**,
  enquanto os crimes cobrem **2012–2017**. Qualquer associação em BQ6 é **transversal**
  contra um retrato que antecede a maior parte da janela criminal — **não é causal nem
  contemporânea**. Isso é reforçado na análise e na Autoavaliação.
- **Amostragem:** para respeitar limites de armazenamento/upload da versão gratuita e
  manter **continuidade de linhagem** com os MVPs 1 e 2, pode-se usar a amostra
  estratificada de 20% (`random_state=42`). A escolha final é registrada em `linhagem.md`.
