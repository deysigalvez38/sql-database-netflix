#!/usr/bin/env python3
"""
etl/split_actors.py (versión con logging)

Lee data/normalized/netflix_titles_clean.csv, separa el campo 'cast' (coma-separado)
y genera:
  - data/normalized/actors.csv
  - data/normalized/title_actors_raw.csv

Imprime trazas para depuración si algo falla.
"""
import os
import sys
import pandas as pd

from pathlib import Path

# RUTAS (ajusta si tu repo está en otra ruta)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "normalized"
IN_CSV = DATA_DIR / "netflix_titles_clean.csv"
OUT_ACTORS = DATA_DIR / "actors.csv"
OUT_TITLE_ACTORS_RAW = DATA_DIR / "title_actors_raw.csv"

def normalize_name(name: str) -> str:
    return " ".join(str(name).strip().split())

def safe_read_csv(path: Path):
    # intento con utf-8, si falla pruebo latin-1
    try:
        print(f"Intentando leer CSV con UTF-8: {path}")
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    except Exception as e:
        print(f"Error leyendo con UTF-8: {e}")
        print("Intentando leer con latin-1...")
        return pd.read_csv(path, dtype=str, encoding="latin-1", keep_default_na=False)

def main():
    print("Proyecto root:", PROJECT_ROOT)
    print("Buscando archivo:", IN_CSV)

    if not IN_CSV.exists():
        print("ERROR: archivo no encontrado:", IN_CSV)
        print("Listado data/normalized:")
        for p in sorted((PROJECT_ROOT / "data").glob("**/*")):
            print(" -", p)
        sys.exit(2)

    # crear carpeta output por si no existe
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    df = safe_read_csv(IN_CSV)
    print("CSV leído. Filas:", len(df))
    print("Columnas:", list(df.columns[:20]))

    # normalizar nombres de columnas frecuentes
    cols_lower = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df.columns = cols_lower
    print("Columnas normalizadas:", cols_lower)

    if "show_id" not in df.columns:
        print("WARN: 'show_id' no está en el CSV. Generando IDs automáticos.")
        df.insert(0, "show_id", [f"S{i:06d}" for i in range(1, len(df) + 1)])

    if "cast" not in df.columns:
        print("ERROR: columna 'cast' no encontrada. Columnas disponibles:")
        print(df.columns.tolist())
        sys.exit(3)

    rows = []
    actors_set = set()
    n_missing = 0
    n_total_split = 0

    for idx, row in df.iterrows():
        show_id = str(row.get("show_id", "")).strip()
        raw_cast = str(row.get("cast", "")).strip()
        if not show_id:
            continue
        if raw_cast == "" or raw_cast.lower() in ("unknown", "n/a", "nan"):
            n_missing += 1
            continue
        # separar por coma
        parts = [p.strip() for p in raw_cast.split(",") if p.strip()]
        if not parts:
            n_missing += 1
            continue
        for p in parts:
            name = normalize_name(p)
            if name:
                actors_set.add(name)
                rows.append({"show_id": show_id, "actor_name": name})
                n_total_split += 1

    print("Actores únicos detectados:", len(actors_set))
    print("Relaciones show-actor detectadas:", len(rows))
    print("Filas con cast vacío o desconocido:", n_missing)
    print("Filas totales en input:", len(df))

    # Exportar
    df_actors = pd.DataFrame(sorted(actors_set), columns=["actor_name"])
    df_title_actors_raw = pd.DataFrame(rows, columns=["show_id", "actor_name"])

    try:
        df_actors.to_csv(OUT_ACTORS, index=False, encoding="utf-8")
        df_title_actors_raw.to_csv(OUT_TITLE_ACTORS_RAW, index=False, encoding="utf-8")
    except Exception as e:
        print("ERROR al escribir CSVs:", e)
        sys.exit(4)

    print("Archivos escritos:")
    print(" -", OUT_ACTORS, " (rows:", len(df_actors), ")")
    print(" -", OUT_TITLE_ACTORS_RAW, " (rows:", len(df_title_actors_raw), ")")
    print("Hecho.")

if __name__ == "__main__":
    main()
