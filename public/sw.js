var CACHE_NAME = 'video-cache-v1';

self.addEventListener('install', function() {
    self.skipWaiting();
});

self.addEventListener('activate', function(event) {
    event.waitUntil(self.clients.claim());
});

// Serve cached videos if available, otherwise pass through to network
self.addEventListener('fetch', function(event) {
    var url = event.request.url;
    if (!isVideoRequest(url)) return;

    event.respondWith(
        caches.open(CACHE_NAME).then(function(cache) {
            return cache.match(event.request, { ignoreSearch: true }).then(function(cached) {
                if (cached) return cached;
                return fetch(event.request);
            });
        }).catch(function() {
            return fetch(event.request);
        })
    );
});

function isVideoRequest(url) {
    var lower = url.toLowerCase();
    if (lower.indexOf('dropbox.com') !== -1) return true;
    var exts = ['.mp4', '.webm', '.ogg', '.mov', '.m4v'];
    for (var i = 0; i < exts.length; i++) {
        if (lower.indexOf(exts[i]) !== -1) return true;
    }
    return false;
}
