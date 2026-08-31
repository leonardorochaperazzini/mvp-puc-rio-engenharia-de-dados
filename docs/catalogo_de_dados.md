# Catálogo de Dados

Descrição das tabelas da camada Gold (o esquema estrela consultado na análise), com os
domínios de cada atributo. Os mesmos comentários estão aplicados no Unity Catalog via
`COMMENT ON` (ver `pipeline/03_gold_modelagem`), então o catálogo existe tanto aqui quanto
dentro da plataforma.

Faixas numéricas (mín/máx) saem do notebook `04_qualidade_dados` — se você rodar com uma
amostra diferente, confira os valores lá.

---

## fact_crime

Fato central. Grão: uma linha por ocorrência criminal (`id`).

| Coluna | Tipo | Descrição | Domínio |
|--------|------|-----------|---------|
| id | long | Identificador único da ocorrência | chave de negócio |
| date_key | int | FK para `dim_date` (yyyyMMdd) | 20120101–20170118 |
| time_key | int | FK para `dim_time` (hora do dia) | 0–23 |
| crime_type_key | int | FK para `dim_crime_type` | ≥ 1; -1 = desconhecido |
| community_area_key | int | FK para `dim_community_area` | 1–77; -1 = desconhecido |
| location_key | int | FK para `dim_location` | ≥ 1; -1 = desconhecido |
| district | int | Distrito policial | 1–31 |
| beat | int | Beat policial | 111–2535 |
| ward | int | Distrito eleitoral | 1–50 |
| is_arrest | boolean | Houve prisão | true / false |
| is_domestic | boolean | Crime doméstico | true / false |
| latitude | double | Latitude (nula se inválida) | 41.64 a 42.02 |
| longitude | double | Longitude (nula se inválida) | -87.93 a -87.52 |

## dim_date

| Coluna | Tipo | Descrição | Domínio |
|--------|------|-----------|---------|
| date_key | int | Chave (yyyyMMdd) | 20120101–20170118 |
| date | date | Data | 2012-01-01 a 2017-01-18 |
| year | int | Ano | 2012–2017 |
| month | int | Mês | 1–12 |
| month_name | string | Nome do mês | January … December |
| quarter | int | Trimestre | 1–4 |
| day | int | Dia do mês | 1–31 |
| day_of_week | string | Dia da semana | Monday … Sunday |
| is_weekend | boolean | Fim de semana | true / false |

## dim_time

| Coluna | Tipo | Descrição | Domínio |
|--------|------|-----------|---------|
| time_key | int | Chave (= hora) | 0–23 |
| hour | int | Hora do dia | 0–23 |
| shift | string | Turno | Madrugada, Manhã, Tarde, Noite |

## dim_crime_type

Tipo de crime, enriquecido com a tabela de referência IUCR.

| Coluna | Tipo | Descrição | Domínio |
|--------|------|-----------|---------|
| crime_type_key | int | Chave substituta | ≥ 1; -1 = desconhecido |
| iucr | string | Código IUCR (4 dígitos) | ex.: 0110, 0460 |
| primary_type | string | Categoria principal | ex.: THEFT, BATTERY, NARCOTICS |
| description | string | Descrição detalhada | texto |
| fbi_code | string | Código FBI | ex.: 06, 08B |
| iucr_primary_description | string | Descrição oficial IUCR | texto |
| iucr_secondary_description | string | Descrição secundária IUCR | texto |
| is_index | boolean | Crime index (grave/violento) | true / false |

## dim_community_area

Bairro (community area) com os indicadores socioeconômicos. Inclui o membro -1
("Desconhecido") para os crimes sem bairro informado.

| Coluna | Tipo | Descrição | Domínio |
|--------|------|-----------|---------|
| community_area_key | int | Chave (= número da área) | 1–77; -1 = desconhecido |
| community_area | int | Número da community area | 1–77 |
| community_area_name | string | Nome do bairro | ex.: Rogers Park, Loop |
| pct_housing_crowded | double | % domicílios superlotados | ~1 a 16 |
| pct_below_poverty | double | % domicílios abaixo da pobreza | 3.3 a 56.5 |
| pct_unemployed | double | % da população 16+ desempregada | 4.7 a 35.9 |
| pct_no_highschool | double | % 25+ sem ensino médio | ~3 a 55 |
| pct_dependent_age | double | % com menos de 18 ou mais de 64 anos | ~13 a 51 |
| per_capita_income | int | Renda per capita anual (USD) | 8.201 a 88.669 |
| hardship_index | int | Índice de privação (maior = pior) | 1–98 |
| income_quartile | int | Quartil de renda (1 = menor) | 1–4 |
| hardship_quartile | int | Quartil de hardship (4 = maior privação) | 1–4 |

## dim_location

| Coluna | Tipo | Descrição | Domínio |
|--------|------|-----------|---------|
| location_key | int | Chave substituta | ≥ 1; -1 = desconhecido |
| location_description | string | Tipo de local | ex.: STREET, RESIDENCE, APARTMENT |

---

## Observações de domínio

- **Coordenadas** fora do bounding box de Chicago ou iguais a (0,0) foram anuladas no
  Silver. A linha do crime continua na base; só o par lat/long fica nulo.
- **community_area = 0 ou nula** no dado bruto vira a chave -1 no fato.
- **is_index = false** também cobre códigos IUCR que não existem na tabela de referência.
- Os valores de mín/máx dos indicadores socioeconômicos refletem o dataset de 2008–2012.
- **`dim_date` cobre 1.845 dias** (2012-01-01 a 2017-01-18). O corte em janeiro/2017 vem da
  própria amostra de origem, não do pipeline — por isso 2017 aparece truncado nas análises.
