# MVP — Engenharia de Dados

**PUC-Rio · Pós-graduação em Ciência de Dados e Analytics**
Sprint: Engenharia de Dados

Pipeline de dados na nuvem (Databricks) sobre criminalidade em Chicago. É o terceiro MVP
de uma sequência sobre a mesma base: os dois primeiros trataram de análise exploratória e
de machine learning; este muda o foco para **engenharia de dados** — montar um Data
Warehouse confiável, catalogado e consultável.

- **Problema e perguntas de negócio:** [`docs/objetivo.md`](docs/objetivo.md)
- **Catálogo de dados:** [`docs/catalogo_de_dados.md`](docs/catalogo_de_dados.md)
- **Linhagem e coleta:** [`docs/linhagem.md`](docs/linhagem.md)

---

## Arquitetura

Arquitetura medallion (Bronze → Silver → Gold) no Databricks Free Edition, com Unity
Catalog e tabelas Delta. A camada Gold é um **esquema estrela**.

```
Kaggle (crimes)  ─┐
Socrata API       ├─►  bronze  ─►  silver  ─►  gold (star schema)  ─►  SQL + Dashboard
(socioeconômico,  ─┘   (bruto)   (limpo/      (fato + dimensões)
 IUCR)                            conciliado)
```

O modelo dimensional:

```
              dim_date     dim_time
                   \         /
dim_crime_type ──  FACT_CRIME  ── dim_community_area  (+ socioeconômico)
                   /         \
            dim_location    (district/beat/ward)
```

Três fontes são combinadas: o registro de crimes (fato), os indicadores socioeconômicos por
bairro (enriquecem `dim_community_area`) e a tabela de referência IUCR (traz `is_index` para
`dim_crime_type`).

---

## Estrutura do repositório

```
mvp-puc-rio-engenharia-de-dados/
├── pipeline/                     # notebooks Databricks, na ordem de execução
│   ├── 00_setup.py               # catálogo, schemas e volume
│   ├── 01_bronze_ingestao.py     # ingestão das 3 fontes
│   ├── 02_silver_limpeza.py      # limpeza, tipagem, dedupe, conciliação
│   ├── 03_gold_modelagem.py      # esquema estrela + COMMENT ON
│   ├── 04_qualidade_dados.py     # análise de qualidade por atributo
│   └── 05_analise_negocio.py     # SQL das perguntas BQ1–BQ7
├── docs/                         # objetivo, catálogo, linhagem
├── evidencias/                   # screenshots (volume, catalog, dashboard, resultados)
└── README.md
```

---

## Como reproduzir

1. Crie uma conta no [Databricks Free Edition](https://www.databricks.com/learn/free-edition).
2. Importe a pasta `pipeline/` no workspace (os arquivos `.py` importam como notebooks).
3. Rode `00_setup` para criar catálogo, schemas e o volume.
4. Baixe o CSV do Chicago Crimes ([Kaggle](https://www.kaggle.com/datasets/currie32/crimes-in-chicago))
   e faça upload de `Chicago_Crimes_2012_to_2017_sample.csv` para o volume
   `mvp_chicago.bronze.raw`.
5. Execute na ordem: `01` → `02` → `03` → `04` → `05`. As duas fontes de enriquecimento são
   baixadas automaticamente pela API Socrata dentro do `01`.
6. Para o dashboard, abra o SQL Editor, cole as consultas do `05` e monte os gráficos
   (barras para BQ1/BQ5, linha para BQ4, tabela para BQ6). Salve como Dashboard.

> **Sobre a amostra:** uso a amostra de 20% (mesma dos MVPs anteriores) para caber nos
> limites da versão gratuita. Para rodar com a base completa (~1,45M linhas), basta subir o
> CSV inteiro no mesmo volume — nada mais muda.

---

## Perguntas de negócio

Detalhadas em [`docs/objetivo.md`](docs/objetivo.md). Em resumo:

- **BQ1** tipos de crime mais frequentes e taxa de prisão por tipo
- **BQ2** crimes domésticos têm taxa de prisão diferente?
- **BQ3** padrão temporal (hora, turno, dia da semana)
- **BQ4** evolução anual e sazonalidade mensal
- **BQ5** bairros com mais crimes
- **BQ6** relação entre crime/prisão e indicadores socioeconômicos (join)
- **BQ7** crimes graves (index) × non-index (join IUCR)

As respostas, com discussão, estão no notebook `05_analise_negocio` e no dashboard.

---

## Autoavaliação

**O que consegui.** O pipeline cobre todas as etapas pedidas: coleta (upload + API),
modelagem em estrela sobre medallion, carga com ETL documentado, catálogo de dados (no
markdown e na própria plataforma) e análise dividida em qualidade e resposta às perguntas.
As sete perguntas de negócio são respondidas por SQL sobre o Data Warehouse, e as quatro
primeiras dão continuidade às hipóteses dos MVPs anteriores, o que amarra as três etapas do
meu trabalho.

**O que ficou parcial.** A BQ6, que cruza criminalidade com contexto socioeconômico, é a
mais frágil por um motivo que já estava previsto no objetivo: os indicadores são de
2008–2012 e os crimes de 2012–2017. Consigo descrever a associação, mas não afirmar causa
nem tratá-la como contemporânea. Preferi manter a pergunta e ser honesto sobre o limite a
removê-la — o enunciado inclusive pede para não apagar perguntas não resolvidas.

**Dificuldades.** A maior parte foi entender o Free Edition, que é diferente dos tutoriais
antigos: não existe DBFS/`FileStore` como antes, tudo passa por Unity Catalog e Volumes.
Isso mudou a forma de subir e ler os arquivos. A conciliação das fontes também deu trabalho:
descobrir que a tabela socioeconômica tinha uma linha agregada "CHICAGO" que inflava o join,
e tratar os crimes sem community area sem simplesmente descartá-los.

**Trabalhos futuros.** Buscar uma versão mais recente dos indicadores socioeconômicos para
alinhar o período e fortalecer a BQ6; rodar o pipeline com a base completa; adicionar uma
dimensão geográfica mais rica (distrito/ward com fronteiras) para mapas; e transformar o
notebook de qualidade em testes automatizados que rodam a cada carga.

---

## Licença dos dados

- Chicago Crimes: dataset público no Kaggle (`currie32/crimes-in-chicago`).
- Indicadores socioeconômicos e IUCR: dados abertos da City of Chicago Data Portal.

## MVPs anteriores (mesma base)

- [Análise de Dados e Boas Práticas](https://github.com/leonardorochaperazzini/mvp-puc-rio-analise-de-dados)
- [Machine Learning & Analytics](https://github.com/leonardorochaperazzini/mvp-puc-rio-ml-analytics)
