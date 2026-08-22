# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Silver — Limpeza, tipagem, dedupe e conciliação
# MAGIC
# MAGIC Transforma o Bronze em dados **confiáveis e tipados**. Principais operações:
# MAGIC
# MAGIC - **Crimes:** remove coluna de índice do CSV, tipa colunas, converte `Arrest`/`Domestic`
# MAGIC   para boolean, faz parsing da data, **deduplica por `ID`**, filtra coordenadas inválidas
# MAGIC   e registros fora de 2012–2017.
# MAGIC - **Socioeconômico:** tipa numéricos e **exclui a linha agregada "CHICAGO"** (senão o join
# MAGIC   por community area infla os agregados).
# MAGIC - **IUCR:** normaliza o código para 4 dígitos (chave de join) e deriva `is_index`.
# MAGIC
# MAGIC Todas as contagens de descarte são impressas (auditoria da conciliação → nota de Carga).

# COMMAND ----------

from pyspark.sql import functions as F

CATALOG = "mvp_chicago"
spark.sql(f"USE CATALOG {CATALOG}")

def log_drop(df_before, df_after, motivo):
    b, a = df_before, df_after
    print(f"  - {motivo}: removidas {b - a:,} linhas ({a:,} restantes)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1) Silver — Crimes

# COMMAND ----------

b = spark.table(f"{CATALOG}.bronze.crimes")
n0 = b.count()
print(f"Bronze crimes: {n0:,}")

# A 1a coluna do CSV Kaggle é um índice sem nome — descartar se existir.
cols = b.columns
first = cols[0]
if first.lower().startswith("_c0") or first.strip() == "" or first.lower() == "unnamed: 0":
    b = b.drop(first)
    print(f"Coluna de índice descartada: '{first}'")

# COMMAND ----------

crimes = (
    b
    .withColumn("id", F.col("ID").cast("long"))
    .withColumn("case_number", F.col("`Case Number`"))
    .withColumn("occurred_at", F.to_timestamp("Date", "MM/dd/yyyy hh:mm:ss a"))
    .withColumn("block", F.col("Block"))
    .withColumn("iucr", F.lpad(F.trim(F.col("IUCR")), 4, "0"))
    .withColumn("primary_type", F.trim(F.col("`Primary Type`")))
    .withColumn("description", F.trim(F.col("Description")))
    .withColumn("location_description", F.trim(F.col("`Location Description`")))
    .withColumn("arrest", F.col("Arrest") == "True")
    .withColumn("domestic", F.col("Domestic") == "True")
    .withColumn("beat", F.col("Beat").cast("int"))
    .withColumn("district", F.col("District").cast("int"))
    .withColumn("ward", F.col("Ward").cast("int"))
    .withColumn("community_area", F.col("`Community Area`").cast("int"))
    .withColumn("fbi_code", F.trim(F.col("`FBI Code`")))
    .withColumn("year", F.col("Year").cast("int"))
    .withColumn("latitude", F.col("Latitude").cast("double"))
    .withColumn("longitude", F.col("Longitude").cast("double"))
    .select(
        "id", "case_number", "occurred_at", "block", "iucr", "primary_type",
        "description", "location_description", "arrest", "domestic", "beat",
        "district", "ward", "community_area", "fbi_code", "year",
        "latitude", "longitude",
    )
)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Dedupe por `ID` e filtros de qualidade
# MAGIC O release multi-arquivo da Kaggle contém IDs duplicados — mantemos 1 por `id`.

# COMMAND ----------

n1 = crimes.count()
crimes = crimes.dropDuplicates(["id"])
log_drop(n1, crimes.count(), "duplicados por ID")

n2 = crimes.count()
crimes = crimes.filter(F.col("id").isNotNull() & F.col("occurred_at").isNotNull())
log_drop(n2, crimes.count(), "id ou data nulos")

# Fora da janela documentada 2012–2017
n3 = crimes.count()
crimes = crimes.filter(F.col("year").between(2012, 2017))
log_drop(n3, crimes.count(), "ano fora de 2012–2017")

# Coordenadas: (0,0) e fora do bounding box de Chicago viram NULL (não descartam a linha,
# pois o crime ainda é válido para análises não espaciais).
chi_lat = (41.60, 42.05)
chi_lon = (-87.95, -87.50)
valid_coord = (
    F.col("latitude").between(*chi_lat) & F.col("longitude").between(*chi_lon)
    & ~((F.col("latitude") == 0) & (F.col("longitude") == 0))
)
inval = crimes.filter(~valid_coord | F.col("latitude").isNull()).count()
crimes = (
    crimes
    .withColumn("latitude",  F.when(valid_coord, F.col("latitude")))
    .withColumn("longitude", F.when(valid_coord, F.col("longitude")))
)
print(f"  - coordenadas inválidas anuladas (mantidas as linhas): {inval:,}")

crimes.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"{CATALOG}.silver.crimes")
print(f"Silver crimes: {crimes.count():,} linhas")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2) Silver — Socioeconômico (exclui a linha "CHICAGO")

