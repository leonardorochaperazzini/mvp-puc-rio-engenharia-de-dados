# Databricks notebook source
# MAGIC %md
# MAGIC # 05 · Análise — Respostas às perguntas de negócio
# MAGIC
# MAGIC Consultas SQL sobre o esquema estrela (`mvp_chicago.gold`) respondendo BQ1 a BQ7.
# MAGIC Cada bloco traz a query, o resultado e uma discussão do que os números significam.
# MAGIC As mesmas consultas alimentam o dashboard nativo do Databricks (ver README).
# MAGIC
# MAGIC > As discussões abaixo trazem a leitura esperada e devem ser conferidas com os números
# MAGIC > que aparecerem na sua execução — a base pode variar conforme a amostra usada.

# COMMAND ----------

# MAGIC %sql
# MAGIC USE CATALOG mvp_chicago;
# MAGIC USE SCHEMA gold;

# COMMAND ----------

# MAGIC %md
# MAGIC ## BQ1 — Tipos de crime mais frequentes e taxa de prisão por tipo

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT ct.primary_type,
# MAGIC        COUNT(*)                                        AS total,
# MAGIC        SUM(CASE WHEN f.is_arrest THEN 1 ELSE 0 END)    AS prisoes,
# MAGIC        ROUND(100.0 * AVG(CASE WHEN f.is_arrest THEN 1 ELSE 0 END), 1) AS taxa_prisao_pct
# MAGIC FROM fact_crime f
# MAGIC JOIN dim_crime_type ct ON f.crime_type_key = ct.crime_type_key
# MAGIC GROUP BY ct.primary_type
# MAGIC ORDER BY total DESC
# MAGIC LIMIT 20;

# COMMAND ----------

# MAGIC %md
# MAGIC **Discussão.** Poucos tipos concentram a maior parte das ocorrências (roubo, furto,
# MAGIC dano, agressão), mas a taxa de prisão varia muito entre eles: crimes que exigem
# MAGIC flagrante ou têm autor identificável no ato — como porte de entorpecentes, prostituição
# MAGIC e jogo — chegam a taxas próximas de 100%, enquanto furtos e arrombamentos ficam bem
# MAGIC abaixo da média. Isso responde H1: **a taxa de prisão não é uniforme; depende da
# MAGIC natureza do crime**. Confirme na sua execução quais tipos lideram cada extremo.

# COMMAND ----------

# MAGIC %md
# MAGIC ## BQ2 — Crimes domésticos têm taxa de prisão diferente?

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT is_domestic,
# MAGIC        COUNT(*)                                                       AS total,
# MAGIC        ROUND(100.0 * AVG(CASE WHEN is_arrest THEN 1 ELSE 0 END), 1)   AS taxa_prisao_pct
# MAGIC FROM fact_crime
# MAGIC GROUP BY is_domestic;

# COMMAND ----------

# MAGIC %md
# MAGIC **Discussão.** Comparando os dois grupos vê-se se o caráter doméstico do crime muda a
# MAGIC probabilidade de prisão (H2). Em geral crimes domésticos envolvem vítima e agressor
# MAGIC conhecidos, o que tende a facilitar a responsabilização — verifique se a taxa do grupo
# MAGIC doméstico fica acima da do não doméstico e por qual margem.

# COMMAND ----------

# MAGIC %md
# MAGIC ## BQ3 — Padrão temporal (turno, hora e dia da semana)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT t.shift,
# MAGIC        COUNT(*)                                                      AS total,
# MAGIC        ROUND(100.0 * AVG(CASE WHEN f.is_arrest THEN 1 ELSE 0 END), 1) AS taxa_prisao_pct
# MAGIC FROM fact_crime f
# MAGIC JOIN dim_time t ON f.time_key = t.time_key
# MAGIC GROUP BY t.shift
# MAGIC ORDER BY total DESC;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT d.day_of_week,
# MAGIC        COUNT(*) AS total,
# MAGIC        ROUND(100.0 * AVG(CASE WHEN f.is_arrest THEN 1 ELSE 0 END), 1) AS taxa_prisao_pct
# MAGIC FROM fact_crime f
# MAGIC JOIN dim_date d ON f.date_key = d.date_key
# MAGIC GROUP BY d.day_of_week
# MAGIC ORDER BY total DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC **Discussão.** O volume de crimes costuma subir à tarde e à noite, enquanto a taxa de
# MAGIC prisão tende a ser menor justamente nos horários de maior volume — reforçando H3, de
# MAGIC que crimes noturnos são menos resolvidos no ato. O recorte por dia da semana mostra se
# MAGIC há concentração no fim de semana. Confirme onde ficam os picos de volume e de prisão.

# COMMAND ----------

# MAGIC %md
# MAGIC ## BQ4 — Evolução anual (2012–2017) e sazonalidade mensal

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT d.year, COUNT(*) AS total,
# MAGIC        ROUND(100.0 * AVG(CASE WHEN f.is_arrest THEN 1 ELSE 0 END), 1) AS taxa_prisao_pct
# MAGIC FROM fact_crime f JOIN dim_date d ON f.date_key = d.date_key
# MAGIC GROUP BY d.year ORDER BY d.year;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT d.month, d.month_name, COUNT(*) AS total
# MAGIC FROM fact_crime f JOIN dim_date d ON f.date_key = d.date_key
# MAGIC GROUP BY d.month, d.month_name ORDER BY d.month;

# COMMAND ----------

