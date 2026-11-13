// Pond hub service worker.
// Tries the network first so the app shows the latest version, but waits at most 1.5 s:
// if the network is slower than that, it shows the saved copy and updates it in the background.
// Offline, it always uses the saved copy.
const CACHE = 'pond-v4';
const WAIT_MS = 1500;

self.addEventListener('install', e => { self.skipWaiting(); });
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== self.location.origin) return;
  // The sim control page needs cross-origin isolation and big WASM files: never touch it.
  if (new URL(req.url).pathname.includes('/sim/')) return;
  e.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const network = fetch(req, { cache: 'no-store' }).then(res => {
      // only whole answers can be saved (a partial 206 would throw and break the page)
      if (res && res.status === 200) cache.put(req, res.clone()).catch(() => {});
      return res;
    });
    const saved = await cache.match(req);
    if (!saved) return network;
    const slow = new Promise(resolve => setTimeout(() => resolve(saved), WAIT_MS));
    return Promise.race([network.catch(() => saved), slow]);
  })());
});
