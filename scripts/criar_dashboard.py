#!/usr/bin/env python3
"""Cria/atualiza e publica o dashboard Lakeview (BQ1-BQ7) via API do Databricks.

Requer o Databricks CLI autenticado (`databricks auth login --host <workspace>`).
Ajuste WAREHOUSE (databricks warehouses list) e PARENT (seu diretório de workspace).
Uso: `python3 scripts/criar_dashboard.py [dashboard_id]`  (sem id cria um novo).
"""
import json, subprocess
WAREHOUSE = "68dd56f8ca778e98"          # id do SQL warehouse serverless
PARENT = "/Users/leonardoperazzini@gmail.com"  # pasta do workspace onde salvar

def api(method, path, payload=None):
    cmd = ["databricks", "api", method.lower(), path]
    if payload is not None:
        cmd += ["--json", json.dumps(payload)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{method} {path}:\n{r.stderr}\n{r.stdout}")
    return json.loads(r.stdout) if r.stdout.strip() else {}

def ds(name, disp, sql):
    return {"name": name, "displayName": disp, "queryLines": [sql]}

def _chart(wtype, wname, dsname, xcol, ycol, xlab, ylab, title, x, y, w=3, h=6):
    qname = f"{wname}_query"
    ymeas = f"sum({ycol})"
    return {
        "widget": {
            "name": wname,
            "queries": [{"name": qname, "query": {
                "datasetName": dsname,
                "fields": [
                    {"name": xcol, "expression": f"`{xcol}`"},
                    {"name": ymeas, "expression": f"SUM(`{ycol}`)"},
                ],
                "disaggregated": False,
            }}],
            "spec": {
                "version": 3,
                "widgetType": wtype,
                "frame": {"showTitle": True, "title": {"value": title, "fields": []}},
                "encodings": {
                    "x": {"fieldName": xcol, "scale": {"type": "categorical"}, "displayName": xlab},
                    "y": {"fieldName": ymeas, "scale": {"type": "quantitative"}, "displayName": ylab},
                },
                "data": {"queryName": qname},
            },
        },
        "position": {"x": x, "y": y, "width": w, "height": h},
    }

def bar(*a, **k):  return _chart("bar", *a, **k)
def line(*a, **k): return _chart("line", *a, **k)

G = "mvp_chicago.gold"
datasets = [
    ds("bq1", "BQ1 tipos", f"""SELECT ct.primary_type, COUNT(*) total,
        ROUND(100.0*AVG(CASE WHEN f.is_arrest THEN 1 ELSE 0 END),1) taxa_prisao
        FROM {G}.fact_crime f JOIN {G}.dim_crime_type ct ON f.crime_type_key=ct.crime_type_key
        GROUP BY ct.primary_type ORDER BY total DESC LIMIT 10"""),
    ds("bq4", "BQ4 ano", f"""SELECT d.year, COUNT(*) total,
        ROUND(100.0*AVG(CASE WHEN f.is_arrest THEN 1 ELSE 0 END),1) taxa_prisao
        FROM {G}.fact_crime f JOIN {G}.dim_date d ON f.date_key=d.date_key
        WHERE d.year<2017 GROUP BY d.year ORDER BY d.year"""),
    ds("bq5", "BQ5 bairros", f"""SELECT ca.community_area_name bairro, COUNT(*) total
        FROM {G}.fact_crime f JOIN {G}.dim_community_area ca ON f.community_area_key=ca.community_area_key
        WHERE ca.community_area_key>0 GROUP BY ca.community_area_name ORDER BY total DESC LIMIT 10"""),
    ds("bq6", "BQ6 privacao", f"""SELECT ca.hardship_quartile quartil, COUNT(*) total,
        ROUND(100.0*AVG(CASE WHEN f.is_arrest THEN 1 ELSE 0 END),1) taxa_prisao
        FROM {G}.fact_crime f JOIN {G}.dim_community_area ca ON f.community_area_key=ca.community_area_key
        WHERE ca.community_area_key>0 GROUP BY ca.hardship_quartile ORDER BY ca.hardship_quartile"""),
    ds("bq7", "BQ7 index", f"""SELECT CASE WHEN ct.is_index THEN 'Index (graves)' ELSE 'Non-index' END tipo,
        COUNT(*) total, ROUND(100.0*AVG(CASE WHEN f.is_arrest THEN 1 ELSE 0 END),1) taxa_prisao
        FROM {G}.fact_crime f JOIN {G}.dim_crime_type ct ON f.crime_type_key=ct.crime_type_key
        GROUP BY ct.is_index"""),
    ds("bq2", "BQ2 domestico", f"""SELECT CASE WHEN is_domestic THEN 'Domestico' ELSE 'Nao domestico' END tipo,
        COUNT(*) total, ROUND(100.0*AVG(CASE WHEN is_arrest THEN 1 ELSE 0 END),1) taxa_prisao
        FROM {G}.fact_crime GROUP BY is_domestic"""),
    ds("bq3", "BQ3 turno", f"""SELECT t.shift turno, COUNT(*) total,
        ROUND(100.0*AVG(CASE WHEN f.is_arrest THEN 1 ELSE 0 END),1) taxa_prisao
        FROM {G}.fact_crime f JOIN {G}.dim_time t ON f.time_key=t.time_key
        GROUP BY t.shift ORDER BY total DESC"""),
]

widgets = [
    bar("w1", "bq1", "primary_type", "total", "Tipo de crime", "Ocorrências",
        "BQ1 · Tipos mais frequentes", 0, 0),
    bar("w1b", "bq1", "primary_type", "taxa_prisao", "Tipo", "Taxa de prisão %",
        "BQ1 · Taxa de prisão por tipo", 3, 0),
    line("w4", "bq4", "year", "total", "Ano", "Ocorrências",
         "BQ4 · Evolução anual (2012–2016)", 0, 6),
    bar("w5", "bq5", "bairro", "total", "Bairro", "Ocorrências",
        "BQ5 · Bairros com mais crimes", 3, 6),
    bar("w6", "bq6", "quartil", "taxa_prisao", "Quartil de privação (1=menor,4=maior)",
        "Taxa de prisão %", "BQ6 · Prisão × privação socioeconômica", 0, 12),
    bar("w7", "bq7", "tipo", "taxa_prisao", "Classe", "Taxa de prisão %",
        "BQ7 · Index vs non-index", 3, 12),
    bar("w2", "bq2", "tipo", "taxa_prisao", "Classe", "Taxa de prisão %",
        "BQ2 · Doméstico vs não doméstico", 0, 18),
    bar("w3", "bq3", "turno", "taxa_prisao", "Turno", "Taxa de prisão %",
        "BQ3 · Taxa de prisão por turno", 3, 18),
]

serialized = {"datasets": datasets, "pages": [{
    "name": "main", "displayName": "Chicago Crimes — Análise",
    "layout": widgets,
}]}

import sys
DID = sys.argv[1] if len(sys.argv) > 1 else None
body = {
    "display_name": "MVP Chicago Crimes — Dashboard",
    "warehouse_id": WAREHOUSE,
    "serialized_dashboard": json.dumps(serialized),
}
if DID:  # atualiza o existente (mesma URL)
    res = api("PATCH", f"/api/2.0/lakeview/dashboards/{DID}", body)
    did = DID
    print("atualizado:", did)
else:
    body["parent_path"] = PARENT
    res = api("POST", "/api/2.0/lakeview/dashboards", body)
    did = res["dashboard_id"]
    print("criado:", did)
pub = api("POST", f"/api/2.0/lakeview/dashboards/{did}/published",
          {"warehouse_id": WAREHOUSE, "embed_credentials": True})
print("publicado:", pub.get("display_name", "ok"))
