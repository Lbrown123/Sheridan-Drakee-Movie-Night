const DEFAULTS = { sortBy: 'date-desc', filterYear: '2026', filterGenre: 'any', searchQuery: '' };

const state = {
  movies: [],
  sortBy: DEFAULTS.sortBy,
  filterYear: DEFAULTS.filterYear,
  filterGenre: DEFAULTS.filterGenre,
  searchQuery: DEFAULTS.searchQuery
};

const sortSelect = document.getElementById('sort-select');
const yearSelect = document.getElementById('year-select');
const genreSelect = document.getElementById('genre-select');
const searchInput = document.getElementById('search-input');
const movieGrid = document.getElementById('movie-grid');
const noResults = document.getElementById('no-results');
const resetBtn = document.getElementById('reset-btn');
const searchFilterHint = document.getElementById('search-filter-hint');

init(MOVIES_DATA);

function init(data) {
  state.movies = data.movies || [];
  renderUpNext(data.upNext);
  populateYearFilter();
  renderMovies();

  sortSelect.addEventListener('change', () => {
    state.sortBy = sortSelect.value;
    updateReset();
    renderMovies();
  });

  yearSelect.addEventListener('change', () => {
    state.filterYear = yearSelect.value;
    updateReset();
    renderMovies();
  });

  genreSelect.addEventListener('change', () => {
    state.filterGenre = genreSelect.value;
    updateReset();
    renderMovies();
  });

  searchInput.addEventListener('input', () => {
    state.searchQuery = searchInput.value.trim();
    updateReset();
    renderMovies();
  });

  resetBtn.addEventListener('click', () => {
    state.sortBy = DEFAULTS.sortBy;
    state.filterYear = DEFAULTS.filterYear;
    state.filterGenre = DEFAULTS.filterGenre;
    state.searchQuery = DEFAULTS.searchQuery;
    sortSelect.value = DEFAULTS.sortBy;
    yearSelect.value = DEFAULTS.filterYear;
    genreSelect.value = DEFAULTS.filterGenre;
    searchInput.value = '';
    updateReset();
    renderMovies();
  });
}

function updateReset() {
  const changed = state.sortBy !== DEFAULTS.sortBy ||
                  state.filterYear !== DEFAULTS.filterYear ||
                  state.filterGenre !== DEFAULTS.filterGenre ||
                  state.searchQuery !== DEFAULTS.searchQuery;
  resetBtn.hidden = !changed;
}

function renderUpNext(upNext) {
  const section = document.getElementById('up-next');
  if (!upNext || !upNext.title) return;

  section.hidden = false;
  document.getElementById('up-next-title').textContent = upNext.title;

  const img = document.getElementById('up-next-img');
  const placeholder = document.getElementById('up-next-placeholder');
  const placeholderTitle = document.getElementById('up-next-placeholder-title');

  if (upNext.poster) {
    img.src = 'posters/' + upNext.poster;
    img.alt = upNext.title;
    img.hidden = false;
    placeholder.hidden = true;
    img.onerror = () => {
      img.hidden = true;
      placeholder.hidden = false;
      placeholderTitle.textContent = upNext.title;
    };
  } else {
    img.hidden = true;
    placeholder.hidden = false;
    placeholderTitle.textContent = upNext.title;
  }
}

function populateYearFilter() {
  const years = [...new Set(state.movies.filter(m => m.dateWatched).map(m => m.dateWatched.slice(0, 4)))].sort().reverse();
  years.forEach(year => {
    const opt = document.createElement('option');
    opt.value = year;
    opt.textContent = year;
    yearSelect.appendChild(opt);
  });
  yearSelect.value = DEFAULTS.filterYear;
}

function getFilteredAndSortedMovies() {
  let movies = state.movies;

  if (state.filterYear !== 'any') {
    movies = movies.filter(m => m.dateWatched && m.dateWatched.slice(0, 4) === state.filterYear);
  }

  if (state.filterGenre !== 'any') {
    movies = movies.filter(m => Array.isArray(m.genres) && m.genres.includes(state.filterGenre));
  }

  if (state.searchQuery) {
    const q = state.searchQuery.toLowerCase();
    movies = movies.filter(m => m.title.toLowerCase().includes(q));
  }

  movies = [...movies].sort((a, b) => {
    switch (state.sortBy) {
      case 'date-desc':
        return (b.dateWatched || '').localeCompare(a.dateWatched || '');
      case 'date-asc':
        return (a.dateWatched || '').localeCompare(b.dateWatched || '');
      case 'rating-logan':
        return comparByRating(a, b, 'logan');
      case 'rating-elizabeth':
        return comparByRating(a, b, 'elizabeth');
      case 'rating-abby':
        return comparByRating(a, b, 'abby');
      case 'rating-average':
        return compareByAverage(a, b);
      default:
        return 0;
    }
  });

  return movies;
}

function comparByRating(a, b, person) {
  const ra = a.ratings[person] ?? -1;
  const rb = b.ratings[person] ?? -1;
  if (rb !== ra) return rb - ra;
  return (b.dateWatched || '').localeCompare(a.dateWatched || '');
}

function compareByAverage(a, b) {
  const aa = computeAverage(a.ratings) ?? -1;
  const ab = computeAverage(b.ratings) ?? -1;
  if (ab !== aa) return ab - aa;
  return (b.dateWatched || '').localeCompare(a.dateWatched || '');
}

