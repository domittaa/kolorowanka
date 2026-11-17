// Dziala offline: zapisuje cala aplikacje i obrazki w pamieci podrecznej.
const VERSION = 'kolorowanka-v7';
const SHELL = ['./', 'index.html', 'style.css', 'app.js', 'photo-worker.js', 'manifest.webmanifest',
  'icons/icon-180.png', 'icons/icon-192.png', 'icons/icon-512.png', 'pictures/index.json'];

self.addEventListener('install', (e) => {
  e.waitUntil((async () => {
    const c = await caches.open(VERSION);
    await c.addAll(SHELL);
    try {
      const list = await (await fetch('pictures/index.json', { cache: 'no-cache' })).json();
      const files = [];
      list.forEach((p) => files.push(`pictures/${p.id}.json`, `pictures/${p.id}.jpg`));
      await c.addAll(files);
    } catch (err) { /* obrazki dociagna sie przy pierwszym otwarciu */ }
    self.skipWaiting();
  })());
});

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== VERSION) await caches.delete(k);
    await self.clients.claim();
  })());
});

// Aplikacja i lista obrazkow: najpierw siec (zeby aktualizacje docieraly), bez sieci - pamiec.
// Obrazki: od razu z pamieci, w tle odswiezane.
self.addEventListener('fetch', (e) => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== location.origin) return;
  const isAsset = /\/(pictures|icons)\//.test(url.pathname) && !url.pathname.endsWith('index.json');
  e.respondWith((async () => {
    const c = await caches.open(VERSION);
    if (isAsset) {
      const hit = await c.match(req, { ignoreSearch: true });
      const net = fetch(req).then((res) => { if (res.ok) c.put(req, res.clone()); return res; }).catch(() => null);
      if (hit) { e.waitUntil(net); return hit; }
      return (await net) || Response.error();
    }
    try {
      const res = await fetch(req, { cache: 'no-cache' });
      if (res.ok) c.put(req, res.clone());
      return res;
    } catch (err) {
      const hit = await c.match(req, { ignoreSearch: true });
      if (hit) return hit;
      if (req.mode === 'navigate') return (await c.match('index.html')) || Response.error();
      return Response.error();
    }
  })());
});
