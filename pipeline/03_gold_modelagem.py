# Databricks notebook source
# MAGIC %md
# MAGIC # 03 · Gold — Esquema Estrela (star schema)
# MAGIC
# MAGIC Constrói o Data Warehouse dimensional a partir do Silver:
# MAGIC
# MAGIC ```
# MAGIC                 dim_date ── dim_time
# MAGIC                     \        /
# MAGIC dim_crime_type ── FACT_CRIME ── dim_community_area  (+ socioeconômico)
# MAGIC                     /        \
# MAGIC          dim_location      (district/beat/ward degenerate)
# MAGIC ```
# MAGIC
# MAGIC - **Grão do fato:** 1 linha por ocorrência (`id`).
# MAGIC - `dim_community_area` recebe os **indicadores socioeconômicos** (fonte 2) + faixas/quartis.
# MAGIC - `dim_crime_type` recebe **is_index** e descrições IUCR (fonte 3).
# MAGIC - Membros **"desconhecido" (chave -1)** garantem integridade referencial p/ community area
# MAGIC   e location ausentes (não perdemos fatos).

# COMMAND ----------

from pyspark.sql import functions as F, Window as W

CATALOG = "mvp_chicago"
spark.sql(f"USE CATALOG {CATALOG}")
crimes = spark.table(f"{CATALOG}.silver.crimes")

# COMMAND ----------

# MAGIC %md
# MAGIC ## dim_date

# COMMAND ----------

dim_date = (
    crimes.select(F.to_date("occurred_at").alias("date"))
    .where(F.col("date").isNotNull()).distinct()
    .withColumn("date_key", F.date_format("date", "yyyyMMdd").cast("int"))
    .withColumn("year", F.year("date"))
    .withColumn("month", F.month("date"))
    .withColumn("month_name", F.date_format("date", "MMMM"))
    .withColumn("quarter", F.quarter("date"))
    .withColumn("day", F.dayofmonth("date"))
    .withColumn("day_of_week", F.date_format("date", "EEEE"))
    .withColumn("is_weekend", F.dayofweek("date").isin(1, 7))
)
dim_date.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"{CATALOG}.gold.dim_date")
print(f"dim_date: {dim_date.count():,} dias")

# COMMAND ----------

# MAGIC %md
# MAGIC ## dim_time (hora do dia + turno)

# COMMAND ----------

dim_time = spark.range(0, 24).withColumnRenamed("id", "time_key")
dim_time = (
    dim_time
    .withColumn("hour", F.col("time_key"))
    .withColumn("shift", F.when(F.col("hour").between(0, 5), "Madrugada")
                          .when(F.col("hour").between(6, 11), "Manhã")
                          .when(F.col("hour").between(12, 17), "Tarde")
                          .otherwise("Noite"))
)
dim_time.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"{CATALOG}.gold.dim_time")
display(dim_time)

# COMMAND ----------

# MAGIC %md
# MAGIC ## dim_crime_type (+ IUCR: is_index e descrições)
# MAGIC Grão: código IUCR. Atributos representativos de `primary_type`/`description` (o mais
# MAGIC frequente por IUCR) + enriquecimento da tabela de referência IUCR.

# COMMAND ----------

# primary_type/description representativos (mais frequentes) por iucr
w = W.partitionBy("iucr").orderBy(F.desc("cnt"))
rep = (
    crimes.groupBy("iucr", "primary_type", "description", "fbi_code").count()
    .withColumnRenamed("count", "cnt")
    .withColumn("rn", F.row_number().over(w))
    .where(F.col("rn") == 1)
    .select("iucr", "primary_type", "description", "fbi_code")
)

iucr_ref = spark.table(f"{CATALOG}.silver.iucr_codes")

