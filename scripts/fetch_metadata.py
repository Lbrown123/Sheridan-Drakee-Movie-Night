"""
fetch_metadata.py — fetch descriptions and genres from TMDB and update movies.js

Usage (from project root):
    TMDB_API_KEY=your_key python scripts/fetch_metadata.py           # fetch all missing metadata
    TMDB_API_KEY=your_key python scripts/fetch_metadata.py "Title"   # fetch specific movie(s)
    TMDB_API_KEY=your_key python scripts/fetch_metadata.py --all     # re-fetch everything
    TMDB_API_KEY=your_key python scripts/fetch_metadata.py --dry-run # preview without modifying

Get a free TMDB API key at https://www.themoviedb.org/settings/api

Genre crosswalk — TMDB genre_id → site category:
    Action (28), Adventure (12), War (10752), Western (37) → action/adventure
    Drama (18), History (36), Music (10402)                → drama
    Sci-Fi (878), Fantasy (14)                             → scifi/fantasy
    Thriller (53), Crime (80), Mystery (9648)              → thriller
    Horror (27)                                            → horror
    Romance (10749)                                        → romance
    Comedy (35)                                            → comedy
    Animation (16)                                         → animation
    Documentary (99)                                       → documentary
    Family (10751), TV Movie (10770)                       → (unmapped)
"""

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Optional

import requests

PROJECT_ROOT = Path(__file__).parent.parent
MOVIES_JS = PROJECT_ROOT / "movies.js"

TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
RATE_LIMIT_DELAY = 0.25  # seconds between TMDB requests

# TMDB genre_id → site category
GENRE_CROSSWALK: dict[int, str] = {
    28:    "action/adventure",  # Action
    12:    "action/adventure",  # Adventure
    10752: "action/adventure",  # War
    37:    "action/adventure",  # Western
    18:    "drama",             # Drama
    36:    "drama",             # History
    10402: "drama",             # Music
    878:   "scifi/fantasy",     # Science Fiction
    14:    "scifi/fantasy",     # Fantasy
    53:    "thriller",          # Thriller
    80:    "thriller",          # Crime
    9648:  "thriller",          # Mystery
    27:    "horror",            # Horror
    10749: "romance",           # Romance
    35:    "comedy",            # Comedy
    16:    "animation",         # Animation
    99:    "documentary",       # Documentary
    # Unmapped: 10751 (Family), 10770 (TV Movie)
}

# Display order for genres in the output
GENRE_ORDER = [
    "action/adventure",
    "animation",
    "comedy",
    "documentary",
    "drama",
    "horror",
    "romance",
    "scifi/fantasy",
    "thriller",
]


# ---------------------------------------------------------------------------
# Data I/O  (same pattern as fetch_posters.py)
# ---------------------------------------------------------------------------

def load_data() -> dict:
    content = MOVIES_JS.read_text(encoding="utf-8")
    json_str = content.removeprefix("const MOVIES_DATA = ").rstrip().rstrip(";")
    return json.loads(json_str)


def save_data(data: dict) -> None:
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    with open(MOVIES_JS, "w", encoding="utf-8") as f:
        f.write("const MOVIES_DATA = ")
        f.write(json_str)
        f.write(";\n")


# ---------------------------------------------------------------------------
# TMDB API  (same pattern as fetch_posters.py)
# ---------------------------------------------------------------------------

def get_tmdb_api_key() -> str:
    key = os.environ.get("TMDB_API_KEY", "").strip()
    if not key:
        print("Error: TMDB_API_KEY environment variable is not set.")
        print()
        print("To get a free API key:")
        print("  1. Register at https://www.themoviedb.org/signup")
        print("  2. Go to Settings → API → Request API Key")
        print("  3. Export it in your shell:")
        print("       export TMDB_API_KEY=your_key_here")
        print()
        sys.exit(1)
    return key


def extract_title_and_year(raw_title: str) -> tuple[str, Optional[int]]:
    """Strip a trailing (YYYY) from a title and return (clean_title, year_or_None).

    Examples:
        "Footloose (1984)"  -> ("Footloose", 1984)
        "The Thing"         -> ("The Thing", None)
    """
    match = re.match(r"^(.*?)\s*\((\d{4})\)\s*$", raw_title)
    if match:
        return match.group(1).strip(), int(match.group(2))
    return raw_title, None


