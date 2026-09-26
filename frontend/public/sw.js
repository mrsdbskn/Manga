/**
 * sw.js - Service Worker for One Piece Manga Showcase PWA
 * Caches app shell, fonts, and assets for fast load times and offline reading resilience.
 */

const CACHE_NAME = 'one-piece-manga-v2';
const APP_SHELL = [
  './',
  './index.html',
  './manifest.json',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(APP_SHELL).catch((err) => {
        console.warn('PWA shell pre-cache note:', err);
      });
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  
  // Skip non-GET requests
  if (req.method !== 'GET') return;

  // Let browser handle chrome extensions or external cross-origin analytics
  const url = new URL(req.url);
  if (!url.protocol.startsWith('http')) return;

  // Network-first for dynamic master catalog index.json so changes are immediately reflected
  if (url.pathname.endsWith('index.json')) {
    event.respondWith(
      fetch(req)
        .then((res) => {
          if (res.ok) {
            const clone = res.clone();
            caches.open(CACHE_NAME).then((c) => c.put(req, clone));
          }
          return res;
        })
        .catch(() => caches.match(req))
    );
    return;
  }

  // Cache-first with stale-while-revalidate for assets, images, and fonts
  event.respondWith(
    caches.match(req).then((cached) => {
      if (cached) {
        // Asynchronously update in background if online
        fetch(req).then((fresh) => {
          if (fresh && fresh.ok) {
            caches.open(CACHE_NAME).then((c) => c.put(req, fresh));
          }
        }).catch(() => {});
        return cached;
      }

      return fetch(req).then((res) => {
        if (res && res.ok && (req.url.startsWith(self.location.origin) || req.url.includes('fonts.gstatic.com'))) {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((c) => c.put(req, clone));
        }
        return res;
      }).catch((err) => {
        // Fallback for navigation requests
        if (req.mode === 'navigate') {
          return caches.match('./index.html');
        }
        throw err;
      });
    })
  );
});