# COMMAND ----------

s = spark.table(f"{CATALOG}.bronze.socioeconomic")
print(f"Bronze socioeconômico: {s.count()} linhas (esperado 78)")

socio = (
    s
    .withColumn("community_area", F.col("ca").cast("int"))
    .withColumnRenamed("community_area_name", "community_area_name")
    .withColumn("pct_housing_crowded",   F.col("percent_of_housing_crowded").cast("double"))
    .withColumn("pct_below_poverty",     F.col("percent_households_below_poverty").cast("double"))
    .withColumn("pct_unemployed",        F.col("percent_aged_16_unemployed").cast("double"))
    .withColumn("pct_no_highschool",     F.col("percent_aged_25_without_high_school_diploma").cast("double"))
    .withColumn("pct_dependent_age",     F.col("percent_aged_under_18_or_over_64").cast("double"))
    .withColumn("per_capita_income",     F.col("per_capita_income_").cast("int"))
    .withColumn("hardship_index",        F.col("hardship_index").cast("int"))
)

# A linha agregada "CHICAGO" tem community_area (ca) nulo/branco → excluir.
n0 = socio.count()
socio = socio.filter(F.col("community_area").isNotNull())
log_drop(n0, socio.count(), "linha agregada CHICAGO (ca nulo)")

socio = socio.select(
    "community_area", "community_area_name", "pct_housing_crowded", "pct_below_poverty",
    "pct_unemployed", "pct_no_highschool", "pct_dependent_age", "per_capita_income", "hardship_index",
)
socio.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"{CATALOG}.silver.socioeconomic")
print(f"Silver socioeconômico: {socio.count()} linhas (esperado 77)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3) Silver — IUCR (chave de 4 dígitos + is_index)

# COMMAND ----------

i = spark.table(f"{CATALOG}.bronze.iucr_codes")
iucr = (
    i
    .withColumn("iucr", F.lpad(F.trim(F.col("iucr")), 4, "0"))
    .withColumn("iucr_primary_description",   F.trim(F.col("primary_description")))
    .withColumn("iucr_secondary_description", F.trim(F.col("secondary_description")))
    .withColumn("is_index", F.upper(F.trim(F.col("index_code"))) == "I")
    .select("iucr", "iucr_primary_description", "iucr_secondary_description", "is_index")
    .dropDuplicates(["iucr"])
)
iucr.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"{CATALOG}.silver.iucr_codes")
print(f"Silver IUCR: {iucr.count()} códigos")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verificação

# COMMAND ----------

for t in ["crimes", "socioeconomic", "iucr_codes"]:
    print(f"silver.{t}: {spark.table(f'{CATALOG}.silver.{t}').count():,} linhas")
display(spark.table(f"{CATALOG}.silver.crimes").limit(5))
