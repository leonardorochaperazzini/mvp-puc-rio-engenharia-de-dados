# Databricks notebook source
# MAGIC %md
# MAGIC # 00 · Setup — Catálogo, Schemas e Volume
# MAGIC
# MAGIC **MVP Engenharia de Dados — PUC-Rio** · Pipeline Chicago Crimes no Databricks Free Edition.
# MAGIC
# MAGIC Este notebook prepara a estrutura do Unity Catalog usada por todo o pipeline (medallion):
# MAGIC
# MAGIC - **Catálogo** `mvp_chicago`
# MAGIC - **Schemas** `bronze` (bruto), `silver` (limpo), `gold` (star schema)
# MAGIC - **Volume** `bronze.raw` para os arquivos de origem (CSV do Chicago Crimes)
# MAGIC
# MAGIC > **Free Edition:** o armazenamento é o Unity Catalog. Arquivos ficam em **Volumes**
# MAGIC > (`/Volumes/<catalog>/<schema>/<volume>/`), **não** em DBFS/`FileStore`. Padrões antigos
# MAGIC > de tutorial (`dbutils.fs.cp` para `/FileStore`, `/dbfs/...`) não funcionam aqui.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Parâmetros

# COMMAND ----------

CATALOG = "mvp_chicago"
SCHEMAS = ["bronze", "silver", "gold"]
VOLUME  = "raw"          # em bronze: /Volumes/mvp_chicago/bronze/raw
VOLUME_SCHEMA = "bronze"

print(f"Catálogo: {CATALOG}")
print(f"Schemas : {SCHEMAS}")
print(f"Volume  : /Volumes/{CATALOG}/{VOLUME_SCHEMA}/{VOLUME}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Criação do catálogo, schemas e volume
# MAGIC
# MAGIC Se a Free Edition **não permitir criar catálogo** (algumas contas só liberam o catálogo
# MAGIC `workspace`), troque `CATALOG = "workspace"` acima — o resto do pipeline funciona igual,
# MAGIC pois tudo é referenciado por `{CATALOG}.{schema}.{tabela}`.

# COMMAND ----------

spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")

for sch in SCHEMAS:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{sch}")

spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{VOLUME_SCHEMA}.{VOLUME}")

spark.sql(f"USE CATALOG {CATALOG}")
print("Estrutura criada.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Comentários de catálogo (documentação viva no Unity Catalog)
# MAGIC Parte do **Catálogo de Dados** exigido pela disciplina fica na própria plataforma.

# COMMAND ----------

spark.sql(f"COMMENT ON CATALOG {CATALOG} IS "
          "'MVP Engenharia de Dados PUC-Rio — pipeline analitico de crimes de Chicago (2012-2017).'")
spark.sql(f"COMMENT ON SCHEMA {CATALOG}.bronze IS 'Camada Bronze: ingestao bruta das fontes, sem transformacao.'")
spark.sql(f"COMMENT ON SCHEMA {CATALOG}.silver IS 'Camada Silver: dados limpos, tipados, deduplicados e conciliados.'")
spark.sql(f"COMMENT ON SCHEMA {CATALOG}.gold IS 'Camada Gold: esquema estrela (fato + dimensoes) e marts analiticos.'")
print("Comentarios aplicados.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verificação

# COMMAND ----------

display(spark.sql(f"SHOW SCHEMAS IN {CATALOG}"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Próximo passo — subir o arquivo de origem para o Volume
# MAGIC
# MAGIC 1. No menu lateral: **Catalog → `mvp_chicago` → `bronze` → Volumes → `raw`**.
# MAGIC 2. Botão **Upload to this volume** e envie `Chicago_Crimes_2012_to_2017_sample.csv`
# MAGIC    (amostra de 20%, `random_state=42` — mesma linhagem dos MVPs 1 e 2).
# MAGIC 3. Confirme o caminho abaixo. Depois, execute `01_bronze`.

# COMMAND ----------

vol_path = f"/Volumes/{CATALOG}/{VOLUME_SCHEMA}/{VOLUME}"
try:
    display(dbutils.fs.ls(vol_path))
except Exception as e:
    print(f"Volume vazio ou ainda não criado. Faça o upload do CSV. Detalhe: {e}")
