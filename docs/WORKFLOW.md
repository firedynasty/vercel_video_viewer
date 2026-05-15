# Video Upload & Playlist Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ~/Downloads/forsort/                          │
│                     (unsorted downloaded videos)                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
              Right-click            Terminal
              (Automator)          (manual rclone)
                    │                     │
                    ▼                     ▼
         ┌──────────────────┐   ┌──────────────────────────┐
         │ Choose folder    │   │ rclone copy file.mp4     │
         │ from cached list │   │   dropbox:/videos/basketball │
         │ (dbrefresh)      │   │                          │
         └────────┬─────────┘   │ rcloned file.mp4         │
                  │             │   dropbox:/videos/basketball │
                  │             │   (copy + get link)       │
                  ▼             └────────────┬──────────────┘
         ┌──────────────────┐               │
         │ rclone copy      │               │
         │ file → dropbox   │               │
         └────────┬─────────┘               │
                  │                         │
                  └────────────┬────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Dropbox /videos/                                │
│                                                                     │
│  basketball/          running/          cooking/         ...        │
│  ├── drills/          ├── warmup.mp4    ├── recipe1.mp4             │
│  ├── highlights/      ├── sprints.mp4   └── recipe2.mp4             │
│  ├── plays/           └── form.mp4                                  │
│  ├── twitter/                                                       │
│  └── individual/                                                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
              ┌────────────────┴────────────────┐
              │                                 │
       OPTION A: Scan              OPTION B: Retrieve         OPTION C: Manual
       (entire directory)          (links to clipboard)       (single entry)
              │                           │                         │
              ▼                           ▼                         ▼
┌───────────────────────────┐ ┌─────────────────────────┐ ┌────────────────────────┐
│ python scan_dropbox.py    │ │ retrievedb              │ │ rcloned file.mp4       │
│   dropbox:/videos/basketball │ │  dropbox:/videos/       │ │   dropbox:/videos/...  │
│                           │ │  basketball/twitter     │ │  → link to clipboard   │
│ Scans all videos + .txt   │ │                         │ │                        │
│ Gets links automatically  │ │ Gets all links for a    │ │ Paste link into:       │
│ Writes to:                │ │ folder → clipboard      │ │  playlists/basketball/ │
│   playlists/              │ │                         │ │  main.txt              │
│     basketball_scanned/   │ │ Paste into:             │ │                        │
│       scanned.txt         │ │  playlists/folder/      │ │ Format:                │
│       drills.txt          │ │  sample.txt             │ │  name,https://dropbox  │
│       plays.txt           │ │                         │ │  name,0:28(label)      │
│       twitter.txt         │ └────────────┬────────────┘ └───────────┬────────────┘
│       ...                 │              │                          │
└─────────────┬─────────────┘              │                          │
              │
              └────────────────┬──────────────────┬───────────────────┘
                               │                  │
                               └────────┬─────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     playlists/ directory                             │
│                                                                     │
│  basketball/              basketball_scanned/        twitter/        │
│  ├── main.txt  (manual)   ├── scanned.txt           ├── sample.txt  │
│  └── youtube.txt          ├── drills.txt                            │
│                           ├── plays.txt             cooking/        │
│  Format:                  ├── highlights.txt        ├── cooking.txt  │
│  name,url                 └── twitter.txt                           │
│  name,0:28(label)                                                   │
│                                                                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              python generate_playlists.py                            │
│                                                                     │
│  Reads all playlists/**/*.txt                                       │
│  Outputs: public/playlists.json                                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          Deploy                                      │
│                                                                     │
│  rclone copy public/playlists.json dropbox:/vercel                  │
│  rclone link dropbox:/vercel/playlists.json                         │
│  vercel env update DROPBOX_PLAYLISTS_URL                            │
└─────────────────────────────────────────────────────────────────────┘
```

## Quick Reference

| Command | What it does |
|---------|-------------|
| `dbrefresh dropbox:/videos/basketball` | Cache folder list for Automator picker |
| `rcloned file.mp4 dropbox:/videos/basketball` | Upload + get link to clipboard |
| `rclone copy file.mp4 dropbox:/videos/basketball` | Upload only (no link) |
| `retrievedb dropbox:/videos/basketball/twitter` | Get all links for a folder → clipboard |
| `python dropboxautomation/scan_dropbox.py dropbox:/videos/basketball` | Scan entire folder → generate playlist .txt files |
| `python generate_playlists.py` | Build playlists.json from all .txt files |
| Right-click → Quick Actions → Upload to Dropbox | Automator: pick folder + upload |
