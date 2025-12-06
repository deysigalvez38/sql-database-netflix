#!/usr/bin/env python3
# etl/fix_date_added_generate_updates.py
import pandas as pd
from pathlib import Path
import re

ROOT = Path.cwd()
CSV = ROOT / "data" / "normalized" / "netflix_titles_clean.csv"
OUT_SQL = ROOT / "data" / "normalized" / "update_date_added.sql"

def parse_date(s):
    if pd.isna(s): return None
    s = str(s).strip()
    if s == "": return None
    # Try pandas auto-parse first
    try:
        dt = pd.to_datetime(s, dayfirst=False, yearfirst=False, errors='coerce')
        if pd.notna(dt):
            return dt.date().isoformat()
    except:
        pass
    # Try manual common patterns
    patterns = ['%B %d, %Y', '%b %d, %Y', '%d %B %Y', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']
    for fmt in patterns:
        try:
            dt = pd.to_datetime(s, format=fmt, errors='raise')
            return dt.date().isoformat()
        except Exception:
            continue
    # Fallback: extract 4-digit year if present
    m = re.search(r'([0-9]{4})', s)
    if m:
        return f"{m.group(1)}-01-01"
    return None

def main():
    if not CSV.exists():
        print("CSV not found:", CSV)
        return
    df = pd.read_csv(CSV, dtype=str, keep_default_na=False)
    # detect id column
    id_col = next((c for c in df.columns if c.lower() in ('show_id','showid','id')), None)
    date_cols = [c for c in df.columns if 'date' in c.lower()]
    if id_col is None:
        print("No id column found. Columns:", df.columns.tolist())
        return
    # prefer explicit date_added-like column
    date_col = next((c for c in date_cols if 'date_added' in c.lower()), (date_cols[0] if date_cols else None))
    updates = []
    for _, row in df.iterrows():
        sid = str(row.get(id_col,'')).strip()
        if not sid:
            continue
        raw = row.get(date_col, '') if date_col else ''
        parsed = parse_date(raw)
        if parsed:
            updates.append((sid, parsed))
    # write SQL file
    with open(OUT_SQL, 'w', encoding='utf-8') as f:
        f.write("USE netflix_db;\nSTART TRANSACTION;\n")
        # set zero dates to NULL first (safe)
        f.write("UPDATE netflix_titles SET date_added = NULL WHERE date_added = '0000-00-00' OR date_added = '';\n")
        for sid, d in updates:
            f.write(f"UPDATE netflix_titles SET date_added = '{d}' WHERE show_id = {repr(sid)} AND (date_added IS NULL OR date_added = '0000-00-00');\n")
        f.write("COMMIT;\n")
    print("Generated:", OUT_SQL, "rows:", len(updates))

if __name__ == '__main__':
    main()
