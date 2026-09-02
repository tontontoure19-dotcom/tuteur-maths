// Service worker minimal : permet l'installation sur l'écran d'accueil
// et garde l'interface disponible même avec une connexion faible.
// Les réponses de l'IA (/api/) ne sont jamais mises en cache.
// Changer ce numéro force tous les téléphones à récupérer la nouvelle version.
const CACHE = 'tuteur-v28';
const FICHIERS = ['./', './index.html', './manifest.json', './icone.svg'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FICHIERS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(cles => Promise.all(cles.filter(c => c !== CACHE).map(c => caches.delete(c))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.pathname.startsWith('/api/')) return;
  // Réseau d'abord (pour recevoir les mises à jour), cache en secours.
  e.respondWith(
    fetch(e.request)
      .then(r => {
        const copie = r.clone();
        caches.open(CACHE).then(c => c.put(e.request, copie));
        return r;
      })
      .catch(() => caches.match(e.request))
  );
});
