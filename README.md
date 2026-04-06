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

## Tech

Plain HTML, CSS, and JavaScript. No frameworks, no build tools. Hosted on GitHub Pages.
