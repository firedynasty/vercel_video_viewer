# vercel_video_viewer

Video viewer with dynamic category playlists loaded from Dropbox-hosted JSON.

## How it works

1. The page loads `playlists.json` from Dropbox via a serverless CORS proxy
2. Each key in the JSON becomes a navbar button
3. Clicking a button loads that category's videos into the gallery

## Updating playlists

1. Edit `.txt` files in `playlists/` (format: `name, URL` per line, or just URLs)
2. Run `python3 generate_playlists.py`
3. Upload/replace `playlists.json` to **Dropbox > vercel > playlists.json**
   - Dropbox path: https://www.dropbox.com/home/vercel
   - Overwrite the same file so the share link stays the same
4. No redeploy needed — the site fetches the latest JSON from Dropbox