# MAGIC %md
# MAGIC **Discussão.** A série anual mostra a tendência da criminalidade no período (H4) — nos
# MAGIC dados de Chicago costuma haver queda até 2015/2016 e alguma retomada depois. O recorte
# MAGIC mensal expõe sazonalidade: meses quentes (verão do hemisfério norte, jun–ago)
# MAGIC concentram mais ocorrências. Verifique a direção da tendência na sua amostra.

# COMMAND ----------

# MAGIC %md
# MAGIC ## BQ5 — Community areas com mais crimes

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT ca.community_area, ca.community_area_name, COUNT(*) AS total
# MAGIC FROM fact_crime f
# MAGIC JOIN dim_community_area ca ON f.community_area_key = ca.community_area_key
# MAGIC WHERE ca.community_area_key > 0
# MAGIC GROUP BY ca.community_area, ca.community_area_name
# MAGIC ORDER BY total DESC
# MAGIC LIMIT 15;

# COMMAND ----------

# MAGIC %md
# MAGIC **Discussão.** A criminalidade se concentra geograficamente em poucos bairros. Guarde
# MAGIC os nomes do topo da lista — eles reaparecem em BQ6 quando cruzamos com os indicadores
# MAGIC socioeconômicos.

# COMMAND ----------

# MAGIC %md
# MAGIC ## BQ6 — Crime e prisão × indicadores socioeconômicos (join)

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Volume e taxa de prisão por quartil de privação (hardship): 1 = menor, 4 = maior
# MAGIC SELECT ca.hardship_quartile,
# MAGIC        COUNT(*)                                     AS total_crimes,
# MAGIC        ROUND(AVG(ca.per_capita_income))             AS renda_media,
# MAGIC        ROUND(100.0 * AVG(CASE WHEN f.is_arrest THEN 1 ELSE 0 END), 1) AS taxa_prisao_pct
# MAGIC FROM fact_crime f
# MAGIC JOIN dim_community_area ca ON f.community_area_key = ca.community_area_key
# MAGIC WHERE ca.community_area_key > 0
# MAGIC GROUP BY ca.hardship_quartile
# MAGIC ORDER BY ca.hardship_quartile;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Correlação bairro a bairro entre indicadores e nº de crimes
# MAGIC WITH por_area AS (
# MAGIC   SELECT ca.community_area, COUNT(*) AS crimes,
# MAGIC          MAX(ca.per_capita_income) AS renda, MAX(ca.hardship_index) AS hardship,
# MAGIC          MAX(ca.pct_below_poverty) AS pobreza
# MAGIC   FROM fact_crime f JOIN dim_community_area ca ON f.community_area_key = ca.community_area_key
# MAGIC   WHERE ca.community_area_key > 0
# MAGIC   GROUP BY ca.community_area
# MAGIC )
# MAGIC SELECT ROUND(corr(crimes, renda), 3)    AS corr_crimes_renda,
# MAGIC        ROUND(corr(crimes, hardship), 3) AS corr_crimes_hardship,
# MAGIC        ROUND(corr(crimes, pobreza), 3)  AS corr_crimes_pobreza
# MAGIC FROM por_area;

# COMMAND ----------

# MAGIC %md
# MAGIC **Discussão.** Aqui está o valor de cruzar as duas fontes: dá para ver se bairros mais
# MAGIC vulneráveis (maior hardship, menor renda) concentram mais crimes. Uma correlação
# MAGIC negativa entre renda e nº de crimes, e positiva entre hardship e crimes, confirmaria
# MAGIC essa leitura.
# MAGIC
# MAGIC **Limitação importante:** os indicadores socioeconômicos são de **2008–2012** e os
# MAGIC crimes de **2012–2017**. A associação é transversal, contra um retrato anterior à maior
# MAGIC parte da janela — serve para descrever, não para afirmar causa nem relação
# MAGIC contemporânea. Isso é retomado na Autoavaliação.

# COMMAND ----------

# MAGIC %md
# MAGIC ## BQ7 — Crimes index (graves) × non-index (join IUCR)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT ct.is_index,
# MAGIC        COUNT(*)                                                      AS total,
# MAGIC        ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)            AS pct_do_total,
# MAGIC        ROUND(100.0 * AVG(CASE WHEN f.is_arrest THEN 1 ELSE 0 END), 1) AS taxa_prisao_pct
# MAGIC FROM fact_crime f
# MAGIC JOIN dim_crime_type ct ON f.crime_type_key = ct.crime_type_key
# MAGIC GROUP BY ct.is_index;

# COMMAND ----------

# MAGIC %md
# MAGIC **Discussão.** A classificação index (crimes graves/violentos, padrão FBI) separa o que
# MAGIC mais preocupa em segurança pública do restante. Normalmente os crimes index têm taxa de
# MAGIC prisão **menor** que os non-index — estes últimos incluem muito flagrante (drogas,
# MAGIC perturbação da ordem). Confirme a diferença na sua execução.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Síntese
# MAGIC As respostas se conectam: o crime em Chicago é concentrado em poucos tipos, poucos
# MAGIC bairros e certos horários, e a chance de prisão depende muito mais da natureza do crime
# MAGIC (flagrante vs. investigação) do que do volume. O cruzamento socioeconômico sugere
# MAGIC associação entre vulnerabilidade do bairro e criminalidade, sempre lida com a ressalva
# MAGIC temporal. A discussão fechada, com os números finais, está no README.
