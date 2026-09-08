const CACHE = "raahsetu-shell-v2";
const SHELL = ["/", "/index.html", "/manifest.webmanifest", "/favicon.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key.startsWith('raahsetu-shell-') && key !== CACHE).map((key) => caches.delete(key)))));
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin || request.headers.has('Authorization')) return;
  // Allow only the public app shell and generated assets. API data is network-only.
  if (url.search || !(SHELL.includes(url.pathname) || /^\/assets\/[^/]+\.(js|css|woff2?|png|svg)$/.test(url.pathname))) return;
  if (request.mode === "navigate") {
    event.respondWith(fetch(request).then((response) => {
      const copy = response.clone();
      if (response.ok) event.waitUntil(caches.open(CACHE).then((cache) => cache.put("/index.html", copy)));
      return response;
    }).catch(async () => (await caches.match("/index.html")) || Response.error()));
    return;
  }
  event.respondWith(caches.match(request).then((cached) => cached || fetch(request).then((response) => {
    if (response.ok) {
      const copy = response.clone();
      event.waitUntil(caches.open(CACHE).then((cache) => cache.put(request, copy)));
    }
    return response;
  })));
});
