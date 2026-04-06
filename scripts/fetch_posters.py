"""
fetch_posters.py — download movie posters from TMDB and update movies.js

Usage (from project root):
    TMDB_API_KEY=your_key python scripts/fetch_posters.py           # fetch all missing
    TMDB_API_KEY=your_key python scripts/fetch_posters.py "Title"   # fetch specific movie(s)
    TMDB_API_KEY=your_key python scripts/fetch_posters.py --all     # re-fetch everything
    TMDB_API_KEY=your_key python scripts/fetch_posters.py --dry-run # preview without downloading

Get a free TMDB API key at https://www.themoviedb.org/settings/api
"""

import argparse
import io
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Optional

import requests
from PIL import Image

PROJECT_ROOT = Path(__file__).parent.parent
MOVIES_JS = PROJECT_ROOT / "movies.js"
POSTERS_DIR = PROJECT_ROOT / "posters"

TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

POSTER_MAX_WIDTH = 500
JPEG_QUALITY = 85
RATE_LIMIT_DELAY = 0.25  # seconds between TMDB requests


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def to_kebab_case(title: str) -> str:
    """Convert a movie title to a kebab-case filename stem."""
    # Normalize unicode: decompose accents then drop non-ASCII combining marks
    normalized = unicodedata.normalize("NFD", title)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    lower = ascii_only.lower()
    # Replace & with "and"
    lower = lower.replace("&", "and")
    # Strip chars that aren't alphanumeric, spaces, or hyphens
    cleaned = re.sub(r"[^a-z0-9 -]", "", lower)
    # Collapse runs of whitespace/hyphens to a single hyphen
    slug = re.sub(r"[\s-]+", "-", cleaned).strip("-")
    return slug


def poster_filename_for(title: str) -> str:
    return to_kebab_case(title) + ".jpg"


# ---------------------------------------------------------------------------
# Data I/O
# ---------------------------------------------------------------------------

def load_data() -> dict:
    content = MOVIES_JS.read_text(encoding="utf-8")
    # Strip JS wrapper: "const MOVIES_DATA = {...};\n"
    json_str = content.removeprefix("const MOVIES_DATA = ").rstrip().rstrip(";")
    return json.loads(json_str)


def save_data(data: dict) -> None:
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    with open(MOVIES_JS, "w", encoding="utf-8") as f:
        f.write("const MOVIES_DATA = ")
        f.write(json_str)
        f.write(";\n")


# ---------------------------------------------------------------------------
# TMDB API
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
        # Retry without year constraint
        result = _tmdb_search_request(title, None, api_key)
    return result


def tmdb_poster_url(result: dict) -> Optional[str]:
    poster_path = result.get("poster_path")
    if not poster_path:
        return None
    return f"{TMDB_IMAGE_BASE}{poster_path}"


# ---------------------------------------------------------------------------
# Image download + save
# ---------------------------------------------------------------------------

def download_and_save_poster(url: str, dest_path: Path) -> bool:
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  -> Failed to download image: {e}")
        return False

    try:
        img = Image.open(io.BytesIO(resp.content))

        if img.width > POSTER_MAX_WIDTH:
            ratio = POSTER_MAX_WIDTH / img.width
            new_height = int(img.height * ratio)
            img = img.resize((POSTER_MAX_WIDTH, new_height), Image.LANCZOS)

        if img.mode != "RGB":
            img = img.convert("RGB")

        img.save(dest_path, "JPEG", quality=JPEG_QUALITY, optimize=True)
        return True
    except Exception as e:
        print(f"  -> Failed to process image: {e}")
        return False


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def collect_targets(
    data: dict,
    titles_filter: list[str],
    force_all: bool,
) -> list[dict]:
    """Return list of movie entry dicts that need a poster fetched."""
    candidates: list[dict] = []

    up_next = data.get("upNext")
    if up_next and isinstance(up_next, dict):
        candidates.append(up_next)

    candidates.extend(data.get("movies", []))

    if titles_filter:
        lower_filter = [t.lower() for t in titles_filter]
        matched_titles: set[str] = set()
        filtered = []
        for entry in candidates:
            if entry.get("title", "").lower() in lower_filter:
                filtered.append(entry)
                matched_titles.add(entry["title"].lower())
        for requested in lower_filter:
            if requested not in matched_titles:
                print(f"Warning: '{requested}' not found in movie list.")
        return filtered

    if force_all:
        return candidates

    # Default: only movies missing a poster field, or whose poster file doesn't exist
    result = []
    for entry in candidates:
        poster_field = entry.get("poster")
        if poster_field and (POSTERS_DIR / poster_field).exists():
            continue  # Already have it
        result.append(entry)
    return result


