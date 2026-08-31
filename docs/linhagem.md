# Linhagem dos dados

Registro de onde cada conjunto veio, como foi coletado e o que aconteceu com ele até
chegar na camada Gold.

## Fontes

### 1. Chicago Crimes 2012–2017 (fato principal)

- **Origem:** Kaggle, dataset `currie32/crimes-in-chicago`, que por sua vez reempacota o
  portal de dados abertos da cidade de Chicago.
- **Por que essa base:** é a mesma dos meus dois MVPs anteriores (Análise de Dados e
  Machine Learning). Manter a fonte garante continuidade — dá para comparar as três etapas
  do meu trabalho sobre o mesmo problema.
- **Coleta:** download manual do CSV e upload para um Volume do Unity Catalog
  (`/Volumes/mvp_chicago/bronze/raw`). Optei pela amostra estratificada de 20%
  (`random_state=42`, ~291 mil registros), a mesma dos MVPs anteriores, por dois motivos:
  respeita os limites de upload da versão gratuita do Databricks e mantém a linhagem
  idêntica às etapas passadas.
- **Volume completo:** o arquivo original tem ~1,45 milhão de linhas e ~300 MB. Se quiser
  reproduzir com a base inteira, basta subir o CSV completo no mesmo Volume — o pipeline
  não muda.

### 2. Selected Socioeconomic Indicators in Chicago, 2008–2012 (enriquecimento)

- **Origem:** City of Chicago Data Portal, recurso Socrata `kn9c-c2s2`.
- **Coleta:** direto da API Socrata em tempo de execução
  (`https://data.cityofchicago.org/resource/kn9c-c2s2.csv`). Não precisa de download manual;
  o notebook `01_bronze_ingestao` baixa na hora — funciona como um pequeno robô de coleta.
- **Conteúdo:** um registro por community area (bairro) com renda per capita, percentual de
  domicílios abaixo da linha da pobreza, desemprego, escolaridade e o hardship index.
- **Ressalva:** os indicadores se referem a 2008–2012, período anterior à maior parte dos
  crimes analisados. Isso está documentado como limitação no `objetivo.md` e na análise.

### 3. Chicago Police IUCR Codes (enriquecimento)

- **Origem:** City of Chicago Data Portal, recurso Socrata `c7ck-438e`.
- **Coleta:** também pela API Socrata, dentro do `01_bronze_ingestao`.
- **Conteúdo:** tabela de referência que traduz cada código IUCR em descrição e informa se
  o crime é *index* (grave/violento, na classificação do FBI) ou *non-index*.

## Caminho dos dados (medallion)

```
Kaggle CSV ─┐
Socrata API ─┼─► bronze (bruto + metadados)
Socrata API ─┘        │
                      ▼
                   silver (tipado, limpo, deduplicado, conciliado)
                      │
                      ▼
                    gold (esquema estrela: fato + dimensões)
```

## Principais transformações

| Etapa | O que acontece |
|-------|----------------|
| Bronze | Cópia fiel das três fontes como tabelas Delta, com `_ingested_at` e `_source`. |
| Silver — crimes | Descarte da coluna de índice do CSV; tipagem; `Arrest`/`Domestic` viram boolean; parsing da data; dedupe por `id` (guarda defensiva, 0 nesta amostra); filtro de ano (guarda defensiva, 0 nesta amostra); coordenadas inválidas anuladas (7.441 linhas). |
| Silver — socioeconômico | Tipagem dos indicadores e **remoção da linha agregada "CHICAGO"**, que somava a cidade toda e inflaria o join. |
| Silver — IUCR | Código padronizado para 4 dígitos (chave do join) e derivação de `is_index`. |
| Gold | Montagem do fato e das dimensões; indicadores socioeconômicos e `is_index` incorporados às dimensões; membros "desconhecido" (chave -1) em `dim_community_area`, `dim_location` e `dim_crime_type` para não perder fatos sem bairro, local ou tipo. |

## Conciliação dos joins

- **Crimes × socioeconômico** pela community area (1–77). No lado dos crimes há registros com
  community area 0 ou nula — direcionados ao membro -1 em vez de descartados. No lado
  socioeconômico, a linha "CHICAGO" (sem número de área) foi excluída para não duplicar
  contagem.
- **Crimes × IUCR** pelo código IUCR de 4 dígitos. Códigos sem correspondência na tabela de
  referência ficam com `is_index = false`.