def _tmdb_search_request(title: str, year: Optional[int], api_key: str) -> Optional[dict]:
    """Single TMDB search request. Returns first result or None. Handles rate limiting."""
    params: dict = {"query": title, "api_key": api_key}
    if year is not None:
        params["year"] = year

    for attempt in range(2):
        try:
            resp = requests.get(TMDB_SEARCH_URL, params=params, timeout=10)
        except requests.RequestException as e:
            print(f"  -> Network error: {e}")
            return None

        if resp.status_code == 429:
            if attempt == 0:
                print("  -> Rate limited. Waiting 5 seconds...")
                time.sleep(5)
                continue
            else:
                print("  -> Still rate limited after retry. Skipping.")
                return None

        if resp.status_code == 401:
            print("  -> TMDB API key is invalid (401 Unauthorized).")
            sys.exit(1)

        if not resp.ok:
            print(f"  -> TMDB returned HTTP {resp.status_code}. Skipping.")
            return None

        results = resp.json().get("results", [])
        time.sleep(RATE_LIMIT_DELAY)
        return results[0] if results else None

    return None


def tmdb_search(title: str, year: Optional[int], api_key: str) -> Optional[dict]:
    """Search TMDB for a movie. Falls back to year-less search if year yields no results."""
    result = _tmdb_search_request(title, year, api_key)
    if result is None and year is not None:
        result = _tmdb_search_request(title, None, api_key)
    return result


# ---------------------------------------------------------------------------
# Genre mapping
# ---------------------------------------------------------------------------

def genre_ids_to_categories(genre_ids: list[int]) -> list[str]:
    """Map a list of TMDB genre_ids to sorted site category names."""
    categories = {GENRE_CROSSWALK[gid] for gid in genre_ids if gid in GENRE_CROSSWALK}
    return [g for g in GENRE_ORDER if g in categories]


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def collect_targets(data: dict, titles_filter: list[str], force_all: bool) -> list[dict]:
    """Return movie entries that need metadata fetched."""
    candidates: list[dict] = list(data.get("movies", []))

    if titles_filter:
        lower_filter = [t.lower() for t in titles_filter]
        matched: set[str] = set()
        filtered = []
        for entry in candidates:
            if entry.get("title", "").lower() in lower_filter:
                filtered.append(entry)
                matched.add(entry["title"].lower())
        for requested in lower_filter:
            if requested not in matched:
                print(f"Warning: '{requested}' not found in movie list.")
        return filtered

    if force_all:
        return candidates

    # Default: only movies missing the 'genres' field
    return [m for m in candidates if "genres" not in m]


def process_movie(entry: dict, api_key: str, dry_run: bool) -> bool:
    """Fetch and apply description + genres for one movie entry. Returns True on success."""
    raw_title = entry.get("title", "")
    search_title, year = extract_title_and_year(raw_title)

    print(f"\n[{raw_title}]")

    result = tmdb_search(search_title, year, api_key)
    if result is None:
        print("  -> Not found on TMDB, skipping.")
        return False

    tmdb_title = result.get("title", raw_title)
    tmdb_year = (result.get("release_date") or "")[:4]
    print(f"  -> Found: {tmdb_title} ({tmdb_year})")

    genre_ids: list[int] = result.get("genre_ids", [])
    categories = genre_ids_to_categories(genre_ids)
    description: str = result.get("overview") or ""

    print(f"  -> Genres: {categories if categories else '(none matched)'}")
    print(f"  -> Description: {description[:80] + '...' if len(description) > 80 else description or '(none)'}")

    if dry_run:
        print("  -> [DRY RUN] Would update entry.")
        return True

    entry["genres"] = categories
    entry["description"] = description
    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch movie descriptions and genres from TMDB and update movies.js.",
        epilog="Requires TMDB_API_KEY environment variable. "
               "Get a free key at https://www.themoviedb.org/settings/api",
    )
    parser.add_argument(
        "titles",
        nargs="*",
        metavar="TITLE",
        help="Movie title(s) to fetch. If omitted, all movies missing genres are processed.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="force_all",
        help="Re-fetch metadata even for movies that already have it.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fetched without modifying movies.js.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    api_key = get_tmdb_api_key()
    data = load_data()

    targets = collect_targets(data, args.titles, args.force_all)

    if not targets:
        print("All movies already have metadata. Use --all to re-fetch.")
        return

    label = "DRY RUN — " if args.dry_run else ""
    print(f"{label}Found {len(targets)} movie(s) to process.")

    updated = 0
    skipped = 0

    for entry in targets:
        if process_movie(entry, api_key, args.dry_run):
            updated += 1
        else:
            skipped += 1

    print()
    if not args.dry_run and updated > 0:
        save_data(data)
        print("Updated movies.js.")

    print(f"{updated} movie(s) updated, {skipped} skipped.")


if __name__ == "__main__":
    main()