def extract_title_and_year(raw_title: str) -> tuple[str, Optional[int]]:
    """Strip a trailing (YYYY) from a title and return (clean_title, year_or_None).

    Examples:
        "Footloose (1984)"      -> ("Footloose", 1984)
        "Mean Girls (2024)"     -> ("Mean Girls", 2024)
        "The Thing"             -> ("The Thing", None)
    """
    match = re.match(r"^(.*?)\s*\((\d{4})\)\s*$", raw_title)
    if match:
        return match.group(1).strip(), int(match.group(2))
    return raw_title, None


def process_movie(entry: dict, api_key: str, dry_run: bool) -> bool:
    """Fetch and save poster for one movie entry. Returns True on success."""
    raw_title = entry.get("title", "")

    # Use year embedded in title (e.g. "Footloose (1984)") rather than dateWatched,
    # because dateWatched is when the group watched it, not the movie's release year.
    search_title, year = extract_title_and_year(raw_title)

    print(f"\n[{raw_title}]")

    result = tmdb_search(search_title, year, api_key)
    if result is None:
        print("  -> Not found on TMDB, skipping.")
        return False

    poster_url = tmdb_poster_url(result)
    if poster_url is None:
        print("  -> No poster available on TMDB, skipping.")
        return False

    tmdb_title = result.get("title", raw_title)
    tmdb_year = (result.get("release_date") or "")[:4]
    print(f"  -> Found: {tmdb_title} ({tmdb_year})")
    print(f"  -> Poster: {poster_url}")

    filename = poster_filename_for(raw_title)
    dest = POSTERS_DIR / filename

    if dry_run:
        print(f"  -> [DRY RUN] Would save to posters/{filename}")
        return True

    if download_and_save_poster(poster_url, dest):
        print(f"  -> Saved posters/{filename}")
        entry["poster"] = filename
        return True

    return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch movie posters from TMDB and update movies.js.",
        epilog="Requires TMDB_API_KEY environment variable. "
               "Get a free key at https://www.themoviedb.org/settings/api",
    )
    parser.add_argument(
        "titles",
        nargs="*",
        metavar="TITLE",
        help="Movie title(s) to fetch. If omitted, all movies without posters are processed.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="force_all",
        help="Re-fetch posters even for movies that already have one.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without downloading or modifying files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    api_key = get_tmdb_api_key()
    data = load_data()
    POSTERS_DIR.mkdir(exist_ok=True)

    targets = collect_targets(data, args.titles, args.force_all)

    if not targets:
        print("All posters already present. Use --all to re-fetch.")
        return

    label = "DRY RUN — " if args.dry_run else ""
    print(f"{label}Found {len(targets)} movie(s) to process.")

    fetched = 0
    skipped = 0

    for entry in targets:
        if process_movie(entry, api_key, args.dry_run):
            fetched += 1
        else:
            skipped += 1

    print()
    if not args.dry_run and fetched > 0:
        save_data(data)
        print("Updated movies.js.")

    print(f"{fetched} poster(s) fetched, {skipped} skipped.")


if __name__ == "__main__":
    main()