dim_crime_type = (
    rep.join(iucr_ref, "iucr", "left")
    .withColumn("is_index", F.coalesce(F.col("is_index"), F.lit(False)))
    .withColumn("crime_type_key", F.row_number().over(W.orderBy("iucr")))
    .select("crime_type_key", "iucr", "primary_type", "description", "fbi_code",
            "iucr_primary_description", "iucr_secondary_description", "is_index")
)
# Membro -1 (desconhecido) para IUCR sem correspondência → mantém integridade referencial.
unknown_ct = spark.sql("""
    SELECT -1 AS crime_type_key, 'XXXX' AS iucr, 'DESCONHECIDO' AS primary_type,
           CAST(NULL AS STRING) AS description, CAST(NULL AS STRING) AS fbi_code,
           CAST(NULL AS STRING) AS iucr_primary_description,
           CAST(NULL AS STRING) AS iucr_secondary_description, FALSE AS is_index
""")
dim_crime_type = dim_crime_type.unionByName(unknown_ct)
dim_crime_type.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"{CATALOG}.gold.dim_crime_type")
print(f"dim_crime_type: {dim_crime_type.count()} tipos (inclui -1 desconhecido)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## dim_community_area (+ socioeconômico + quartis)
# MAGIC Chave natural = número da community area (1–77). Membro **-1 = desconhecido** para
# MAGIC crimes com community area 0/nula. Quartis de renda e hardship p/ agrupamento em BQ6.

# COMMAND ----------

socio = spark.table(f"{CATALOG}.silver.socioeconomic")

qwin = W.orderBy("per_capita_income")
hwin = W.orderBy("hardship_index")
dim_ca = (
    socio
    .withColumn("community_area_key", F.col("community_area"))
    .withColumn("income_quartile", F.ntile(4).over(qwin))     # 1 = menor renda
    .withColumn("hardship_quartile", F.ntile(4).over(hwin))   # 4 = maior privação
    .select("community_area_key", "community_area", "community_area_name",
            "pct_housing_crowded", "pct_below_poverty", "pct_unemployed",
            "pct_no_highschool", "pct_dependent_age", "per_capita_income",
            "hardship_index", "income_quartile", "hardship_quartile")
)

unknown_ca = spark.sql("""
    SELECT -1 AS community_area_key,
           CAST(NULL AS INT)    AS community_area,
           'Desconhecido'       AS community_area_name,
           CAST(NULL AS DOUBLE) AS pct_housing_crowded,
           CAST(NULL AS DOUBLE) AS pct_below_poverty,
           CAST(NULL AS DOUBLE) AS pct_unemployed,
           CAST(NULL AS DOUBLE) AS pct_no_highschool,
           CAST(NULL AS DOUBLE) AS pct_dependent_age,
           CAST(NULL AS INT)    AS per_capita_income,
           CAST(NULL AS INT)    AS hardship_index,
           CAST(NULL AS INT)    AS income_quartile,
           CAST(NULL AS INT)    AS hardship_quartile
""")
dim_ca = dim_ca.unionByName(unknown_ca)
dim_ca.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"{CATALOG}.gold.dim_community_area")
print(f"dim_community_area: {dim_ca.count()} (77 + 1 desconhecido)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## dim_location (location description)

# COMMAND ----------

dim_location = (
    crimes.select("location_description").distinct()
    .where(F.col("location_description").isNotNull() & (F.col("location_description") != ""))
    .withColumn("location_key", F.row_number().over(W.orderBy("location_description")))
    .select("location_key", "location_description")
)
unknown_loc = spark.createDataFrame([(-1, "DESCONHECIDO")], dim_location.schema)
dim_location = dim_location.unionByName(unknown_loc)
dim_location.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"{CATALOG}.gold.dim_location")
print(f"dim_location: {dim_location.count()} locais")

# COMMAND ----------

# MAGIC %md
# MAGIC ## fact_crime
# MAGIC Junta as chaves substitutas. Community area 0/nula → -1; location ausente → -1.

# COMMAND ----------

ct = spark.table(f"{CATALOG}.gold.dim_crime_type").select("crime_type_key", "iucr")
loc = spark.table(f"{CATALOG}.gold.dim_location")

