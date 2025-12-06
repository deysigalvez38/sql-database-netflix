#!/usr/bin/env python3
"""
etl/generate_update_data_sql.py

Lee data/normalized/netflix_titles_clean.csv (o data/netflix_titles.csv)
y genera data/normalized/update_data.sql con UPDATEs seguros que:
 - normalizan date_added (varios formatos),
 - convierten '0000-00-00' a NULL,
 - rellenan duration_int y duration_unit desde duration_raw,
 - opcionalmente escriben cast_list.

Cada UPDATE incluye WHERE show_id = '...' (clave primaria) para evitar Safe Update Mode errors.
También genera CSVs de debug: debug_parsed_dates.csv y debug_parsed_duration.csv
"""

from pathlib import Path
import pandas as pd
import re
from datetime import datetime
import html
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
NORMAL = DATA / "normalized"
NORMAL.mkdir(parents=True, exist_ok=True)

CSV_TITLES_PRIMARY = NORMAL / "netflix_titles_clean.csv"
CSV_TITLES_FALLBACK = DATA / "netflix_titles.csv"

OUT_SQL = NORMAL / "update_data.sql"
DEBUG_DATES = NORMAL / "debug_parsed_dates.csv"
DEBUG_DUR = NORMAL / "debug_parsed_duration.csv"

# Encodings a probar
ENCODINGS = ["utf-8", "latin-1", "cp1252"]

def read_csv_try(path):
    if not path.exists():
        return None, f"missing {path.name}"
    last = None
    for enc in ENCODINGS:
        try:
            df = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[''])
            return df, f"ok ({enc}, rows={len(df)})"
        except Exception as e:
            last = e
    return None, f"error reading {path}: {last}"

def sql_quote(s):
    if s is None:
        return "NULL"
    s = str(s)
    s = s.replace("'", "''")
    return f"'{s}'"

def try_parse_date(s):
    """Intenta parsear muchos formatos; devuelve ISO date 'YYYY-MM-DD' o None.
       Si sólo encuentra un año devuelve 'YYYY-01-01' como aproximación."""
    if s is None:
        return None
    s = str(s).strip()
    if s == "" or s.lower() in ("nan", "none"):
        return None
    # evita valores numéricos sin sentido
    if s in ("0000-00-00", "0", "0000"):
        return None
    # Try pandas flexible parser first
    try:
        dt = pd.to_datetime(s, dayfirst=False, yearfirst=False, errors="coerce")
        if pd.notna(dt):
            # return isoformat date
            return dt.date().isoformat()
    except Exception:
        pass
    # Try many common formats explicitly
    fmts = [
        "%B %d, %Y",    # September 9, 2019
        "%b %d, %Y",    # Sep 9, 2019
        "%d %B %Y",     # 9 September 2019
        "%d %b %Y",     # 9 Sep 2019
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y.%m.%d",
        "%d.%m.%Y"
    ]
    for fmt in fmts:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.date().isoformat()
        except Exception:
            continue
    # fallback: buscar 4 dígitos de año
    m = re.search(r"([1-2][0-9]{3})", s)
    if m:
        year = m.group(1)
        return f"{year}-01-01"
    return None

def parse_duration(raw):
    """Extrae número y unidad desde duration_raw.
       Devuelve (duration_int or None, duration_unit or None)"""
    if raw is None:
        return None, None
    s = str(raw).strip()
    if s == "":
        return None, None
    # buscar primer número (puede haber más)
    m = re.search(r"(\d+)", s)
    if not m:
        return None, None
    num = int(m.group(1))
    lower = s.lower()
    if "season" in lower:
        unit = "Seasons"
    elif "min" in lower or "minute" in lower:
        unit = "min"
    else:
        # fallback: si contiene palabra 'ep' o 'episode'
        if "ep" in lower or "episode" in lower:
            unit = "episodes"
        else:
            unit = None
    return num, unit

def detect_show_id_col(df):
    if df is None:
        return None
    # prefer exact
    for c in df.columns:
        if c.lower() in ("show_id","showid","id"):
            return c
    # fuzzy
    for c in df.columns:
        if "show" in c.lower() and "id" in c.lower():
            return c
    return None

