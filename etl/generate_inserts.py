"""
generate_inserts.py — versión estable para MySQL
"""

import os
import csv
import re
import pandas as pd
from rapidfuzz import process, fuzz

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUT_DIR = os.path.join(DATA_DIR, "normalized")

os.makedirs(OUT_DIR, exist_ok=True)

INPUT_CSV = os.path.join(DATA_DIR, "netflix_titles.csv")
OUT_NETFLIX_CSV = os.path.join(OUT_DIR, "netflix_titles_clean.csv")
OUT_GENRES_CSV = os.path.join(OUT_DIR, "genres.csv")
OUT_TITLE_GENRES_CSV = os.path.join(OUT_DIR, "title_genres.csv")
OUT_INSERTS_SQL = os.path.join(OUT_DIR, "inserts.sql")


def snake_case_cols(df):
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


def parse_duration(duration):
    if pd.isna(duration):
        return (None, None)

    s = str(duration).strip()
    parts = s.split()

    try:
        num = int(parts[0])
    except:
        m = re.search(r"(\d+)", s)
        num = int(m.group(1)) if m else None

    unit = parts[1] if len(parts) > 1 else None
    return (num, unit)


def split_genres(s):
    if pd.isna(s):
        return []
    return [g.strip() for g in str(s).split(",") if g.strip()]


def fuzzy_dedup_genres(raw_genres_list, score_cutoff=90):
    unique_raw = sorted(set(raw_genres_list))
    canonical = []
    mapping = {}

    for raw in unique_raw:
        if canonical:
            match, score, _ = process.extractOne(raw, canonical, scorer=fuzz.WRatio)
            if score >= score_cutoff:
                mapping[raw] = match
                continue

        canonical.append(raw)
        mapping[raw] = raw

    return mapping, canonical


def escape(value):
    """Escapa comillas simples para MySQL"""
    if value is None or pd.isna(value):
        return "NULL"
    value = str(value)
    return "'" + value.replace("'", "''") + "'"


def main():
    print("Leyendo:", INPUT_CSV)

    if not os.path.exists(INPUT_CSV):
        print("ERROR: No se encontró netflix_titles.csv")
        return

    df = pd.read_csv(INPUT_CSV)
    df = snake_case_cols(df)

    if "show_id" not in df.columns:
        df.insert(0, "show_id", [f"S{i:06d}" for i in range(1, len(df) + 1)])
    else:
        df["show_id"] = df["show_id"].astype(str)

    if "date_added" in df.columns:
        df["date_added"] = pd.to_datetime(df["date_added"], errors="coerce")

    if "duration" in df.columns:
        parsed = df["duration"].apply(parse_duration)
        df["duration_int"] = parsed.apply(lambda t: t[0])
        df["duration_unit"] = parsed.apply(lambda t: t[1])

    for c in ["director", "cast", "country", "rating", "listed_in", "description"]:
        if c in df.columns:
            df[c] = df[c].fillna("Unknown")

    df["__genres_list"] = df["listed_in"].apply(split_genres)
    all_raw_genres = []
    df["__genres_list"].apply(lambda L: all_raw_genres.extend(L))

    mapping, canonical_genres = fuzzy_dedup_genres(all_raw_genres)

    genres_df = (
        pd.DataFrame({"genre_name": sorted(set(mapping[g] for g in mapping))})
        .reset_index(drop=True)
    )
    genres_df.insert(0, "genre_id", range(1, len(genres_df) + 1))

    title_genres_rows = []
    for _, row in df.iterrows():
        sid = row["show_id"]
        for raw_g in row["__genres_list"]:
            canonical = mapping.get(raw_g, raw_g)
            gid = genres_df[genres_df["genre_name"] == canonical]["genre_id"].values
            if len(gid) > 0:
                title_genres_rows.append({"show_id": sid, "genre_id": int(gid[0])})

    title_genres_df = pd.DataFrame(title_genres_rows)

    netflix_clean_cols = [
        "show_id", "type", "title", "director", "cast", "country",
        "date_added", "release_year", "rating", "duration",
        "duration_int", "duration_unit", "description",
    ]

    df_out = df[netflix_clean_cols]
    df_out.to_csv(OUT_NETFLIX_CSV, index=False)
    genres_df.to_csv(OUT_GENRES_CSV, index=False)
    title_genres_df.to_csv(OUT_TITLE_GENRES_CSV, index=False)

    print("Generando inserts.sql...")

    with open(OUT_INSERTS_SQL, "w", encoding="utf-8") as f:

        # netflix_titles
        for _, r in df_out.iterrows():
            date_added = (
                f"'{r['date_added'].date()}'" if not pd.isna(r["date_added"]) else "NULL"
            )

            query = (
                "INSERT INTO netflix_titles VALUES ("
                f"{escape(r['show_id'])}, "
                f"{escape(r['type'])}, "
                f"{escape(r['title'])}, "
                f"{escape(r['director'])}, "
                f"{escape(r['cast'])}, "
                f"{escape(r['country'])}, "
                f"{date_added}, "
                f"{r['release_year'] if not pd.isna(r['release_year']) else 'NULL'}, "
                f"{escape(r['rating'])}, "
                f"{escape(r['duration'])}, "
                f"{r['duration_int'] if not pd.isna(r['duration_int']) else 'NULL'}, "
                f"{escape(r['duration_unit'])}, "
                f"{escape(r['description'])}"
                ");\n"
            )
            f.write(query)

        # genres
        for _, r in genres_df.iterrows():
            f.write(
                f"INSERT INTO genres (genre_id, genre_name) VALUES "
                f"({r['genre_id']}, {escape(r['genre_name'])});\n"
            )

        # title_genres
        for _, r in title_genres_df.iterrows():
            f.write(
                f"INSERT INTO title_genres (show_id, genre_id) VALUES "
                f"({escape(r['show_id'])}, {r['genre_id']});\n"
            )

    print("¡Listo! inserts.sql generado en:", OUT_INSERTS_SQL)


if __name__ == "__main__":
    main()
