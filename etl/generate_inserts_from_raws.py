#!/usr/bin/env python3
# generate_inserts_from_raws.py
"""
ETL: lee CSVs normalizados y genera inserts_all.sql listo para importar en MySQL.
Rutas por defecto:
 - data/normalized/netflix_titles_clean.csv
 - data/normalized/title_genres.csv   (opcional)
 - data/normalized/title_actors_raw.csv (opcional)

Salida:
 - data/normalized/inserts_all.sql
"""

import sys
from pathlib import Path
import pandas as pd
from collections import defaultdict, Counter
import re
from unidecode import unidecode

ROOT = Path.cwd()
DATA_DIR = ROOT / "data" / "normalized"
OUT_SQL = DATA_DIR / "inserts_all.sql"

# CSV default paths (puedes modificarlos si tienes otros nombres)
CSV_TITLES = DATA_DIR / "netflix_titles_clean.csv"
CSV_TG = DATA_DIR / "title_genres.csv"
CSV_TA = DATA_DIR / "title_actors_raw.csv"

def read_csv_optional(path):
    if not path.exists():
        return None
    encs = ["utf-8", "latin-1", "cp1252"]
    for enc in encs:
        try:
            df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding=enc)
            print(f"Leído {path} con encoding {enc} (filas={len(df)})")
            return df
        except Exception as e:
            # try next
            pass
    raise RuntimeError(f"No se pudo leer {path}")

def sql_escape(val):
    if val is None:
        return "NULL"
    s = str(val).strip()
    if s == "":
        return "NULL"
    s = s.replace("\r", " ").replace("\n", " ")
    s = s.replace("'", "''")
    return f"'{s}'"

def normalize_key(s):
    if not s:
        return ""
    s = unidecode(str(s)).lower()
    s = " ".join(s.split())
    s = re.sub(r"[^a-z0-9 ]+", "", s)
    return s

def detect_date(s):
    if not s or str(s).strip() == "":
        return None
    try:
        d = pd.to_datetime(s, errors="coerce")
        if pd.isna(d):
            return None
        return d.date().isoformat()
    except Exception:
        return None

# Load CSVs
df_titles = read_csv_optional(CSV_TITLES)
df_tg = read_csv_optional(CSV_TG)
df_ta_raw = read_csv_optional(CSV_TA)

lines = []
lines.append("-- inserts_all.sql generado por generate_inserts_from_raws.py")
lines.append("SET NAMES utf8mb4;")
lines.append("SET FOREIGN_KEY_CHECKS = 0;")
lines.append("START TRANSACTION;")
lines.append("")

def col(name):
    return f"`{name}`"

# 1) netflix_titles
if df_titles is not None:
    lines.append("-- netflix_titles")
    # try to find show_id column name
    for idx, r in df_titles.iterrows():
        # flexible retrieval for show id
        sid = None
        for cand in ("show_id", "showId", "showid", "id"):
            if cand in df_titles.columns:
                sid = str(r.get(cand, "")).strip()
                if sid:
                    break
        if not sid:
            # skip rows without id
            continue

        def gv(*cands):
            for c in cands:
                if c in df_titles.columns and str(r.get(c, "")).strip():
                    return r.get(c, "")
            return ""

        type_ = gv("type", "Type")
        title = gv("title", "name")
        director = gv("director", "Director")
        # detect cast column or use cast_list if already normalized
        cast_list = ""
        for c in df_titles.columns:
            if c.lower() in ("cast_list", "cast", "actors", "starring") or "cast" in c.lower() or "actor" in c.lower():
                cast_list = r.get(c, "") or ""
                if cast_list:
                    break
        country = gv("country", "Country")
        date_added = detect_date(gv("date_added", "dateAdded", "date_added_date"))
        release_year = gv("release_year", "releaseYear")
        rating = gv("rating")
        duration_raw = gv("duration_raw", "duration")
        duration_int = None
        duration_unit = ""
        if duration_raw:
            m = re.search(r"(\d+)", str(duration_raw))
            if m:
                try:
                    duration_int = int(m.group(1))
                except:
                    duration_int = None
            if "season" in str(duration_raw).lower():
                duration_unit = "Seasons"
            elif "min" in str(duration_raw).lower():
                duration_unit = "min"

        description = gv("description", "synopsis", "summary")

        vals = ",".join([
            sql_escape(sid),
            sql_escape(type_),
            sql_escape(title),
            sql_escape(director),
            sql_escape(cast_list),
            sql_escape(country),
            (f"'{date_added}'" if date_added else "NULL"),
            (str(int(release_year)) if str(release_year).isdigit() else (sql_escape(release_year) if release_year else "NULL")),
            sql_escape(rating),
            sql_escape(duration_raw),
            (str(duration_int) if duration_int is not None else "NULL"),
            sql_escape(duration_unit),
            sql_escape(description)
        ])
        cols = ",".join([col(c) for c in ["show_id","type","title","director","cast_list","country","date_added","release_year","rating","duration_raw","duration_int","duration_unit","description"]])
        lines.append(f"INSERT IGNORE INTO netflix_titles ({cols}) VALUES ({vals});")
    lines.append("")

