#!/usr/bin/env python3
"""
etl/dedupe_inserts_actors.py

Lee data/normalized/inserts_actors.sql y genera data/normalized/inserts_actors_dedup.sql
- Mantiene la primera aparición de cada actor_name
- Emite INSERT IGNORE INTO actors (actor_name) VALUES ('...') para cada actor único
- Conserva el bloque de title_actors tal cual (no toca esas líneas)
"""

import re
from pathlib import Path

ROOT = Path.cwd()
IN_FILE = ROOT / "data" / "normalized" / "inserts_actors.sql"
OUT_FILE = ROOT / "data" / "normalized" / "inserts_actors_dedup.sql"

if not IN_FILE.exists():
    print("ERROR: no encuentro", IN_FILE)
    raise SystemExit(1)

seen = set()
out_lines = []
actor_insert_re = re.compile(r"INSERT\s+INTO\s+actors\s*\([^\)]*\)\s*VALUES\s*\((.+)\)\s*;", re.IGNORECASE)

def parse_actor_name_from_values(values_text):
    # values_text typical: 294, 'Adam Devine'
    # We want the last quoted string (actor_name). Handle escaped quotes by doubling ('')
    # Simple approach: find first ' then last ' and extract between, but handle doubled quotes.
    # We'll search for the last single-quoted literal.
    matches = re.findall(r"'((?:[^']|'')+)'", values_text)
    if not matches:
        return None
    # last match is actor_name
    name = matches[-1]
    # unescape doubled single-quotes to single
    name = name.replace("''", "'")
    return name

with IN_FILE.open("r", encoding="utf-8", errors="replace") as f:
    for line in f:
        m = actor_insert_re.search(line)
        if m:
            vals = m.group(1)
            actor_name = parse_actor_name_from_values(vals)
            if not actor_name:
                # no parse -> keep original line to be safe
                out_lines.append(line)
            else:
                if actor_name not in seen:
                    seen.add(actor_name)
                    # write normalized INSERT IGNORE with only actor_name so MySQL assigns id
                    safe = actor_name.replace("'", "''")
                    out_lines.append(f"INSERT IGNORE INTO actors (actor_name) VALUES ('{safe}');\n")
                else:
                    # skip duplicate actor insert
                    pass
        else:
            out_lines.append(line)

OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
with OUT_FILE.open("w", encoding="utf-8") as f:
    f.writelines(out_lines)

print(f"Hecho. Actores únicos escritos: {len(seen)}")
print("Archivo generado:", OUT_FILE)
