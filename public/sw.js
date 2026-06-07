var CACHE_NAME = 'video-cache-v1';

self.addEventListener('install', function() {
    self.skipWaiting();
});

self.addEventListener('activate', function(event) {
    event.waitUntil(self.clients.claim());
});

// Serve from cache ONLY if we have a cached copy.
// Never intercept uncached requests — let the browser handle them normally.
// This avoids breaking cross-origin Dropbox requests, range requests, etc.
self.addEventListener('fetch', function(event) {
    var url = event.request.url;
    if (!isVideoRequest(url)) return;

    event.respondWith(
        caches.open(CACHE_NAME).then(function(cache) {
            return cache.match(event.request, { ignoreSearch: true }).then(function(cached) {
                if (cached) return cached;
                // No cache hit — pass through to network without interfering
                return fetch(event.request);
            });
        }).catch(function() {
            // If anything fails, fall through to normal network
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

// Handle messages from the main page
self.addEventListener('message', function(event) {
    var msg = event.data;

    if (msg.type === 'PRECACHE_VIDEO') {
        caches.open(CACHE_NAME).then(function(cache) {
            // Check by URL ignoring query string differences
            cache.match(new Request(msg.url), { ignoreSearch: true }).then(function(existing) {
                if (existing) {
                    notifyClient(event.source, { type: 'PRECACHE_DONE', url: msg.url, alreadyCached: true });
                    return;
                }
                // Fetch with no-cors to handle cross-origin Dropbox URLs
                fetch(msg.url, { mode: 'no-cors' }).then(function(response) {
                    // Opaque responses (type === 'opaque') have status 0,
                    // but are still valid and cacheable
                    if (response.ok || response.type === 'opaque') {
                        cache.put(msg.url, response.clone());
                        notifyClient(event.source, {
                            type: 'PRECACHE_DONE',
                            url: msg.url,
                            size: parseInt(response.headers.get('content-length') || '0')
                        });
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
            cache.delete(new Request(msg.url), { ignoreSearch: true }).then(function(deleted) {
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
