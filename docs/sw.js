// Pond hub service worker.
// Stale-while-revalidate: every page, script and JSON file is answered from the saved copy straight
// away (no network wait), and refreshed in the background, so the next visit has the latest version.
// The shell and data files are saved on install, so even the first tab switch is instant.
const CACHE = 'pond-v3';
const PRECACHE = [
  './', 'assets/site.js', 'assets/style.css', 'manifest.webmanifest',
  'gallery/', 'gallery/renders.json',
  'roadmap/', 'roadmap/item.html', 'roadmap/roadmap.json',
  'decisions/', 'decisions/docs.json',
  'shopping/', 'shopping/shopping.json',
  'history/', 'history/history.json'
];
const IMAGE_HOST = 'pond-render-500653746288.us-east1.run.app';

self.addEventListener('install', e => {
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then(c => Promise.all(PRECACHE.map(u => c.add(u).catch(() => {})))));
});
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  const sameOrigin = url.origin === self.location.origin;
  const isThumb = url.hostname === IMAGE_HOST && req.destination === 'image';
  if (!sameOrigin && !isThumb) return;
  e.respondWith((async () => {
    const cache = await caches.open(CACHE);
    // Match ignoring the query string so "item.html?id=x" and "#hash" pages reuse the saved shell.
    const saved = await cache.match(req, { ignoreSearch: sameOrigin });
    const update = fetch(req).then(res => {
      if (res && (res.ok || res.type === 'opaque')) cache.put(req, res.clone());
      return res;
    });
    if (saved) { e.waitUntil(update.catch(() => {})); return saved; }
    return update;
  })());
});