# 2) genres + title_genres
genre_set = set()
genre_pairs = []  # (show_id, genre_name)

if df_tg is not None:
    # expected columns: show_id, genre_name (or genre)
    for idx, r in df_tg.iterrows():
        sid = ""
        for cand in ("show_id","showId","showid","id"):
            if cand in df_tg.columns:
                sid = str(r.get(cand,"")).strip()
                if sid:
                    break
        g = ""
        for cand in ("genre_name","genre","listed_in","genres"):
            if cand in df_tg.columns:
                g = str(r.get(cand,"")).strip()
                if g:
                    break
        if sid and g:
            # may be comma separated
            for part in [p.strip() for p in g.split(",") if p.strip()]:
                genre_set.add(part)
                genre_pairs.append((sid, part))
elif df_titles is not None:
    # try to get listed_in from titles CSV
    cand = None
    for c in df_titles.columns:
        if "listed" in c.lower() or "genre" in c.lower():
            cand = c
            break
    if cand:
        for idx, r in df_titles.iterrows():
            sid = ""
            for sc in ("show_id","showId","showid","id"):
                if sc in df_titles.columns:
                    sid = str(r.get(sc,"")).strip()
                    if sid:
                        break
            gtext = str(r.get(cand,"") or "").strip()
            if sid and gtext:
                for part in [p.strip() for p in gtext.split(",") if p.strip()]:
                    genre_set.add(part)
                    genre_pairs.append((sid, part))

if genre_set:
    lines.append("-- genres")
    for g in sorted(genre_set):
        lines.append(f"INSERT IGNORE INTO genres (`genre_name`) VALUES ({sql_escape(g)});")
    lines.append("")
    lines.append("-- title_genres mapping")
    for sid, g in genre_pairs:
        # use SELECT ... FROM genres to get genre_id
        lines.append(f"INSERT IGNORE INTO title_genres (`show_id`, `genre_id`) SELECT {sql_escape(sid)}, `genre_id` FROM genres WHERE `genre_name` = {sql_escape(g)};")
    lines.append("")

# 3) actors + title_actors
pairs = []  # (show_id, actor_name)

if df_ta_raw is not None:
    for idx, r in df_ta_raw.iterrows():
        sid = ""
        for cand in ("show_id","showId","showid","id"):
            if cand in df_ta_raw.columns:
                sid = str(r.get(cand,"")).strip()
                if sid:
                    break
        actor = ""
        for cand in ("actor_name","actor","name","actors","actorName"):
            if cand in df_ta_raw.columns:
                actor = str(r.get(cand,"")).strip()
                if actor:
                    break
        if sid and actor:
            # actor may be single per row; if comma-separated, split
            for p in [x.strip() for x in re.split(r",|;|\|", actor) if x.strip()]:
                pairs.append((sid, p))
elif df_titles is not None:
    # try detect cast column
    cast_col = None
    for c in df_titles.columns:
        if "cast" in c.lower() or "actor" in c.lower() or "starring" in c.lower():
            cast_col = c
            break
    if cast_col:
        for idx, r in df_titles.iterrows():
            sid = ""
            for sc in ("show_id","showId","showid","id"):
                if sc in df_titles.columns:
                    sid = str(r.get(sc,"")).strip()
                    if sid:
                        break
            raw = str(r.get(cast_col,"") or "").strip()
            if sid and raw:
                for p in [x.strip() for x in re.split(r",|;|\|", raw) if x.strip()]:
                    pairs.append((sid, p))

if pairs:
    # dedupe actors by normalized key and pick canonical form
    groups = defaultdict(list)
    for sid, actor in pairs:
        k = normalize_key(actor)
        groups[k].append(actor)
    canonical = {}
    for k, names in groups.items():
        cnt = Counter(names)
        best = sorted(cnt.items(), key=lambda x: (-x[1], len(x[0]), x[0]))[0][0]
        canonical[k] = best
    orig_to_canon = {}
    for k, names in groups.items():
        for n in set(names):
            orig_to_canon[n] = canonical[k]
    unique_canons = sorted(set(canonical.values()))
    lines.append("-- actors (deduplicados)")
    for a in unique_canons:
        lines.append(f"INSERT IGNORE INTO actors (`actor_name`) VALUES ({sql_escape(a)});")
    lines.append("")
    lines.append("-- title_actors mapping")
    seen = set()
    for sid, actor in pairs:
        canon = orig_to_canon.get(actor, actor)
        key = (sid, canon)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"INSERT IGNORE INTO title_actors (`show_id`, `actor_id`) SELECT {sql_escape(sid)}, `actor_id` FROM actors WHERE `actor_name` = {sql_escape(canon)};")
    lines.append("")

lines.append("COMMIT;")
lines.append("SET FOREIGN_KEY_CHECKS = 1;")
lines.append("")

# Ensure output directory exists
OUT_SQL.parent.mkdir(parents=True, exist_ok=True)
with open(OUT_SQL, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("Generado:", OUT_SQL)
print("Ejecuta: mysql -u <user> -p netflix_db < data/normalized/inserts_all.sql")
