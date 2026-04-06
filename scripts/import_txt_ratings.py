"""
import_txt_ratings.py — parse OG Ratings/2021 and 2022.txt and merge into movies.js

Emoji key (as confirmed by user):
    🐢 = Abby
    🦊 = Elizabeth
    🐧 = Logan

Usage (from project root):
    python scripts/import_txt_ratings.py             # import and write movies.js
    python scripts/import_txt_ratings.py --dry-run   # preview without writing
"""

import argparse
import datetime
import json
import re
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
MOVIES_JS = PROJECT_ROOT / "movies.js"
TXT_FILE = PROJECT_ROOT / "OG Ratings" / "2021 and 2022.txt"

TURTLE  = "\U0001f422"  # 🐢 = Abby
FOX     = "\U0001f98a"  # 🦊 = Elizabeth
PENGUIN = "\U0001f427"  # 🐧 = Logan

DATE_RE  = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{2})\b")
# Matches a standalone float (avg score) — used to strip it from undated titles
FLOAT_RE = re.compile(r"\b\d+\.\d+\b")


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def parse_date(m: str, d: str, y: str) -> Optional[str]:
    try:
        year = 2000 + int(y)
        return datetime.date(year, int(m), int(d)).isoformat()
    except ValueError:
        return None


def count_emoji(text: str, emoji: str) -> int:
    return text.count(emoji)


def parse_rating_line(line: str) -> tuple[Optional[str], Optional[float]]:
    """Parse a '* 🐢🐢🐢.5' line into (person, rating) or (None, None)."""
    body = line.lstrip("*").strip()

    if "N/A" in body:
        return None, None

    has_half = ".5" in body

    if TURTLE in body:
        person = "abby"
        count = count_emoji(body, TURTLE)
    elif FOX in body:
        person = "elizabeth"
        count = count_emoji(body, FOX)
    elif PENGUIN in body:
        person = "logan"
        count = count_emoji(body, PENGUIN)
    else:
        return None, None

    return person, count + (0.5 if has_half else 0)


def extract_title(header: str) -> str:
    """
    Extract a clean movie title from a (possibly messy) header string.

    For headers with a date, everything before the date is the title.
    For headers without a date, strip the avg score and status emoji from the right.
    """
    m = DATE_RE.search(header)
    if m:
        raw_title = header[: m.start()]
    else:
        # No date — strip trailing avg score and status markers
        raw_title = header
        raw_title = raw_title.replace("✅", "").replace("🚫", "")
        raw_title = FLOAT_RE.sub("", raw_title)

    # Strip empty parens, trailing open-paren (from date in parens), punctuation, whitespace
    raw_title = re.sub(r"\(\s*\)", "", raw_title)
    raw_title = raw_title.strip(" .,(")
    return raw_title


# ---------------------------------------------------------------------------
# Block grouping
# ---------------------------------------------------------------------------

def group_blocks(lines: list[str]) -> list[tuple[list[str], list[str]]]:
    """
    Group lines into (header_lines, rating_lines) blocks.

    A new block starts when a non-'*' non-blank line appears after at least
    one '*' rating line — handles back-to-back entries with no blank separator.
    """
    blocks: list[tuple[list[str], list[str]]] = []
    current_headers: list[str] = []
    current_ratings: list[str] = []
    seen_star = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("*"):
            seen_star = True
            current_ratings.append(stripped)
        else:
            if seen_star:
                # Flush current block, start a new one
                blocks.append((current_headers, current_ratings))
                current_headers = [stripped]
                current_ratings = []
                seen_star = False
            else:
                current_headers.append(stripped)

    # Flush last block
    if current_headers or current_ratings:
        blocks.append((current_headers, current_ratings))

    return blocks


# ---------------------------------------------------------------------------
# Movie parsing
# ---------------------------------------------------------------------------

def parse_movie(header_lines: list[str], rating_lines: list[str]) -> Optional[dict]:
    """Convert a (header_lines, rating_lines) block into a movie dict."""
    if not rating_lines:
        return None  # Not a movie block (e.g., trailing note)

    header = " ".join(header_lines)

    # Date
    date_match = DATE_RE.search(header)
    date_watched = parse_date(*date_match.groups()) if date_match else None

    # Title
    title = extract_title(header)
    if not title:
        return None

    # Ratings
    ratings: dict[str, float] = {}
    for line in rating_lines:
        person, rating = parse_rating_line(line)
        if person is not None:
            ratings[person] = rating

    if not ratings:
        return None

    movie: dict = {"title": title, "ratings": ratings}
    if date_watched:
        movie["dateWatched"] = date_watched

    return movie


def parse_txt(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    blocks = group_blocks(lines)
    movies = []
    for header_lines, rating_lines in blocks:
        movie = parse_movie(header_lines, rating_lines)
        if movie:
            movies.append(movie)
    return movies


# ---------------------------------------------------------------------------
# movies.js I/O  (same format as import_ratings.py and fetch_posters.py)
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
# Merge + sort
# ---------------------------------------------------------------------------

def merge(existing: list[dict], new_movies: list[dict]) -> list[dict]:
    seen = {m["title"].lower().strip() for m in existing}
    added = []
    for movie in new_movies:
        key = movie["title"].lower().strip()
        if key not in seen:
            seen.add(key)
            added.append(movie)
    return existing + added


def sort_movies(movies: list[dict]) -> list[dict]:
    def key(m):
        d = m.get("dateWatched")
        return (1, d) if d else (0, "")
    return sorted(movies, key=key, reverse=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse 2021 and 2022.txt emoji ratings and merge into movies.js."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print parsed movies without writing movies.js.",
    )
    args = parser.parse_args()

    print(f"Reading {TXT_FILE}")
    parsed = parse_txt(TXT_FILE)
    print(f"Parsed {len(parsed)} movies from text file.")

    data = load_data()
    existing = data.get("movies", [])

    merged = merge(existing, parsed)
    added = len(merged) - len(existing)
    print(f"New movies to add: {added}  (skipped {len(parsed) - added} duplicates)")

    if args.dry_run:
        print("\n--- DRY RUN: parsed movies ---")
        for m in parsed:
            key = m["title"].lower().strip()
            dupe = key in {e["title"].lower().strip() for e in existing}
            tag = " [SKIP - duplicate]" if dupe else ""
            ratings_str = ", ".join(
                f"{p}={v}" for p, v in sorted(m["ratings"].items())
            )
            print(f"  {m['title']!r:55s}  {m.get('dateWatched', 'no date'):12s}  [{ratings_str}]{tag}")
        return

    data["movies"] = sort_movies(merged)
    save_data(data)
    print(f"Wrote {MOVIES_JS}  (total movies: {len(data['movies'])})")


if __name__ == "__main__":
    main()
