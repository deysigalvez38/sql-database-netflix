#!/usr/bin/env python3
# etl/generate_inserts_from_raws.py
import sys
from pathlib import Path
import pandas as pd
from unidecode import unidecode
from collections import defaultdict, Counter

ROOT = Path.cwd()
DATA_DIR = ROOT / "data" / "normalized"
OUT_SQL = DATA_DIR / "inserts_all.sql"

def read_csv_optional(path):
    if not path.exists():
        return None
    encs = ["utf-8","latin-1","cp1252"]
    for enc in encs:
        try:
            df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding=enc)
            print(f"Read {path.name} using {enc}, rows={len(df)}")
            return df
        except Exception as e:
            pass
    raise RuntimeError(f"Cannot read {path}")

def sql_escape(s):
    if s is None or s == "":
        return "NULL"
    s = str(s).replace("\r"," ").replace("\n"," ").strip()
    s = s.replace("'", "''")
    return f"'{s}'"

def normalize_key(s):
    if not s:
        return ""
    s = str(s).strip()
    s = unidecode(s).lower()
    s = " ".join(s.split())
    import re
    s = re.sub(r"[^a-z0-9 ]+", "", s)
    return s

# load CSVs
df_titles = read_csv_optional(DATA_DIR / "netflix_titles_clean.csv")
df_tg = read_csv_optional(DATA_DIR / "title_genres.csv")
df_ta_raw = read_csv_optional(DATA_DIR / "title_actors_raw.csv")

lines = []
lines.append("-- inserts_all.sql (generated)")
lines.append("SET NAMES utf8mb4;")
lines.append("SET FOREIGN_KEY_CHECKS = 0;")
lines.append("START TRANSACTION;")
lines.append("")

# netflix_titles if available
if df_titles is not None:
    lines.append("-- netflix_titles")
    for _, r in df_titles.iterrows():
        sid = str(r.get("show_id") or r.get("showId") or r.get("id") or "").strip()
        if not sid:
            continue
        def gv(*cands):
            for c in cands:
                if c in r and str(r[c]).strip():
                    return r[c]
            return ""
        type_ = gv("type")
        title = gv("title","name")
        director = gv("director")
        # cast detection
        cast = ""
        for c in r.index:
            if "cast" in str(c).lower() or "actor" in str(c).lower():
                cast = r.get(c,"") or ""
                break
        country = gv("country")
        date_added = gv("date_added","dateAdded","date_added_date")
        if date_added:
            try:
                d = pd.to_datetime(date_added, errors="coerce")
                if not pd.isna(d):
                    date_added = d.date().isoformat()
            except Exception:
                pass
        release_year = gv("release_year","releaseYear")
        rating = gv("rating")
        duration_raw = gv("duration_raw","duration")
        duration_int = ""
        duration_unit = ""
        if duration_raw:
            import re
            m = re.search(r"(\d+)", str(duration_raw))
            if m:
                duration_int = m.group(1)
            if "season" in str(duration_raw).lower():
                duration_unit = "Seasons"
            elif "min" in str(duration_raw).lower():
                duration_unit = "min"
        description = gv("description","synopsis","summary")
        vals = ",".join([
            sql_escape(sid), sql_escape(type_), sql_escape(title), sql_escape(director),
            sql_escape(cast), sql_escape(country), sql_escape(date_added if date_added else None),
            sql_escape(release_year), sql_escape(rating), sql_escape(duration_raw),
            sql_escape(duration_int), sql_escape(duration_unit), sql_escape(description)
        ])
        lines.append(f"INSERT IGNORE INTO netflix_titles (show_id,type,title,director,cast,country,date_added,release_year,rating,duration_raw,duration_int,duration_unit,description) VALUES ({vals});")
    lines.append("")

# genres
genre_set = set()
genre_pairs = []
if df_tg is not None:
    for _, r in df_tg.iterrows():
        sid = str(r.get("show_id") or r.get("showId") or "").strip()
        g = str(r.get("genre_name") or r.get("genre") or r.get("listed_in") or "").strip()
        if sid and g:
            for part in [p.strip() for p in g.split(",") if p.strip()]:
                genre_set.add(part)
                genre_pairs.append((sid, part))
elif df_titles is not None:
    # search for genre-like column
    cand = None
    for c in df_titles.columns:
        if "listed" in c.lower() or "genre" in c.lower():
            cand = c
            break
    if cand:
        for _, r in df_titles.iterrows():
            sid = str(r.get("show_id") or r.get("showId") or "").strip()
            gtext = str(r.get(cand,"") or "").strip()
            if sid and gtext:
                for part in [p.strip() for p in gtext.split(",") if p.strip()]:
                    genre_set.add(part)
                    genre_pairs.append((sid, part))

if genre_set:
    lines.append("-- genres")
    for g in sorted(genre_set):
        lines.append(f"INSERT IGNORE INTO genres (genre_name) VALUES ({sql_escape(g)});")
    lines.append("")
    lines.append("-- title_genres mapping")
    for sid, g in genre_pairs:
        lines.append(f"INSERT IGNORE INTO title_genres (show_id, genre_id) SELECT {sql_escape(sid)}, genre_id FROM genres WHERE genre_name = {sql_escape(g)};")
    lines.append("")

# actors and title_actors
pairs = []
if df_ta_raw is not None:
    for _, r in df_ta_raw.iterrows():
        sid = str(r.get("show_id") or r.get("showId") or r.get("showid") or "").strip()
        actor = str(r.get("actor_name") or r.get("actor") or r.get("name") or "").strip()
        if sid and actor:
            pairs.append((sid, actor))
elif df_titles is not None:
    # find cast column
    cast_col = None
    for c in df_titles.columns:
        if "cast" in c.lower() or "actor" in c.lower() or "starring" in c.lower():
            cast_col = c
            break
    if cast_col:
        for _, r in df_titles.iterrows():
            sid = str(r.get("show_id") or r.get("showId") or "").strip()
            raw = str(r.get(cast_col,"") or "").strip()
            if sid and raw:
                for p in [p.strip() for p in raw.split(",") if p.strip()]:
                    pairs.append((sid, p))

if pairs:
    # canonical grouping to dedup semantically similar names
    groups = defaultdict(list)
    for sid, actor in pairs:
        groups[normalize_key(actor)].append(actor)
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
    lines.append("-- actors (deduped canonical)")
    for a in unique_canons:
        lines.append(f"INSERT IGNORE INTO actors (actor_name) VALUES ({sql_escape(a)});")
    lines.append("")
    lines.append("-- title_actors mapping")
    seen = set()
    for sid, actor in pairs:
        canon = orig_to_canon.get(actor, actor)
        key = (sid, canon)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"INSERT IGNORE INTO title_actors (show_id, actor_id) SELECT {sql_escape(sid)}, actor_id FROM actors WHERE actor_name = {sql_escape(canon)};")
    lines.append("")

lines.append("COMMIT;")
lines.append("SET FOREIGN_KEY_CHECKS = 1;")
lines.append("")

OUT_SQL.parent.mkdir(parents=True, exist_ok=True)
with open(OUT_SQL, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("Wrote:", OUT_SQL, "size(bytes)=", OUT_SQL.stat().st_size)
print("Next: mysql -u your_user -p netflix_db <", OUT_SQL)