fact = (
    crimes
    .withColumn("date_key", F.date_format("occurred_at", "yyyyMMdd").cast("int"))
    .withColumn("time_key", F.hour("occurred_at"))
    .join(ct, "iucr", "left")
    .join(loc, "location_description", "left")
    # community area válida (1–77)? senão -1 (desconhecido)
    .withColumn("community_area_key",
                F.when(F.col("community_area").between(1, 77), F.col("community_area"))
                 .otherwise(F.lit(-1)))
    .withColumn("location_key", F.coalesce(F.col("location_key"), F.lit(-1)))
    .withColumn("crime_type_key", F.coalesce(F.col("crime_type_key"), F.lit(-1)))
    .select(
        "id", "date_key", "time_key", "crime_type_key", "community_area_key", "location_key",
        "district", "beat", "ward",
        F.col("arrest").alias("is_arrest"), F.col("domestic").alias("is_domestic"),
        "latitude", "longitude",
    )
)
fact.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"{CATALOG}.gold.fact_crime")
print(f"fact_crime: {fact.count():,} linhas (deve = silver.crimes)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verificação de integridade do star schema

# COMMAND ----------

f = spark.table(f"{CATALOG}.gold.fact_crime")
print("Grão (id único)?", f.count() == f.select("id").distinct().count())
print("Órfãos de community area:", f.join(spark.table(f"{CATALOG}.gold.dim_community_area"),
      "community_area_key", "left_anti").count())
print("Órfãos de crime_type:", f.join(spark.table(f"{CATALOG}.gold.dim_crime_type"),
      "crime_type_key", "left_anti").count())
print("% arrest:", round(f.filter("is_arrest").count() / f.count() * 100, 2))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Catálogo de Dados na plataforma (COMMENT ON)
# MAGIC Documenta tabelas e colunas-chave no Unity Catalog — o Catálogo de Dados vive na
# MAGIC plataforma **e** em `docs/catalogo_de_dados.md`. (Tirar screenshot da aba Catalog.)

# COMMAND ----------

table_comments = {
    "bronze.crimes": "Bronze: ocorrencias criminais brutas (CSV Kaggle) + metadados de ingestao.",
    "bronze.socioeconomic": "Bronze: indicadores socioeconomicos brutos por community area (API Socrata).",
    "bronze.iucr_codes": "Bronze: tabela de referencia IUCR bruta (API Socrata).",
    "silver.crimes": "Silver: crimes limpos, tipados e deduplicados.",
    "silver.socioeconomic": "Silver: socioeconomico tipado, sem a linha agregada CHICAGO (77 areas).",
    "silver.iucr_codes": "Silver: IUCR com codigo de 4 digitos e flag is_index.",
    "gold.fact_crime": "Fato: 1 linha por ocorrencia criminal (grao = id).",
    "gold.dim_date": "Dimensao de data (2012-01-01 a 2017-01-18; ano, mes, trimestre, dia da semana).",
    "gold.dim_time": "Dimensao de hora do dia (0-23) e turno.",
    "gold.dim_crime_type": "Dimensao de tipo de crime (IUCR, primary type, FBI code, is_index).",
    "gold.dim_community_area": "Dimensao de bairro (community area) + indicadores socioeconomicos e quartis.",
    "gold.dim_location": "Dimensao de tipo de local da ocorrencia.",
}
for tbl, cmt in table_comments.items():
    spark.sql(f"COMMENT ON TABLE {CATALOG}.{tbl} IS '{cmt}'")

# Comentarios de coluna em TODAS as colunas gold (catalogo completo na plataforma).
col_comments = {
    "gold.fact_crime": {
        "id": "Identificador unico da ocorrencia (chave de negocio).",
        "date_key": "FK para dim_date no formato yyyyMMdd (20120101-20170118).",
        "time_key": "FK para dim_time = hora do dia (0-23).",
        "crime_type_key": "FK para dim_crime_type (-1 = desconhecido).",
        "community_area_key": "FK para dim_community_area (-1 = desconhecido).",
        "location_key": "FK para dim_location (-1 = desconhecido).",
        "district": "Distrito policial (1-31).",
        "beat": "Beat policial (111-2535).",
        "ward": "Distrito eleitoral (1-50).",
        "is_arrest": "Houve prisao (boolean).",
        "is_domestic": "Crime domestico (boolean).",
        "latitude": "Latitude (~41.64 a 42.02; nula se invalida).",
        "longitude": "Longitude (~-87.93 a -87.52; nula se invalida).",
    },
    "gold.dim_date": {
        "date_key": "Chave da data no formato yyyyMMdd.",
        "date": "Data da ocorrencia (2012-01-01 a 2017-01-18).",
        "year": "Ano (2012-2017).", "month": "Mes (1-12).",
        "month_name": "Nome do mes (January-December).", "quarter": "Trimestre (1-4).",
        "day": "Dia do mes (1-31).", "day_of_week": "Dia da semana (Monday-Sunday).",
        "is_weekend": "Fim de semana (boolean).",
    },
    "gold.dim_time": {
        "time_key": "Chave = hora do dia (0-23).", "hour": "Hora do dia (0-23).",
        "shift": "Turno (Madrugada, Manha, Tarde, Noite).",
    },
    "gold.dim_crime_type": {
        "crime_type_key": "Chave substituta (-1 = desconhecido).",
        "iucr": "Codigo IUCR de 4 digitos (ex.: 0110, 0460).",
        "primary_type": "Categoria principal (ex.: THEFT, BATTERY, NARCOTICS).",
        "description": "Descricao detalhada do crime.", "fbi_code": "Codigo FBI (ex.: 06, 08B).",
        "iucr_primary_description": "Descricao oficial IUCR (primaria).",
        "iucr_secondary_description": "Descricao oficial IUCR (secundaria).",
        "is_index": "Crime index (grave/violento) conforme classificacao FBI/IUCR.",
    },
    "gold.dim_community_area": {
        "community_area_key": "Chave = numero da community area (1-77; -1 = desconhecido).",
        "community_area": "Numero da community area (1-77).",
        "community_area_name": "Nome do bairro (ex.: Rogers Park, Loop).",
        "pct_housing_crowded": "% de domicilios superlotados (~1 a 16).",
        "pct_below_poverty": "% de domicilios abaixo da pobreza (3.3 a 56.5).",
        "pct_unemployed": "% da populacao 16+ desempregada (4.7 a 35.9).",
        "pct_no_highschool": "% da populacao 25+ sem ensino medio.",
        "pct_dependent_age": "% com menos de 18 ou mais de 64 anos.",
        "per_capita_income": "Renda per capita anual em USD (8201 a 88669; base 2008-2012).",
        "hardship_index": "Indice de privacao 1-98 (maior = mais vulneravel).",
        "income_quartile": "Quartil de renda (1 = menor, 4 = maior).",
        "hardship_quartile": "Quartil de privacao (1 = menor, 4 = maior).",
    },
    "gold.dim_location": {
        "location_key": "Chave substituta (-1 = desconhecido).",
        "location_description": "Tipo de local (ex.: STREET, RESIDENCE, APARTMENT).",
    },
}
for tbl, cols in col_comments.items():
    for col, cmt in cols.items():
        spark.sql(f"ALTER TABLE {CATALOG}.{tbl} ALTER COLUMN {col} COMMENT '{cmt}'")

print("Comentarios de catalogo aplicados no Unity Catalog (tabelas bronze/silver/gold + todas as colunas gold).")
