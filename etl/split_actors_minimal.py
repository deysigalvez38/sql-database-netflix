#!/usr/bin/env python3
# etl/split_actors_minimal.py (versión corregida, no usa errors=)
import os, pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "data" / "normalized" / "netflix_titles_clean.csv"
OUT_ACT = ROOT / "data" / "normalized" / "actors.csv"
OUT_RAW = ROOT / "data" / "normalized" / "title_actors_raw.csv"

print("Leyendo:", IN)

def try_read(path):
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False, encoding='utf-8')
    except Exception as e:
        print("Lectura con utf-8 falló:", e)
        print("Intentando con latin-1...")
        return pd.read_csv(path, dtype=str, keep_default_na=False, encoding='latin-1')

df = try_read(IN)
cols = {c.lower().strip(): c for c in df.columns}
print("Columnas detectadas (lowercased):", list(cols.keys()))

# detectar columna de reparto
cast_col = None
for candidate in ("cast","cast_","casts","actors"):
    if candidate in cols:
        cast_col = cols[candidate]
        break
if cast_col is None:
    for c in df.columns:
        if "cast" in c.lower():
            cast_col = c
            break
if cast_col is None:
    print("ERROR: no se encontró columna 'cast' en el CSV. Columnas:", list(df.columns))
    raise SystemExit(1)

print("Usando columna de reparto:", cast_col)
rows = []
set_actors = set()
for _, r in df.iterrows():
    show_id = str(r.get('show_id') or "").strip()
    raw = str(r.get(cast_col) or "").strip()
    if not show_id or not raw or raw.lower() in ("unknown","nan","n/a"):
        continue
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    for p in parts:
        set_actors.add(p)
        rows.append({"show_id": show_id, "actor_name": p})

pd.DataFrame(sorted(set_actors), columns=["actor_name"]).to_csv(OUT_ACT, index=False)
pd.DataFrame(rows, columns=["show_id","actor_name"]).to_csv(OUT_RAW, index=False)
print("Generados:", OUT_ACT, OUT_RAW)
print("Actores únicos:", len(set_actors), "Relaciones:", len(rows))
