# Evidências

Screenshots da execução real no Databricks Free Edition, referenciados no `README.md`.

| Arquivo | O que evidencia | Etapa |
|---------|-----------------|-------|
| `volume_csv.png` | CSV bruto persistido no Volume do Unity Catalog + árvore bronze/silver/gold | Carga (4.2) |
| `catalogo_comentarios.png` | Catálogo de dados vivo — comentários em todas as colunas gold | Modelagem/Catálogo (4.3) |
| `qualidade_persistida.png` | Tabela `data_quality_report` (Delta) com as verificações de qualidade | Qualidade / Pipeline (4.4/4.5) |
| `dashboard.png` | Dashboard nativo respondendo as BQ1–BQ7 | Análise (4.5) |
| `resultados_consultas.md` | Saída textual das consultas BQ1–BQ7 e da integridade do star schema | Análise (4.5) |

Dashboard publicado (requer login no workspace):
https://dbc-fe5fa4ce-9950.cloud.databricks.com/dashboardsv3/01f1a4db68211e0395d4dd1268dd542d/published