function computeAverage(ratings) {
  const vals = Object.values(ratings).filter(v => typeof v === 'number');
  if (vals.length === 0) return null;
  return vals.reduce((sum, v) => sum + v, 0) / vals.length;
}

function updateSearchHint() {
  const hasSearch = state.searchQuery !== '';
  const yearFiltered = state.filterYear !== 'any';
  const genreFiltered = state.filterGenre !== 'any';

  if (!hasSearch || (!yearFiltered && !genreFiltered)) {
    searchFilterHint.hidden = true;
    return;
  }

  const both = yearFiltered && genreFiltered;
  const filterText = both ? 'year and genre' : yearFiltered ? 'year' : 'genre';
  const resetText = both ? 'Any Year and All Genres' : yearFiltered ? 'Any Year' : 'All Genres';
  const plural = both ? 's' : '';

  searchFilterHint.textContent = `Your search is currently filtered by ${filterText}. You may want to change the filter${plural} to ${resetText} to get a full search.`;
  searchFilterHint.hidden = false;
}

function renderMovies() {
  const movies = getFilteredAndSortedMovies();
  updateCount(movies.length);
  updateSearchHint();
  movieGrid.innerHTML = '';

  if (movies.length === 0) {
    noResults.hidden = false;
    return;
  }

  noResults.hidden = true;
  movies.forEach(movie => movieGrid.appendChild(createMovieCard(movie)));
}

function updateCount(count) {
  const countEl = document.getElementById('movie-count');
  const yearFiltered = state.filterYear !== 'any';
  const genreFiltered = state.filterGenre !== 'any';
  const noun = count === 1 ? 'movie' : 'movies';

  let text;
  if (!yearFiltered && !genreFiltered) {
    text = `${count} ${noun} total`;
  } else if (yearFiltered && !genreFiltered) {
    const currentYear = new Date().getFullYear().toString();
    if (state.filterYear === currentYear) {
      text = `${count} ${noun} watched in ${state.filterYear} so far`;
    } else {
      text = `${count} ${noun} watched in ${state.filterYear}`;
    }
  } else {
    text = `${count} ${noun} meet your filter criteria`;
  }

  countEl.textContent = text;
}

function createMovieCard(movie) {
  const card = document.createElement('div');
  card.className = 'movie-card';

  const avg = computeAverage(movie.ratings);

  card.innerHTML = `
    <div class="poster-wrapper">
      ${movie.poster
        ? `<img src="posters/${movie.poster}" alt="${movie.title}" onerror="this.parentElement.innerHTML='<div class=\\'poster-placeholder\\'><span>${escapeHtml(movie.title)}</span></div>'">`
        : `<div class="poster-placeholder"><span>${escapeHtml(movie.title)}</span></div>`
      }
    </div>
    <div class="card-body">
      <h3>${escapeHtml(movie.title)}</h3>
      <div class="date">${movie.dateWatched ? formatDate(movie.dateWatched) : ''}</div>
      <div class="ratings">
        ${ratingRow('Logan', movie.ratings.logan)}
        ${ratingRow('Elizabeth', movie.ratings.elizabeth)}
        ${ratingRow('Abby', movie.ratings.abby)}
        <div class="average-row">
          <span class="name">Average</span>
          <span class="average-value">${avg !== null ? renderStars(Math.round(avg * 2) / 2) + ' ' + avg.toFixed(1) : 'N/A'}</span>
        </div>
      </div>
    </div>
  `;

  return card;
}

function ratingRow(name, rating) {
  if (rating != null) {
    const label = Number.isInteger(rating) ? String(rating) : rating.toFixed(1);
    return `
      <div class="rating-row">
        <span class="name">${name}</span>
        <span class="stars">${renderStars(rating)} <span class="rating-value">${label}</span></span>
      </div>
    `;
  }
  return `
    <div class="rating-row">
      <span class="name">${name}</span>
      <span class="stars"><span style="color:var(--text-secondary)">N/A</span></span>
    </div>
  `;
}

function renderStars(rating) {
  const full = Math.floor(rating);
  const half = (rating - full) >= 0.5;
  let html = '';
  for (let i = 1; i <= 5; i++) {
    if (i <= full) {
      html += `<span class="star filled">&#9733;</span>`;
    } else if (i === full + 1 && half) {
      html += `<span class="star half">&#9733;</span>`;
    } else {
      html += `<span class="star">&#9733;</span>`;
    }
  }
  return html;
}

function formatDate(dateString) {
  const parts = dateString.split('-');
  if (parts.length === 1) return parts[0];
  const [year, month, day] = parts.map(Number);
  const date = new Date(year, month - 1, day);
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

document.addEventListener('DOMContentLoaded', () => {
  const sentinel = document.getElementById('controls-sentinel');
  const notchFill = document.getElementById('notch-fill');

  if (sentinel && notchFill) {
    const observer = new IntersectionObserver((entries) => {
      const entry = entries[0];
      
      // If the sentinel's top is less than 0, it has scrolled out of view at the top,
      // which means the .controls bar immediately below it is now stuck.
      if (entry.boundingClientRect.top < 0 && !entry.isIntersecting) {
        notchFill.classList.add('visible');
      } else {
        notchFill.classList.remove('visible');
      }
    }, {
      rootMargin: '0px',
      threshold: 0
    });

    observer.observe(sentinel);
  }
});
