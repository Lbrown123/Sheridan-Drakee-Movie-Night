"""
import_ratings.py — merge OG Ratings CSVs into movies.js

Usage (from project root):
    python scripts/import_ratings.py
"""

import csv
import datetime
import json
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
MOVIES_JS = PROJECT_ROOT / "movies.js"
CSV_DIR = PROJECT_ROOT / "OG Ratings"

CSV_FILES = [
    ("Movie Night Ratings 2023.csv", 2023),
    ("Movie Night Ratings 2024.csv", 2024),
    ("Movie Night Ratings 2025.csv", 2025),
    ("Movie Night Ratings 2026.csv", 2026),
]


def parse_date(raw: str, year_hint: int) -> Optional[str]:
    raw = raw.strip()
    if not raw:
        return None
    parts = raw.split("/")
    try:
        if len(parts) == 3:
            month, day, year_short = parts
            year = 2000 + int(year_short)
        elif len(parts) == 2:
            month, day = parts
            year = year_hint
        else:
            return None
        return datetime.date(year, int(month), int(day)).isoformat()
    except (ValueError, OverflowError):
        return None


def parse_rating(raw: str) -> Optional[float]:
    try:
        return float(raw.strip())
    except ValueError:
        return None


def detect_columns(header: list[str]) -> dict:
    normalized = [h.strip().lower() for h in header]
    cols = {}
    cols["title"] = normalized.index("movie")
    cols["abby"] = next(i for i, h in enumerate(normalized) if "abby" in h and "rating" in h)
    cols["elizabeth"] = next(i for i, h in enumerate(normalized) if "elizabeth" in h and "rating" in h)
    cols["logan"] = next(i for i, h in enumerate(normalized) if "logan" in h and "rating" in h)
    cols["date"] = next((i for i, h in enumerate(normalized) if h == "date watched"), None)
    return cols


def parse_csv(filename: str, year_hint: int) -> list[dict]:
    path = CSV_DIR / filename
    movies = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        cols = detect_columns(header)

        for row in reader:
            if len(row) <= cols["title"]:
                continue

            title = row[cols["title"]].strip()
            if not title:
                continue

            abby = parse_rating(row[cols["abby"]]) if len(row) > cols["abby"] else None
            elizabeth = parse_rating(row[cols["elizabeth"]]) if len(row) > cols["elizabeth"] else None
            logan = parse_rating(row[cols["logan"]]) if len(row) > cols["logan"] else None

            if abby is None and elizabeth is None and logan is None:
                continue

            ratings = {}
            if abby is not None:
                ratings["abby"] = abby
            if elizabeth is not None:
                ratings["elizabeth"] = elizabeth
            if logan is not None:
                ratings["logan"] = logan

            movie: dict = {"title": title, "ratings": ratings}

            if cols["date"] is not None and len(row) > cols["date"]:
                date_str = parse_date(row[cols["date"]], year_hint)
                if date_str:
                    movie["dateWatched"] = date_str

            movies.append(movie)

    return movies


def merge(existing: list[dict], csv_movies: list[dict]) -> list[dict]:
    existing_keys = {m["title"].lower().strip() for m in existing}
    seen = set(existing_keys)
    new_entries = []

    for movie in csv_movies:
        key = movie["title"].lower().strip()
        if key in seen:
            continue
        seen.add(key)
        new_entries.append(movie)

    return existing + new_entries


def sort_movies(movies: list[dict]) -> list[dict]:
    def sort_key(m):
        date = m.get("dateWatched")
        return (1, date) if date else (0, "")

    return sorted(movies, key=sort_key, reverse=True)


def main():
    content = MOVIES_JS.read_text(encoding="utf-8")
    json_str = content.removeprefix("const MOVIES_DATA = ").rstrip().rstrip(";")
    data = json.loads(json_str)

    existing = data.get("movies", [])
    up_next = data.get("upNext")

    all_csv_movies: list[dict] = []
    for filename, year_hint in CSV_FILES:
        movies = parse_csv(filename, year_hint)
        all_csv_movies.extend(movies)
        print(f"  Parsed {len(movies):3d} movies from {filename}")

    merged = merge(existing, all_csv_movies)
    added = len(merged) - len(existing)
    print(f"\nAdded {added} new movies. Total: {len(merged)}")

    sorted_movies = sort_movies(merged)

    output = {"upNext": up_next, "movies": sorted_movies}
    out_json = json.dumps(output, indent=2, ensure_ascii=False)
    with open(MOVIES_JS, "w", encoding="utf-8") as f:
        f.write("const MOVIES_DATA = ")
        f.write(out_json)
        f.write(";\n")

    print(f"Wrote {MOVIES_JS}")


if __name__ == "__main__":
    main()
