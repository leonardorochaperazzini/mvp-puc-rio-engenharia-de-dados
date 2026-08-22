# Objetivo do MVP

Este documento foi escrito e versionado antes de qualquer coleta ou transformação, como
pede a disciplina. Não removo nenhuma pergunta ao longo do trabalho, mesmo as que não
consiga responder; a discussão sobre o que foi atingido está na autoavaliação, no
`README.md`.

## O problema

Chicago publica o registro de todas as ocorrências criminais da cidade. Só que esse dado
bruto vem num formato transacional, uma linha por ocorrência com 22 colunas de tipos
misturados, que não ajuda muito na hora de analisar: não há dimensões prontas de tempo,
local ou tipo de crime, existem duplicidades e valores inválidos, e nada liga o crime ao
contexto socioeconômico do bairro.

A proposta deste MVP é construir um pipeline na nuvem, no Databricks, que colete, limpe,
modele em esquema estrela e carregue esses dados num Data Warehouse. Com isso dá para
responder perguntas sobre padrões de criminalidade e de prisão em Chicago usando SQL e
dashboards.

O foco aqui não é treinar modelos de machine learning, que foi o assunto dos MVPs 1 e 2. É
entregar uma base analítica organizada, documentada e fácil de consultar.

## Perguntas de negócio

As quatro primeiras continuam as hipóteses (H1–H4) que investiguei nos MVPs anteriores,
agora respondidas em cima do Data Warehouse. As três últimas são novas e só existem porque
cruzei os crimes com fontes externas.

| #    | Pergunta | Origem |
|------|----------|--------|
| BQ1  | Quais são os tipos de crime mais frequentes e qual a taxa de prisão de cada um? | H1 |
| BQ2  | Crimes domésticos têm taxa de prisão diferente dos demais? | H2 |
| BQ3  | Existe padrão temporal (hora, turno, dia da semana) na criminalidade e na taxa de prisão? | H3 |
| BQ4  | Como a criminalidade evoluiu de 2012 a 2017, e há sazonalidade ao longo do ano? | H4 |
| BQ5  | Quais bairros (community areas) concentram mais crimes? | nova |
| BQ6  | A quantidade de crimes e a taxa de prisão têm relação com os indicadores socioeconômicos do bairro (renda, pobreza, hardship)? | nova (join) |
| BQ7  | Crimes graves (index, na classificação do FBI) se distribuem e se resolvem de forma diferente dos non-index? | nova (join) |

## Fontes escolhidas

| Fonte | O que é | Papel | Licença |
|-------|---------|-------|---------|
| Chicago Crimes 2012–2017 | Ocorrências criminais (Kaggle, `currie32/crimes-in-chicago`). Mesma base dos MVPs 1 e 2. | Fato | dado público |
| Socioeconomic Indicators 2008–2012 | Renda per capita, pobreza, desemprego, escolaridade e hardship index por bairro (77 áreas). | Enriquece `dim_community_area` | Open Data (City of Chicago) |
| IUCR Codes | Referência de códigos IUCR: descrição e se o crime é index ou não. | Enriquece `dim_crime_type` | Open Data (City of Chicago) |

Os crimes se ligam ao socioeconômico pela community area (1–77) e à referência IUCR pelo
código IUCR.

## O que considero sucesso

- Pipeline Bronze → Silver → Gold rodando de ponta a ponta no Databricks Free Edition.
- Esquema estrela na camada Gold, com fato e dimensões consolidadas.
- Catálogo de dados com domínios e categorias, mais a linhagem documentada.
- Análise de qualidade atributo por atributo, com os problemas encontrados e resolvidos.
- BQ1 a BQ7 respondidas por SQL, cada uma com uma discussão que liga o número à pergunta.
- Evidências (prints do volume, do catálogo e do dashboard) no repositório.

## Limitações que já assumo desde o começo

A principal é temporal. Os indicadores socioeconômicos são de 2008–2012 e os crimes vão de
2012 a 2017. Então qualquer relação da BQ6 é uma foto transversal, comparada com um retrato
que é anterior à maior parte do período dos crimes. Serve para descrever, não para dizer que
uma coisa causa a outra nem que são do mesmo momento. Volto nisso na autoavaliação.

A outra é a amostragem: para caber nos limites da versão gratuita e manter a linhagem igual
à dos MVPs anteriores, uso a amostra de 20% (`random_state=42`). O detalhe fica no
`linhagem.md`.
