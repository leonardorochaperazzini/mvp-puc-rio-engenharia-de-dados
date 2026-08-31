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
6. Para o dashboard há duas opções: montar na mão no SQL Editor a partir das consultas do
   `05`, ou rodar `python3 scripts/criar_dashboard.py` (com o Databricks CLI autenticado),
   que cria e publica um dashboard Lakeview com os gráficos das BQ automaticamente.

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

## Resultados (amostra de 20%, 291.342 ocorrências)

- **BQ1** — Os tipos mais comuns são THEFT (65,8 mil), BATTERY (52,8 mil) e CRIMINAL DAMAGE
  (31,2 mil). A taxa de prisão varia de 99,6% (PROSTITUTION) e 99,3% (NARCOTICS) até 5,3%
  (BURGLARY). Confirma H1: a prisão depende da natureza do crime, não do volume.
- **BQ2** — Crimes domésticos prendem **menos** (19,7%) que os não domésticos (27,0%),
  contrariando a hipótese H2.
- **BQ3** — A noite concentra mais crimes (92,7 mil) e também a maior taxa de prisão (30,9%);
  a madrugada tem a menor (20,6%). O padrão temporal existe, mas ao contrário do esperado.
- **BQ4** — Queda de 67,3 mil (2012) para ~53 mil (2016); a taxa de prisão cai de ~28% para
  18,8% em 2016. (2017 aparece truncado na amostra.)
- **BQ5** — Austin lidera com folga (≈19 mil), seguido de Near North Side e South Shore.
- **BQ6** — Gradiente claro: o quartil mais vulnerável tem mais crimes (86,1 mil), menor
  renda (US$ 12,7 mil) e maior taxa de prisão (32,3%). Correlação crimes × pobreza = 0,31.
- **BQ7** — Crimes graves (index) são 41,5% do total mas só 11% terminam em prisão; os
  non-index são 58,5% e prendem 36,5%.

Os dois resultados que contrariam hipóteses anteriores (BQ2 e BQ3) foram mantidos e
discutidos — os dados corrigindo a intuição é parte do valor do trabalho.

---

## Autoavaliação

**O que consegui.** O pipeline roda de ponta a ponta no Databricks serverless e cobre todas
as etapas pedidas: coleta (upload do CSV no volume + API Socrata), modelagem em estrela
sobre medallion, carga com ETL documentado, catálogo de dados (no markdown e na própria
plataforma via `COMMENT ON`) e análise dividida em qualidade e resposta às perguntas. As
sete perguntas de negócio foram respondidas por SQL sobre o Data Warehouse, com os números
na seção de Resultados. As quatro primeiras dão continuidade às hipóteses dos MVPs
anteriores, o que amarra as três etapas do meu trabalho — e, curiosamente, duas delas (H2 e
H3) não se confirmaram, o que rendeu boa discussão.

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
