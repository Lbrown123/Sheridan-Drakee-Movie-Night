# Movie Night — Developer Notes

Static GitHub Pages site for Logan, Elizabeth, and Abby's movie night ratings. No build tools, no framework, no server.

## Files

- `index.html` — page structure
- `style.css` — dark cinema theme, CSS custom properties
- `script.js` — filtering, sorting, rendering (no dependencies)
- `movies.js` — **all data; the only file needing regular edits**
- `posters/` — poster images (JPG/WebP)
- `og-image.jpg` — social share card (1200×630), rendered from `scripts/og-image.html`
- `sw.js` — service worker; handles browser caching strategy
- `holiday.js` — seasonal decorations (header string lights + falling-snow canvas). To retire the holiday theme: remove its `<script>` tag and the `#snow` canvas / `#lights` div in `index.html`, then restyle the header and `:root` palette in `style.css`

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

## Social share image (`og-image.jpg`)

**Whenever the site's design changes — especially the header, title, palette, or seasonal theme — re-render the social share image so link previews match the site.**

- Source: `scripts/og-image.html`. It pulls in `style.css` and `holiday.js`, but its `<header>` markup is a copy of the one in `index.html` — update both if the header markup changes. Its inline `<style>` only resizes things for the 1200×630 card.
- Render (with the local server from `.claude/launch.json` running on port 8080):
  ```bash
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars --force-device-scale-factor=2 --window-size=1200,630 --virtual-time-budget=6000 --screenshot=/tmp/og-2x.png http://localhost:8080/scripts/og-image.html && sips -z 630 1200 -s format jpeg -s formatOptions 88 /tmp/og-2x.png --out og-image.jpg
  ```
- Social platforms cache preview images by URL. After replacing the image, either give it a new filename (and update the `og:image` tag in `index.html`) or re-scrape the URL with each platform's debugger (e.g. Facebook Sharing Debugger).
