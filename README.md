# Movie Night

A ratings archive for our regular movie nights. Every film gets a score from Logan, Elizabeth, and Abby — this site collects them all in one place to share with friends.

## Features

- **Up Next** — See which movie is queued up for the next movie night
- **Movie grid** — Every film we've watched, with each person's individual star rating (1–5) and the group average
- **Sort** — Reorder the list by date, by any individual's rating, or by average rating
- **Filter by year** — Narrow the list to films watched in a specific year, or view everything at once
- **Poster art** — Movie posters displayed on each card when available

## How It Works

The site is a static page hosted on GitHub Pages. All movie data lives in `movies.js` — no database, no backend. Filtering and sorting all happen in the browser instantly.

## Ratings

Each movie is rated on a 1–5 star scale:

| Stars | Meaning |
|---|---|
| ⭐⭐⭐⭐⭐ | 5 — Loved it |
| ⭐⭐⭐⭐ | 4 — Really liked it |
| ⭐⭐⭐ | 3 — It was fine |
| ⭐⭐ | 2 — Didn't enjoy it |
| ⭐ | 1 — Did not like it |

If someone missed a movie night, their rating shows as N/A and they're excluded from the average calculation.

## Sort Options

| Option | Description |
|---|---|
| Date (Newest First) | Default — most recently watched at the top |
| Date (Oldest First) | Chronological order |
| Logan's Rating | Highest Logan score first |
| Elizabeth's Rating | Highest Elizabeth score first |
| Abby's Rating | Highest Abby score first |
| Average Rating | Highest group average first |

All rating sorts show the best-rated films first. Ties are broken by most recently watched.

## Caching

The site uses a service worker (`sw.js`) to cache assets in your browser, so repeat visits don't re-download the 21 MB of poster images every time. GitHub Pages only caches files for 10 minutes by default — the service worker overrides this in the browser.

**How it works:**
- **Posters** are cached permanently the first time you load them. Every visit after that serves them instantly with no network request. As you scroll through the page, newly visible posters get added to the cache.
- **`movies.js`** (the data file) is served from cache immediately, while a fresh copy is fetched in the background. This means a newly added movie will show up on your *second* page load after the update is pushed — not the first. This is intentional and keeps the site feeling fast.
- **`index.html`, `script.js`, `style.css`** work the same way as `movies.js`.

**Things to know when making updates:**

| Action | What happens |
|---|---|
| Add a new movie to `movies.js` | Appears after two page loads (stale-while-revalidate) |
| Add a new poster image | Downloaded and cached on first page load that shows it |
| **Replace a poster with the same filename** | **Won't update for anyone who already has it cached** — rename the file and update `movies.js` instead |
| Force everyone to re-fetch all non-poster assets | Bump `CACHE_VERSION` in `sw.js` (e.g. `'v1'` → `'v2'`) and push |

The poster cache (`posters-cache`) is never cleared automatically, even when `CACHE_VERSION` is bumped — posters are assumed to be permanent once uploaded. If you need to clear it manually, open DevTools → Application → Cache Storage → right-click `posters-cache` → Delete.

## Tech

Plain HTML, CSS, and JavaScript. No frameworks, no build tools. Hosted on GitHub Pages. Service worker handles browser-side caching.
