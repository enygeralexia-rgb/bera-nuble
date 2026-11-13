const CACHE_NAME = "bera-demo-v1";
const SHELL_ASSETS = [
  "/",
  "/static/css/styles.css",
  "/static/js/api.js",
  "/static/js/app.js",
  "/static/js/views/home.js",
  "/static/js/views/mobility.js",
  "/static/js/views/jobs.js",
  "/static/js/views/ventures.js",
  "/static/js/views/profile.js",
  "/static/js/views/admin.js",
  "/static/assets/icon.svg",
  "/manifest.json"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.url.includes("/api/")) {
    event.respondWith(
      fetch(event.request).catch(() =>
        new Response(JSON.stringify({ detail: "Sin conexión a internet. Revisa tu red e intenta nuevamente." }), {
          status: 503,
          headers: { "Content-Type": "application/json" }
        })
      )
    );
    return;
  }
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
