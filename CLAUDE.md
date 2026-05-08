# Movie Night — Developer Notes

Static GitHub Pages site for Logan, Elizabeth, and Abby's movie night ratings. No build tools, no framework, no server.

## Files

- `index.html` — page structure
- `style.css` — dark cinema theme, CSS custom properties
- `script.js` — filtering, sorting, rendering (no dependencies)
- `movies.js` — **all data; the only file needing regular edits**
- `posters/` — poster images (JPG/WebP)
- `sw.js` — service worker; handles browser caching strategy

## Data (`movies.js`)

Defines a single global `MOVIES_DATA` with two keys:

**`upNext`** — shown in the top banner. Set to `null` to hide.
```json
"upNext": { "title": "Movie Title", "poster": "filename.jpg" }
```

**`movies`** — array of watched movies. Order doesn't matter; site sorts by date.
```json
{
  "title": "The Thing",
  "dateWatched": "2026-03-28",
  "ratings": { "logan": 5, "elizabeth": 4, "abby": 4 },
  "poster": "the-thing.jpg"
}
```

Field rules:
- `dateWatched`: `YYYY-MM-DD` (required for sorting)
- `ratings`: integers 1–5; omit a person's key if they missed — shows "N/A", excluded from average
- `poster`: filename only (site prepends `posters/`); omit for a styled title placeholder

## Adding a Movie

1. Add object to `movies` array in `movies.js`
2. Drop poster image in `posters/` (optional; use `kebab-case-title.jpg`, 2:3 ratio)
3. Update `upNext` to the next film

## JavaScript (`script.js`)

State: `{ movies: [], sortBy: 'date-desc', filterYear: 'any' }`

Data flow: `movies.js` sets `MOVIES_DATA` → `init()` → `renderUpNext`, `populateYearFilter`, `renderMovies`. Sort/year `<select>` changes trigger `renderMovies`.

Sort behavior: descending; ties broken by date desc; missing ratings sort to bottom.

| Function | Purpose |
|---|---|
| `getFilteredAndSortedMovies()` | Filter + sort pipeline; never mutates state |
| `renderMovies()` | Clears grid, renders cards, shows "no results" if empty |
| `createMovieCard(movie)` | Builds card DOM element |
| `computeAverage(ratings)` | Mean of present ratings; `null` if none |
| `renderStars(rating)` | 5-star HTML string |
| `formatDate(dateString)` | `"2026-03-28"` → `"March 28, 2026"` |
| `escapeHtml(text)` | XSS-safe escaping for innerHTML |

## CSS (`style.css`)

Theme via `:root` custom properties: `--bg-primary`, `--bg-card`, `--accent` (gold/amber), `--text-secondary`. Grid: `repeat(auto-fill, minmax(260px, 1fr))`. One breakpoint at `max-width: 600px`.

## Service Worker (`sw.js`)

Caching strategies by asset type:
- **Posters** (`/posters/*`): cache-first, stored in `posters-cache` forever — **poster filenames are immutable**; same filename must always mean the same image
- **`index.html`, `movies.js`**: network-first with cache fallback — always fetched fresh when online, so data and page-shell updates appear immediately on the next visit. Falls back to `assets-vN` cache if offline.
- **`script.js`, `style.css`**: stale-while-revalidate via `assets-vN` — cached version served immediately, update fetched in background for next visit. Bump `CACHE_VERSION` to force fresh fetch.

To force all visitors to re-fetch non-poster `script.js`/`style.css`: bump `CACHE_VERSION` in `sw.js` (e.g. `'v1'` → `'v2'`). This clears `assets-vN` but never touches `posters-cache`. Note: a version bump only takes effect on the *second* visit after deploy, because the old SW is still active during the first. Editing `movies.js` does **not** require a version bump — it's network-first.

If a poster file was replaced with the same filename, users with it cached won't see the new image — rename the file and update `movies.js` instead.
