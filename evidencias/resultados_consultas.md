# Resultados das consultas (execução real)

Saída das consultas BQ1–BQ7 rodadas sobre `mvp_chicago.gold` no Databricks (amostra de 20%,
291.342 ocorrências). Complementa os screenshots do dashboard.

## Integridade do star schema

| Verificação | Resultado |
|---|---|
| fact_crime (linhas / ids distintos) | 291.342 / 291.342 (grão 1 por ID) |
| Órfãos de FK | 0 |
| Fatos com community area desconhecida (-1) | 14 |
| dim_date / dim_time / dim_crime_type | 1.845 / 24 / 339 |
| dim_community_area / dim_location | 78 (77 + desconhecido) / 122 |
| silver.socioeconomic | 77 (linha "CHICAGO" removida) |

## BQ1 — Tipos mais frequentes e taxa de prisão

| primary_type | total | taxa_prisão % |
|---|---|---|
| THEFT | 65.827 | 11,0 |
| BATTERY | 52.759 | 23,1 |
| CRIMINAL DAMAGE | 31.177 | 6,4 |
| NARCOTICS | 27.261 | 99,3 |
| ASSAULT | 18.207 | 23,7 |

Maiores taxas (≥500 casos): PROSTITUTION 99,6% · NARCOTICS 99,3% · INTERFERENCE W/ PUBLIC
OFFICER 94,1%. Menores: BURGLARY 5,3% · CRIMINAL DAMAGE 6,4% · MOTOR VEHICLE THEFT 7,1%.

## BQ2 — Doméstico vs não doméstico

| doméstico | total | taxa_prisão % |
|---|---|---|
| não | 247.152 | 27,0 |
| sim | 44.190 | 19,7 |

## BQ3 — Por turno

| turno | total | taxa_prisão % |
|---|---|---|
| Noite | 92.679 | 30,9 |
| Tarde | 91.505 | 26,1 |
| Manhã | 61.823 | 22,1 |
| Madrugada | 45.335 | 20,6 |

## BQ4 — Por ano

| ano | total | taxa_prisão % |
|---|---|---|
| 2012 | 67.342 | 27,0 |
| 2013 | 61.620 | 28,4 |
| 2014 | 54.799 | 28,7 |
| 2015 | 52.454 | 26,2 |
| 2016 | 52.900 | 18,8 |
| 2017 | 2.227 | 16,9 (parcial) |

## BQ5 — Top bairros

Austin 18.955 · Near North Side 10.070 · South Shore 9.740 · Humboldt Park 9.438 · North
Lawndale 9.380 · Near West Side 8.540 · Auburn Gresham 8.249 · West Town 8.199.

## BQ6 — Crime/prisão × privação socioeconômica

| quartil hardship | crimes | renda média (US$) | taxa_prisão % |
|---|---|---|---|
| 1 (menor privação) | 71.887 | 53.182 | 19,4 |
| 2 | 41.890 | 24.558 | 19,7 |
| 3 | 91.431 | 17.424 | 27,9 |
| 4 (maior privação) | 86.120 | 12.761 | 32,3 |

Correlação bairro a bairro: crimes × pobreza = 0,307 · crimes × hardship = 0,183 ·
crimes × renda per capita = 0,026.

> Limitação: indicadores socioeconômicos são de 2008–2012; crimes de 2012–2017. Associação
> transversal, não causal nem contemporânea.

## BQ7 — Crimes index vs non-index

| index | total | % do total | taxa_prisão % |
|---|---|---|---|
| sim (graves) | 120.844 | 41,5 | 11,0 |
| não | 170.498 | 58,5 | 36,5 |