def main():
    # cargar CSV (preferido primary)
    df, info = read_csv_try(CSV_TITLES_PRIMARY)
    if df is None:
        df, info_fb = read_csv_try(CSV_TITLES_FALLBACK)
        if df is None:
            print("No se encontró CSV de títulos. Buscados:", CSV_TITLES_PRIMARY, "y", CSV_TITLES_FALLBACK)
            sys.exit(1)
        else:
            print("Usando fallback:", info_fb)
    else:
        print("Leído:", info)

    sid_col = detect_show_id_col(df)
    if sid_col is None:
        print("No se detectó columna show_id en CSV. Cabeceras:", df.columns.tolist())
        sys.exit(1)

    # detect date column candidates
    date_cols = [c for c in df.columns if "date" in c.lower()]
    date_col = None
    for c in date_cols:
        if "date_added" in c.lower() or "dateadded" in c.lower() or "date_added_date" in c.lower():
            date_col = c; break
    if date_col is None and date_cols:
        date_col = date_cols[0]  # fallback
    if date_col is None:
        print("Warning: no se detectó columna de fecha en CSV; se intentará usar columnas posibles:", date_cols)

    # duration column detection
    dur_col = None
    for c in df.columns:
        if "duration" in c.lower():
            dur_col = c; break

    # cast column detection
    cast_col = None
    for c in df.columns:
        if c.lower() in ("cast_list","cast","actors","starring") or "cast" in c.lower() or "actor" in c.lower():
            cast_col = c; break

    updates = []
    debug_dates = []
    debug_dur = []

    for idx, row in df.iterrows():
        sid = str(row.get(sid_col,"")).strip()
        if not sid:
            continue
        # parse date
        raw_date = row.get(date_col,"") if date_col else ""
        parsed_date = try_parse_date(raw_date)
        # parse duration
        raw_dur = row.get(dur_col,"") if dur_col else ""
        dur_int, dur_unit = parse_duration(raw_dur)
        # cast
        cast_val = row.get(cast_col,"") if cast_col else ""

        # prepare update clauses per row - apply only when we have something useful
        set_clauses = []
        # date: if parsed_date is not None -> update only if existing value is NULL or '0000-00-00' or different
        if parsed_date:
            set_clauses.append(f"date_added = {sql_literal_date(parsed_date)}")
            debug_dates.append({"show_id": sid, "raw_date": raw_date, "parsed_date": parsed_date})
        # duration
        if dur_int is not None:
            set_clauses.append(f"duration_int = {dur_int}")
            debug_dur.append({"show_id": sid, "raw_duration": raw_dur, "duration_int": dur_int, "duration_unit": dur_unit})
            if dur_unit:
                set_clauses.append(f"duration_unit = {sql_quote(dur_unit)}")
        # cast_list (optional): write only if CSV has a cast and not empty
        if cast_val and cast_val.strip():
            # write to cast_list column (safer)
            set_clauses.append(f"cast_list = {sql_quote(cast_val.strip())}")

        if set_clauses:
            # build WHERE to be safe: update only if date_added is NULL or '0000-00-00' or different (for date)
            where_parts = [f"show_id = {sql_quote(sid)}"]
            # We'll just use pk show_id, that's enough for Safe Mode.
            updates.append({"show_id": sid, "set": set_clauses, "where": where_parts})

    if not updates:
        print("No updates generados (no se parseó nada útil). Revisa CSV.")
        sys.exit(0)

    # write SQL
    with open(OUT_SQL, "w", encoding="utf-8") as f:
        f.write("-- update_data.sql (generated by etl/generate_update_data_sql.py)\n")
        f.write("USE netflix_db;\n")
        f.write("START TRANSACTION;\n")
        # set zero dates to NULL safely using WHERE show_id IS NOT NULL to satisfy Safe Mode
        f.write("-- Convertir valores '0000-00-00' a NULL (si existen)\n")
        f.write("UPDATE netflix_titles SET date_added = NULL WHERE date_added = '0000-00-00' AND show_id IS NOT NULL;\n")
        f.write("\n")
        for u in updates:
            set_sql = ", ".join(u["set"])
            where_sql = " AND ".join(u["where"])
            # Add additional guard: update only if date_added IS NULL or = '0000-00-00' or differs (but simpler: allow update if show_id matches)
            # To be conservative (avoid overwriting good dates), we'll check date_added IS NULL OR date_added = '0000-00-00' when updating date_added specifically.
            f.write(f"UPDATE netflix_titles SET {set_sql} WHERE {where_sql} AND (date_added IS NULL OR date_added = '0000-00-00' OR date_added <> {sql_quote(parsed_date) if parsed_date else 'date_added'});\n")
        f.write("COMMIT;\n")

    # write debug csvs
    if debug_dates:
        pd.DataFrame(debug_dates).to_csv(DEBUG_DATES, index=False, encoding="utf-8")
    if debug_dur:
        pd.DataFrame(debug_dur).to_csv(DEBUG_DUR, index=False, encoding="utf-8")

    print(f"Generados {len(updates)} UPDATEs en: {OUT_SQL}")
    print("CSV debug escritos:", DEBUG_DATES if debug_dates else "none", DEBUG_DUR if debug_dur else "none")
    print("Revisa el SQL antes de aplicarlo. Luego:")
    print(f"mysql -u root -p netflix_db < {OUT_SQL}")

# helper to quote dates in SQL (already validated as YYYY-MM-DD)
def sql_literal_date(iso_date):
    if not iso_date:
        return "NULL"
    # simple validation
    if not re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$", iso_date):
        return "NULL"
    return f"'{iso_date}'"

if __name__ == "__main__":
    main()
