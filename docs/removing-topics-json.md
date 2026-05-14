# Removing topics.json — Deriving State from a Single Source of Truth

## The Problem

The app had two JSON files synced to Dropbox:

```
playlists.json   — nested object: { "Home": { category: [...] }, "Basketball": { ... }, ... }
topics.json      — flat array:    ["Home", "Basketball", "Chess", ...]
```

This meant:
- **Two files** to generate, sync, and keep in agreement
- **Two Dropbox shared links** to manage (and if either broke, the app broke)
- **Two env vars** on Vercel (`DROPBOX_PLAYLISTS_URL`, `DROPBOX_TOPICS_URL`)

## The Insight

`topics.json` was always just the top-level keys of `playlists.json`:

```js
// topics.json
["Home", "Basketball", "Chess", "Cooking"]

// playlists.json
{
  "Home":       { ... },
  "Basketball": { ... },
  "Chess":      { ... },
  "Cooking":    { ... }
}

// So topics === Object.keys(playlists)
```

When one piece of data is always derivable from another, storing both is redundant. The derived copy can go stale, diverge, or break independently — all risk with no benefit.

## The Fix

**Before:** Two files, two fetches, two env vars.

```
generate_playlists.py  →  playlists.json + topics.json
rclone copy playlists.json dropbox:/vercel
rclone copy topics.json    dropbox:/vercel

Frontend:
  fetch topics.json    → build topic menu
  fetch playlists.json → load video data
```

**After:** One file, one fetch, one env var.

```
generate_playlists.py  →  playlists.json
rclone copy playlists.json dropbox:/vercel

Frontend:
  fetch playlists.json → Object.keys() builds the topic menu
```

### What changed in the code

**Python (`generate_playlists.py`):** Removed the block that wrote `topics.json`.

**API (`api/playlists.js`):** Simplified to one env var — `DROPBOX_PLAYLISTS_URL`. The frontend calls `/api/playlists` and the proxy fetches from Dropbox.

**Frontend (`index.html`):**

```js
// Before: separate fetch for topics
async function loadTopics() {
    var res = await fetchWithFallback('topics', 'topics.json');
    var topics = await res.json();
    // ... build menu from topics array
}

// After: derive topics from playlists keys
function buildTopicMenu() {
    var topics = Object.keys(_allPlaylists);
    // ... build menu from derived array
}
```

## The General Principle

> If data B is always derivable from data A, don't store B. Compute it.

This applies broadly:
- Don't cache what you can cheaply recompute
- Don't sync two files when one contains the other
- Don't maintain a separate index if the data structure already implies the index

The cost of a redundant source is not just storage — it's the operational burden of keeping two things in sync and the debugging cost when they diverge.
