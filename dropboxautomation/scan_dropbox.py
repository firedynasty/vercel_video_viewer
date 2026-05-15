#!/usr/bin/env python3
"""Scan a Dropbox folder recursively and generate playlist .txt files.

Mirrors the Dropbox subfolder hierarchy into playlists/:
  dropbox:/videos/basketball/          -> playlists/basketball/scanned.txt
  dropbox:/videos/basketball/latest/   -> playlists/basketball/latest.txt
  dropbox:/videos/basketball/twitter/  -> playlists/basketball/twitter.txt

Each .txt contains one Dropbox URL per line. generate_playlists.py derives
video names from the URL automatically.

Usage:
  python scan_dropbox.py dropbox:/videos/basketball
  python scan_dropbox.py dropbox:/videos/basketball --dry-run
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

VIDEO_EXTS = {'.mp4', '.webm', '.ogg', '.mov', '.avi', '.mkv', '.m4v'}


def rclone(*args):
    result = subprocess.run(['rclone'] + list(args), capture_output=True, text=True)
    if result.returncode != 0:
        print(f"rclone error: {result.stderr.strip()}", file=sys.stderr)
        return None
    return result.stdout.strip()


def rclone_cat(remote_path):
    """Read contents of a remote text file."""
    return rclone('cat', remote_path)


def list_files(remote_path):
    output = rclone('lsf', '-R', '--files-only', remote_path)
    if output is None:
        return []
    return [f for f in output.splitlines() if f.strip()]


def derive_name(filename):
    """Derive display name from filename (strip extension, clean up)."""
    name = Path(filename).stem
    # If it ends with .mp4 (like file.mp4.txt), strip that too
    if name.lower().endswith('.mp4'):
        name = name[:-4]
    # Remove commas — they break the name,url CSV parsing
    name = name.replace(',', '')
    return name


def get_link(remote_path):
    link = rclone('link', remote_path)
    if link:
        if 'dl=0' in link:
            link = link.replace('dl=0', 'raw=1')
        elif '?' in link:
            link += '&raw=1'
        else:
            link += '?raw=1'
    return link


def normalize_dropbox_path(path):
    if path.startswith('dropbox:'):
        return path.rstrip('/')
    if path.startswith('/'):
        return f'dropbox:{path}'.rstrip('/')
    return f'dropbox:/{path}'.rstrip('/')


def main():
    parser = argparse.ArgumentParser(description='Scan Dropbox folder and generate playlist .txt files')
    parser.add_argument('path', help='Dropbox path (e.g. dropbox:/videos/basketball)')
    parser.add_argument('--dry-run', action='store_true', help='List files without getting links')
    args = parser.parse_args()

    remote = normalize_dropbox_path(args.path)
    folder_name = remote.split('/')[-1] + '_scanned'

    print(f'Scanning {remote} ...')
    all_files = list_files(remote)

    video_files = [f for f in all_files if Path(f).suffix.lower() in VIDEO_EXTS]
    txt_files = [f for f in all_files if f.lower().endswith('.txt')]

    # Build lookup: video_path -> txt file path (for companion .txt files)
    # e.g. "twitter/Danny Cooper - BUMPS... [123].mp4.txt" matches "twitter/Danny Cooper - BUMPS... [123].mp4"
    # and  "twitter/Coach - nice.txt" matches "twitter/Coach - nice.mp4"
    txt_lookup = {}
    companion_txts = set()
    for t in txt_files:
        if t.lower().endswith('.mp4.txt'):
            video_path = t[:-4]  # strip .txt
            txt_lookup[video_path] = t
            companion_txts.add(t)
        else:
            stem = t[:-4]  # strip .txt
            for ext in VIDEO_EXTS:
                candidate = stem + ext
                if candidate in video_files:
                    txt_lookup[candidate] = t
                    companion_txts.add(t)

    # Standalone .txt files (no matching video)
    standalone_txts = [t for t in txt_files if t not in companion_txts]

    print(f'Found {len(video_files)} video(s), {len(companion_txts)} companion txt(s), {len(standalone_txts)} standalone txt(s) out of {len(all_files)} total files\n')

    if not video_files and not standalone_txts:
        print('No videos or text files found.')
        return 1

    # Group by subfolder: root files -> "scanned", subfolder/ -> subfolder name
    # Each entry is (filepath, type) where type is 'video' or 'txt'
    grouped = {}
    for f in video_files:
        parts = f.split('/')
        if len(parts) == 1:
            grouped.setdefault('scanned', []).append((f, 'video'))
        else:
            subfolder = parts[0]
            grouped.setdefault(subfolder, []).append((f, 'video'))
    for f in standalone_txts:
        parts = f.split('/')
        if len(parts) == 1:
            grouped.setdefault('scanned', []).append((f, 'txt'))
        else:
            subfolder = parts[0]
            grouped.setdefault(subfolder, []).append((f, 'txt'))

    if args.dry_run:
        for group_name, entries in sorted(grouped.items()):
            txt_path = f'playlists/{folder_name}/{group_name}.txt'
            vids = [f for f, t in entries if t == 'video']
            txts = [f for f, t in entries if t == 'txt']
            print(f'--- {txt_path} ({len(vids)} videos, {len(txts)} texts)')
            for f, ftype in entries:
                print(f'  [{ftype}] {f}')
            print()
        total_entries = sum(len(e) for e in grouped.values())
        print(f'Total: {total_entries} entries across {len(grouped)} file(s)')
        return 0

    # Generate links and write .txt files (always relative to project root)
    project_root = Path(__file__).resolve().parent.parent
    base_dir = str(project_root / 'playlists' / folder_name)
    os.makedirs(base_dir, exist_ok=True)

    total = sum(len(e) for e in grouped.values())
    count = 0

    for group_name, entries in sorted(grouped.items()):
        output_path = f'{base_dir}/{group_name}.txt'
        print(f'--- {group_name} ({len(entries)} entries) -> {output_path}')

        lines = []
        for f, ftype in entries:
            count += 1
            file_remote = f'{remote}/{f}'

            if ftype == 'video':
                print(f'  [{count}/{total}] {f} ...', end=' ', flush=True)
                link = get_link(file_remote)
                if link:
                    name = derive_name(f.split('/')[-1])
                    lines.append(f'{name},{link}')
                    # Check for companion .txt with timestamps
                    if f in txt_lookup:
                        txt_remote = f'{remote}/{txt_lookup[f]}'
                        timestamps = rclone_cat(txt_remote)
                        if timestamps and timestamps.strip():
                            lines.append(f'{name},{timestamps.strip()}')
                            print('ok (+timestamps)')
                        else:
                            print('ok')
                    else:
                        print('ok')
                else:
                    print('FAILED')

            elif ftype == 'txt':
                print(f'  [{count}/{total}] {f} (text) ...', end=' ', flush=True)
                contents = rclone_cat(file_remote)
                if contents and contents.strip():
                    name = derive_name(f.split('/')[-1])
                    lines.append(f'{name},{contents.strip()}')
                    print('ok')
                else:
                    print('empty, skipped')

        with open(output_path, 'w', encoding='utf-8') as out:
            out.write('\n'.join(lines) + '\n')
        print(f'  Wrote {len(lines)} entries to {output_path}\n')

    print(f'Done. Run: python generate_playlists.py')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
