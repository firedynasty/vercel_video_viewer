var CACHE_NAME = 'video-cache-v1';

self.addEventListener('install', function() {
    self.skipWaiting();
});

self.addEventListener('activate', function(event) {
    event.waitUntil(self.clients.claim());
});

// Intercept fetch requests — serve cached videos if available
self.addEventListener('fetch', function(event) {
    var url = event.request.url;

    // Only cache video requests (Dropbox raw links and common video extensions)
    if (!isVideoRequest(url)) return;

    event.respondWith(
        caches.open(CACHE_NAME).then(function(cache) {
            return cache.match(event.request).then(function(cached) {
                if (cached) return cached;
                return fetch(event.request).then(function(response) {
                    // Only cache successful responses
                    if (response.ok) {
                        cache.put(event.request, response.clone());
                    }
                    return response;
                });
            });
        })
    );
});

function isVideoRequest(url) {
    var lower = url.toLowerCase();
    // Dropbox raw links
    if (lower.indexOf('dropbox.com') !== -1 && lower.indexOf('raw=1') !== -1) return true;
    // Common video extensions
    var exts = ['.mp4', '.webm', '.ogg', '.mov', '.m4v'];
    for (var i = 0; i < exts.length; i++) {
        if (lower.indexOf(exts[i]) !== -1) return true;
    }
    return false;
}

// Handle messages from the main page
self.addEventListener('message', function(event) {
    var msg = event.data;

    if (msg.type === 'PRECACHE_VIDEO') {
        // Download and cache a video URL
        caches.open(CACHE_NAME).then(function(cache) {
            var request = new Request(msg.url);
            cache.match(request).then(function(existing) {
                if (existing) {
                    // Already cached
                    notifyClient(event.source, { type: 'PRECACHE_DONE', url: msg.url, alreadyCached: true });
                    return;
                }
                fetch(request).then(function(response) {
                    if (response.ok) {
                        cache.put(request, response.clone());
                        notifyClient(event.source, { type: 'PRECACHE_DONE', url: msg.url, size: parseInt(response.headers.get('content-length') || '0') });
                    } else {
                        notifyClient(event.source, { type: 'PRECACHE_ERROR', url: msg.url, error: 'HTTP ' + response.status });
                    }
                }).catch(function(err) {
                    notifyClient(event.source, { type: 'PRECACHE_ERROR', url: msg.url, error: err.message });
                });
            });
        });
    }

    if (msg.type === 'DELETE_CACHED') {
        caches.open(CACHE_NAME).then(function(cache) {
            cache.delete(new Request(msg.url)).then(function(deleted) {
                notifyClient(event.source, { type: 'DELETE_DONE', url: msg.url, deleted: deleted });
            });
        });
    }

    if (msg.type === 'CLEAR_ALL_CACHE') {
        caches.delete(CACHE_NAME).then(function() {
            notifyClient(event.source, { type: 'CLEAR_ALL_DONE' });
        });
    }

    if (msg.type === 'GET_CACHE_STATUS') {
        caches.open(CACHE_NAME).then(function(cache) {
            cache.keys().then(function(keys) {
                var urls = keys.map(function(r) { return r.url; });
                notifyClient(event.source, { type: 'CACHE_STATUS', urls: urls });
            });
        });
    }
});

function notifyClient(client, msg) {
    if (client) {
        client.postMessage(msg);
    }
}
