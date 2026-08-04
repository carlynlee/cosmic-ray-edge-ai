// Bump CACHE on every deploy of phone.html / model.js / fl_client.js so phones
// pick up the new code instead of a stale cached copy.
const CACHE = 'cosmicphysicist-v2';
const SHELL = ['/', '/manifest.json', '/phone.html', '/model.js', '/fl_client.js'];

self.addEventListener('install', e => {
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)));
});

self.addEventListener('activate', e =>
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  )
);

self.addEventListener('fetch', e => {
  // Only cache same-origin GETs; let API / FL / stream calls hit the network.
  if (e.request.method !== 'GET') return;
  if (e.request.url.includes('/stream') || e.request.url.includes('/api/')) return;
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
