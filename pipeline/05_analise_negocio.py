# Databricks notebook source
# MAGIC %md
# MAGIC # 05 · Análise — Respostas às perguntas de negócio
# MAGIC
# MAGIC Consultas SQL sobre o esquema estrela (`mvp_chicago.gold`) respondendo BQ1 a BQ7.
# MAGIC Cada bloco traz a query, o resultado e uma discussão do que os números significam.
# MAGIC As mesmas consultas alimentam o dashboard nativo do Databricks (ver README).
# MAGIC
# MAGIC > As discussões trazem os números obtidos na execução sobre a amostra de 20%. Se você
# MAGIC > rodar com a base completa os valores mudam um pouco, mas as tendências se mantêm.

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
# MAGIC **Discussão.** Os tipos mais frequentes são THEFT (65,8 mil), BATTERY (52,8 mil) e
# MAGIC CRIMINAL DAMAGE (31,2 mil), mas a taxa de prisão varia enormemente entre eles. No topo
# MAGIC aparecem crimes que dependem de flagrante: PROSTITUTION (99,6%) e NARCOTICS (99,3%) são
# MAGIC quase sempre registrados com prisão, porque a ocorrência já nasce da abordagem policial.
# MAGIC No extremo oposto estão os crimes contra o patrimônio, que dependem de investigação:
# MAGIC BURGLARY (5,3%), CRIMINAL DAMAGE (6,4%) e MOTOR VEHICLE THEFT (7,1%). Isso confirma H1
# MAGIC de forma bem clara: a taxa de prisão não é uniforme, ela é definida pela natureza do
# MAGIC crime — se há autor identificável no ato ou não.

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
# MAGIC **Discussão.** O resultado contraria a intuição de H2. Eu esperava que crimes
# MAGIC domésticos tivessem taxa de prisão maior, já que costumam ter vítima e agressor
# MAGIC conhecidos. Nos dados acontece o contrário: crimes domésticos têm taxa de prisão de
# MAGIC 19,7%, contra 27,0% dos não domésticos. Uma leitura possível é que boa parte das
# MAGIC ocorrências domésticas é registrada por causa da denúncia da vítima, sem que haja
# MAGIC flagrante ou condições de prisão no momento — e casos de violência doméstica muitas
# MAGIC vezes seguem por outras vias que não a prisão imediata. Vale manter a hipótese anterior
# MAGIC e registrar que, aqui, ela não se sustentou.

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
# MAGIC **Discussão.** O volume realmente sobe à noite (92,7 mil) e à tarde (91,5 mil), e cai
# MAGIC na madrugada (45,3 mil). Mas H3 não se confirmou do jeito esperado: eu imaginava taxa de
# MAGIC prisão menor à noite, e é justamente a noite que tem a maior taxa (30,9%), enquanto a
# MAGIC madrugada tem a menor (20,6%). Ou seja, no período de maior atividade policial noturna
# MAGIC prende-se proporcionalmente mais, não menos. O padrão temporal existe (H3), mas na
# MAGIC direção contrária à que eu supunha — outro caso em que os dados corrigem a intuição.

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
# MAGIC **Discussão.** A criminalidade cai de forma consistente no período (H4): de 67,3 mil
# MAGIC ocorrências em 2012 para cerca de 53 mil em 2016. 2017 aparece com só 2,2 mil porque a
# MAGIC amostra cobre apenas o começo do ano, então esse ponto não deve ser lido como queda
# MAGIC real. Chama atenção a taxa de prisão, estável perto de 27–28% até 2015 e caindo para
# MAGIC 18,8% em 2016 — uma mudança que vale investigar (pode refletir mudança de política de
# MAGIC policiamento no período). O recorte mensal ajuda a ver a sazonalidade de verão.

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
# MAGIC **Discussão.** A criminalidade é bastante concentrada no território. Austin lidera com
# MAGIC folga (quase 19 mil ocorrências), seguido de Near North Side, South Shore, Humboldt Park
# MAGIC e North Lawndale. É uma mistura de bairros de alta vulnerabilidade (Austin, North
# MAGIC Lawndale, West Englewood) com áreas centrais de grande circulação (Near North Side,
# MAGIC Loop). Vários desses nomes voltam na BQ6, quando cruzamos com renda e privação.

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
# MAGIC **Discussão.** É aqui que o join entrega valor. Agrupando por quartil de privação há um
# MAGIC gradiente nítido: o quartil mais vulnerável (4) tem 86,1 mil crimes e renda média de
# MAGIC US$ 12,7 mil, enquanto o menos vulnerável (1) tem 71,9 mil crimes e renda de US$ 53,2
# MAGIC mil. E não é só o volume — a taxa de prisão também sobe com a privação, de 19,4% no
# MAGIC quartil 1 para 32,3% no quartil 4. A correlação bairro a bairro entre número de crimes e
# MAGIC percentual de pobreza é positiva (0,31); com o hardship index é 0,18; com renda per
# MAGIC capita é praticamente nula (0,03). Ou seja, pobreza acompanha melhor a criminalidade do
# MAGIC que a renda média isolada.
# MAGIC
# MAGIC **Limitação importante:** os indicadores socioeconômicos são de 2008–2012 e os crimes de
# MAGIC 2012–2017. A associação é transversal, comparada com um retrato anterior à maior parte da
# MAGIC janela dos crimes. Serve para descrever, não para afirmar causa nem relação
# MAGIC contemporânea. Volto nisso na autoavaliação.

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
# MAGIC **Discussão.** Os crimes index (graves/violentos, padrão FBI) são 41,5% do total e têm
# MAGIC taxa de prisão de apenas 11,0%. Os non-index, 58,5% do total, têm 36,5% de prisão — mais
# MAGIC de três vezes. O motivo é o mesmo que apareceu na BQ1: o grupo non-index concentra
# MAGIC drogas, perturbação da ordem e afins, que são registrados em flagrante, enquanto os
# MAGIC crimes index (roubo, furto, arrombamento) dependem de investigação. É um resultado
# MAGIC importante para segurança pública: justamente os crimes que mais preocupam são os que
# MAGIC menos terminam em prisão.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Síntese
# MAGIC As respostas se conectam em torno de um fio central: **a chance de prisão em Chicago
# MAGIC depende muito mais da natureza do crime — flagrante vs. investigação — do que do
# MAGIC volume**. Crimes de flagrante (drogas, prostituição) prendem quase sempre; crimes contra
# MAGIC o patrimônio, quase nunca. Isso reaparece na BQ7: os crimes graves (index) são os que
# MAGIC menos terminam em prisão.
# MAGIC
# MAGIC Duas hipóteses dos MVPs anteriores não se sustentaram nos dados e ficam registradas
# MAGIC assim: crimes domésticos prendem menos, não mais (BQ2), e a noite tem a maior taxa de
# MAGIC prisão, não a menor (BQ3). O cruzamento socioeconômico (BQ6) mostra associação clara
# MAGIC entre privação do bairro e criminalidade, sempre com a ressalva de que os indicadores
# MAGIC são de um período anterior. A discussão fechada está na autoavaliação do README.
