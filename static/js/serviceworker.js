const CACHE_NAME = 'storems-v1.0.0';
const urlsToCache = [
  '/',
  '/accounts/login/',
  '/static/css/tailwind.css',
  '/static/js/serviceworker.js',
  '/static/images/icons/icon-192x192.png',
  '/static/images/icons/icon-512x512.png',
  // เพิ่ม static files อื่นๆ ที่ต้องการ cache
];

// Install Event
self.addEventListener('install', function(event) {
  console.log('Service Worker: Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('Service Worker: Caching files');
        return cache.addAll(urlsToCache);
      })
      .then(function() {
        console.log('Service Worker: Install complete');
        return self.skipWaiting();
      })
  );
});

// Activate Event
self.addEventListener('activate', function(event) {
  console.log('Service Worker: Activating...');
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          if (cacheName !== CACHE_NAME) {
            console.log('Service Worker: Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(function() {
      console.log('Service Worker: Activation complete');
      return self.clients.claim();
    })
  );
});

// Fetch Event
self.addEventListener('fetch', function(event) {
  // เฉพาะ GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        // ถ้ามีใน cache ให้ return
        if (response) {
          return response;
        }

        // ถ้าไม่มีใน cache ให้ fetch และ cache
        return fetch(event.request).then(
          function(response) {
            // ตรวจสอบ response ว่าถูกต้อง
            if(!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }

            // Clone response สำหรับ cache
            var responseToCache = response.clone();

            caches.open(CACHE_NAME)
              .then(function(cache) {
                // Cache เฉพาะ static files
                if (event.request.url.includes('/static/') || event.request.url === self.location.origin + '/') {
                  cache.put(event.request, responseToCache);
                }
              });

            return response;
          }
        );
      }).catch(function() {
        // ถ้า offline และไม่มีใน cache
        if (event.request.destination === 'document') {
          return caches.match('/');
        }
      })
    );
});
