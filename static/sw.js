// Service Worker for offline support
const CACHE_NAME = 'japan-trip-v1';
const CACHE_URLS = [
    '/',
    '/static/css/app.css',
    '/static/js/app.js',
    '/static/js/itinerary.js',
    'https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css',
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(CACHE_URLS))
    );
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', event => {
    // Network-first strategy for API calls, cache-first for assets
    if (event.request.url.includes('/api/') || event.request.method !== 'GET') {
        return; // Let the browser handle API requests normally
    }

    event.respondWith(
        fetch(event.request)
            .then(response => {
                const clone = response.clone();
                caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                return response;
            })
            .catch(() => caches.match(event.request))
    );
});
