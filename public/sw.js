// Service worker exists solely to enable Cache API access from the main page.
// Video playback uses blob URLs resolved from the cache in the main thread,
// so no fetch interception is needed here.

var CACHE_NAME = 'video-cache-v1';

self.addEventListener('install', function() {
    self.skipWaiting();
});

self.addEventListener('activate', function(event) {
    event.waitUntil(self.clients.claim());
});
