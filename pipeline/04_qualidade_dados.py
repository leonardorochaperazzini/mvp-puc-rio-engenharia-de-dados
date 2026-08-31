# Databricks notebook source
# MAGIC %md
# MAGIC # 04 · Qualidade de Dados (análise por atributo)
# MAGIC
# MAGIC Análise de qualidade **para cada atributo**, comparando Bronze (bruto) e Silver (limpo).
# MAGIC A saída numérica (min/max, categorias, nulos) **alimenta o `docs/catalogo_de_dados.md`**.
# MAGIC
# MAGIC Problemas esperados e como foram tratados:
# MAGIC
# MAGIC | Problema | Onde | Tratamento (Silver/Gold) |
# MAGIC |---|---|---|
# MAGIC | Duplicidade de `ID` | crimes | `dropDuplicates(["id"])` |
# MAGIC | Coluna de índice sem nome | crimes | descartada |
# MAGIC | Coordenadas `(0,0)`/fora de Chicago | crimes | anuladas (linha mantida) |
# MAGIC | Datas fora de 2012–2017 | crimes | filtradas |
# MAGIC | `Community Area` = 0/nula | crimes | mapeada p/ membro -1 (desconhecido) |
# MAGIC | Linha agregada "CHICAGO" | socioeconômico | excluída antes do join |
# MAGIC | Nulos em Ward/District/Location | crimes | mantidos e reportados |

# COMMAND ----------

from pyspark.sql import functions as F

CATALOG = "mvp_chicago"
spark.sql(f"USE CATALOG {CATALOG}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Perfil genérico por atributo (nulos, distintos)

# COMMAND ----------

def profile(df):
    n = df.count()
    rows = []
    for c, t in df.dtypes:
        nulls = df.filter(F.col(c).isNull()).count()
        distinct = df.select(c).distinct().count()
        rows.append((c, t, n, nulls, round(100 * nulls / n, 2) if n else 0.0, distinct))
    return spark.createDataFrame(
        rows, ["coluna", "tipo", "linhas", "nulos", "pct_nulos", "distintos"]
    )

crimes_s = spark.table(f"{CATALOG}.silver.crimes")
display(profile(crimes_s))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Efeito da deduplicação (Bronze → Silver)

# COMMAND ----------

nb = spark.table(f"{CATALOG}.bronze.crimes").count()
ns = crimes_s.count()
dup_ids = (spark.table(f"{CATALOG}.bronze.crimes")
           .groupBy("ID").count().filter("count > 1").count())
print(f"Bronze crimes : {nb:,}")
print(f"Silver crimes : {ns:,}")
print(f"Removidas total (dupes + filtros de qualidade): {nb - ns:,}")
print(f"IDs com duplicidade no bronze: {dup_ids:,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Domínios numéricos (min/max/média) — reaproveitado no Catálogo

# COMMAND ----------

num_cols = ["beat", "district", "ward", "community_area", "year", "latitude", "longitude"]
display(crimes_s.select([F.min(c).alias(f"{c}_min") for c in num_cols] +
                        [F.max(c).alias(f"{c}_max") for c in num_cols]))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Domínios categóricos

# COMMAND ----------

print("Primary Type (top 15 de", crimes_s.select("primary_type").distinct().count(), "categorias):")
display(crimes_s.groupBy("primary_type").count().orderBy(F.desc("count")).limit(15))

# COMMAND ----------

print("Location Description (cauda longa —", crimes_s.select("location_description").distinct().count(), "categorias):")
display(crimes_s.groupBy("location_description").count().orderBy(F.desc("count")).limit(15))

# COMMAND ----------

print("Booleanos:")
display(crimes_s.groupBy("arrest").count())
display(crimes_s.groupBy("domestic").count())

# COMMAND ----------

# MAGIC %md
# MAGIC ## Checagens espaciais e temporais

# COMMAND ----------

print("Coords nulas (anuladas no silver):", crimes_s.filter(F.col("latitude").isNull()).count())
print("Community area = -1/desconhecida no fato:",
      spark.table(f"{CATALOG}.gold.fact_crime").filter("community_area_key = -1").count())
print("Anos presentes:")
display(crimes_s.groupBy("year").count().orderBy("year"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Qualidade das fontes de enriquecimento

# COMMAND ----------

print("Socioeconômico (esperado 77 áreas, sem CHICAGO):")
display(profile(spark.table(f"{CATALOG}.silver.socioeconomic")))

# Cobertura do join: quantas community areas dos crimes existem no socioeconômico?
crimes_ca = crimes_s.select("community_area").distinct().filter("community_area between 1 and 77")
socio_ca = spark.table(f"{CATALOG}.silver.socioeconomic").select("community_area")
sem_match = crimes_ca.join(socio_ca, "community_area", "left_anti").count()
print(f"Community areas válidas nos crimes sem match no socioeconômico: {sem_match} (esperado 0)")

# COMMAND ----------

print("IUCR — cobertura do join:")
crimes_iucr = crimes_s.select("iucr").distinct()
ref_iucr = spark.table(f"{CATALOG}.silver.iucr_codes").select("iucr")
sem_iucr = crimes_iucr.join(ref_iucr, "iucr", "left_anti").count()
print(f"Códigos IUCR nos crimes sem match na referência: {sem_iucr} "
      f"(de {crimes_iucr.count()} distintos) → tratados como is_index=False")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Relatório de qualidade persistido
# MAGIC Grava as verificações numa tabela (`gold.data_quality_report`) — vira evidência
# MAGIC reproduzível e é o embrião de testes automatizados de qualidade (trabalhos futuros).
# MAGIC Distingue **problema real detectado** de **guarda defensiva que não disparou** nesta amostra.

# COMMAND ----------

nb = spark.table(f"{CATALOG}.bronze.crimes").count()
ns = crimes_s.count()
dups = (spark.table(f"{CATALOG}.bronze.crimes").groupBy("ID").count().filter("count>1").count())
lat_null = crimes_s.filter(F.col("latitude").isNull()).count()
fact = spark.table(f"{CATALOG}.gold.fact_crime")
ca_unknown = fact.filter("community_area_key=-1").count()
loc_unknown = fact.filter("location_key=-1").count()
socio_b = spark.table(f"{CATALOG}.bronze.socioeconomic").count()
socio_s = spark.table(f"{CATALOG}.silver.socioeconomic").count()

report = spark.createDataFrame([
    ("crimes", "duplicidade de ID", "guarda defensiva", dups, "dedupe por id (nao disparou nesta amostra)"),
    ("crimes", "ano fora de 2012-2017", "guarda defensiva", nb - ns, "filtro de janela (nao disparou; amostra ja limpa)"),
    ("crimes", "coordenadas invalidas/(0,0)/fora de Chicago", "problema real", lat_null, "lat/long anulados; linha mantida"),
    ("crimes", "community area 0/nula", "problema real", ca_unknown, "mapeado p/ membro -1 em dim_community_area"),
    ("crimes", "location description ausente", "problema real", loc_unknown, "mapeado p/ membro -1 em dim_location"),
    ("socioeconomic", "linha agregada CHICAGO", "problema real", socio_b - socio_s, "excluida antes do join (78->77)"),
], ["tabela", "verificacao", "natureza", "linhas_afetadas", "tratamento"])

report.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"{CATALOG}.gold.data_quality_report")
display(report)
