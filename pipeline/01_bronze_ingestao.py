# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Bronze — Ingestão bruta das 3 fontes
# MAGIC
# MAGIC Camada **Bronze**: cópia fiel das fontes como tabelas Delta, com metadados de linhagem
# MAGIC (`_ingested_at`, `_source`). **Sem** limpeza/transformação — isso é papel do Silver.
# MAGIC
# MAGIC | Fonte | Origem | Técnica de coleta |
# MAGIC |---|---|---|
# MAGIC | Chicago Crimes 2012–2017 | CSV no Volume (upload manual, Kaggle) | Upload → leitura Spark |
# MAGIC | Socioeconomic Indicators 2008–2012 | City of Chicago Data Portal | **API Socrata** (robô de coleta) |
# MAGIC | IUCR Codes | City of Chicago Data Portal | **API Socrata** (robô de coleta) |

# COMMAND ----------

from pyspark.sql import functions as F

CATALOG = "mvp_chicago"
VOL = f"/Volumes/{CATALOG}/bronze/raw"
CRIMES_CSV = f"{VOL}/Chicago_Crimes_2012_to_2017_sample.csv"

spark.sql(f"USE CATALOG {CATALOG}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1) Chicago Crimes — do Volume (CSV bruto)
# MAGIC Lido como string (`inferSchema=False`) para preservar o dado bruto; a tipagem correta
# MAGIC acontece no Silver. `header=True`, aspas multi-linha tratadas.

# COMMAND ----------

crimes_raw = (
    spark.read
    .option("header", True)
    .option("inferSchema", False)
    .option("multiLine", True)
    .option("escape", '"')
    .csv(CRIMES_CSV)
)

# Delta não aceita espaços/caracteres especiais em nomes de coluna → padroniza p/ snake_case.
import re
def _clean(c):
    return re.sub(r"[ ,;{}()\n\t=]+", "_", c.strip()).lower()
crimes_raw = crimes_raw.toDF(*[_clean(c) for c in crimes_raw.columns])

crimes_raw = (
    crimes_raw
    .withColumn("_ingested_at", F.current_timestamp())
    .withColumn("_source", F.lit("kaggle:currie32/crimes-in-chicago (sample 20%)"))
)

print(f"Linhas cruas: {crimes_raw.count():,}")
print(f"Colunas: {len(crimes_raw.columns)}")
crimes_raw.write.mode("overwrite").saveAsTable(f"{CATALOG}.bronze.crimes")
display(crimes_raw.limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2) Indicadores socioeconômicos — API Socrata
# MAGIC Recurso `kn9c-c2s2` (Selected socioeconomic indicators in Chicago, 2008–2012).
# MAGIC Coleta programática via HTTP; 78 linhas (77 áreas + linha agregada "CHICAGO").

# COMMAND ----------

import pandas as pd

SOCIO_URL = "https://data.cityofchicago.org/resource/kn9c-c2s2.csv?$limit=100"
socio_pd = pd.read_csv(SOCIO_URL)
print(f"Linhas socioeconômico: {len(socio_pd)}  (esperado 78: 77 áreas + CHICAGO)")

socio_raw = (
    spark.createDataFrame(socio_pd)
    .withColumn("_ingested_at", F.current_timestamp())
    .withColumn("_source", F.lit("socrata:data.cityofchicago.org/kn9c-c2s2"))
)
socio_raw.write.mode("overwrite").option("mergeSchema", True).saveAsTable(f"{CATALOG}.bronze.socioeconomic")
display(socio_raw)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3) Códigos IUCR — API Socrata
# MAGIC Recurso `c7ck-438e` (Chicago Police Department Illinois Uniform Crime Reporting codes).
# MAGIC Traz `iucr`, `primary_description`, `secondary_description` e **`index_code`** (I = index / N = non-index).

# COMMAND ----------

IUCR_URL = "https://data.cityofchicago.org/resource/c7ck-438e.csv?$limit=2000"
iucr_pd = pd.read_csv(IUCR_URL, dtype=str)
print(f"Linhas IUCR: {len(iucr_pd)}")

iucr_raw = (
    spark.createDataFrame(iucr_pd)
    .withColumn("_ingested_at", F.current_timestamp())
    .withColumn("_source", F.lit("socrata:data.cityofchicago.org/c7ck-438e"))
)
iucr_raw.write.mode("overwrite").option("mergeSchema", True).saveAsTable(f"{CATALOG}.bronze.iucr_codes")
display(iucr_raw.limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verificação da camada Bronze

# COMMAND ----------

for t in ["crimes", "socioeconomic", "iucr_codes"]:
    n = spark.table(f"{CATALOG}.bronze.{t}").count()
    print(f"bronze.{t}: {n:,} linhas")

display(spark.sql(f"SHOW TABLES IN {CATALOG}.bronze"))
