const STATIC_CACHE = 'subbuteo-static-v1';
const isStaticAsset = request => {
  const url = new URL(request.url);
  return url.origin === self.location.origin &&
    request.method === 'GET' &&
    (url.pathname.startsWith('/assets/') || /\.(?:js|css|png|jpg|jpeg|svg|webp|mp3|woff2?)$/i.test(url.pathname));
};

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', event => {
  const {request} = event;
  if (new URL(request.url).pathname.startsWith('/api/') || !isStaticAsset(request)) return;
  event.respondWith(caches.open(STATIC_CACHE).then(async cache => {
    const cached = await cache.match(request);
    if (cached) return cached;
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  }));
});
