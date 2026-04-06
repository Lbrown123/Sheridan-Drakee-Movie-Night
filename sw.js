const CACHE_VERSION = 'v1';
const ASSETS_CACHE = `assets-${CACHE_VERSION}`;
const POSTERS_CACHE = 'posters-cache';

const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/style.css',
  '/script.js',
  '/movies.js',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(ASSETS_CACHE)
      .then(cache => cache.addAll(PRECACHE_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys
        .filter(key => key.startsWith('assets-') && key !== ASSETS_CACHE)
        .map(key => caches.delete(key))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const { request } = event;

  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (url.pathname.startsWith('/posters/')) {
    event.respondWith(handlePoster(request));
    return;
  }

  if (url.pathname === '/' || url.pathname === '/index.html') {
    event.respondWith(handleNetworkFirst(request));
    return;
  }

  event.respondWith(handleStaleWhileRevalidate(request));
});

async function handlePoster(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(POSTERS_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('', { status: 404, statusText: 'Not Found' });
  }
}

async function handleNetworkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(ASSETS_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    return cached || new Response('Offline', { status: 503 });
  }
}

async function handleStaleWhileRevalidate(request) {
  const cache = await caches.open(ASSETS_CACHE);
  const cached = await cache.match(request);

  const fetchPromise = fetch(request).then(response => {
    if (response.ok) cache.put(request, response.clone());
    return response;
  }).catch(() => null);

  return cached || await fetchPromise;
}
