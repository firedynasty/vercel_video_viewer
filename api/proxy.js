// Proxy Dropbox video URLs server-side so the browser can fetch() them
// (Dropbox blocks direct JS fetch due to missing CORS headers, but <video> works fine).
// Only Dropbox URLs are allowed.

export const config = {
    maxDuration: 300,
};

export default async function handler(req, res) {
    const { url } = req.query;

    if (!url) return res.status(400).end('Missing ?url=');

    // Security: only proxy Dropbox URLs
    let parsed;
    try { parsed = new URL(url); } catch (e) { return res.status(400).end('Invalid URL'); }
    if (!parsed.hostname.endsWith('dropbox.com') && !parsed.hostname.endsWith('dropboxusercontent.com')) {
        return res.status(403).end('Only Dropbox URLs are allowed');
    }

    let upstream;
    try {
        upstream = await fetch(url, { redirect: 'follow' });
    } catch (e) {
        return res.status(502).end('Upstream fetch failed: ' + e.message);
    }

    res.status(upstream.status);
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, HEAD');

    const contentType = upstream.headers.get('content-type');
    if (contentType) res.setHeader('Content-Type', contentType);
    const contentLength = upstream.headers.get('content-length');
    if (contentLength) res.setHeader('Content-Length', contentLength);
    // Don't cache the proxy response itself
    res.setHeader('Cache-Control', 'no-store');

    // Stream the body
    if (upstream.body) {
        const { Readable } = await import('stream');
        Readable.fromWeb(upstream.body).pipe(res);
    } else {
        res.end();
    }
}
