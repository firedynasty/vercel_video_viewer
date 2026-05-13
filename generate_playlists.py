#!/usr/bin/env python3
"""Generate playlist JSON files from .txt files in playlist folders.

Scans for directories matching playlists*/ and generates corresponding JSON:
  playlists/        -> public/playlists.json
  playlists_chinese/ -> public/playlists_chinese.json
  playlists_recipes/ -> public/playlists_recipes.json

Each .txt file within a folder becomes a category (filename stem = key).
Each line in a .txt file: name, URL
"""

import argparse
import glob
import json
import os
import re
from pathlib import Path


def parse_playlist_file(filepath):
    entries = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # Check for quoted value: name,"url,time1,time2(label),..."
            m = re.match(r'^([^,]*),\s*"(.+)"$', line)
            if m:
                name = m.group(1).strip()
                inner = m.group(2).strip()
                # First item is URL, rest are times
                parts = [p.strip() for p in inner.split(',')]
                url = parts[0]
                times = []
                for t in parts[1:]:
                    if not t:
                        continue
                    # Parse time with optional label: 4:18(floater) or 0:07
                    tm = re.match(r'^([\d:]+)\s*(?:\(([^)]*)\))?(.*)$', t)
                    if tm:
                        time_str = tm.group(1)
                        label = (tm.group(2) or '').strip()
                        # Check for trailing text after the parenthetical
                        trailing = (tm.group(3) or '').strip()
                        entry = {'time': time_str}
                        if label:
                            entry['label'] = label
                        if trailing:
                            entry['note'] = trailing
                        times.append(entry)
                    else:
                        # Not a time — treat as a note/text
                        pass
            else:
                # Simple format: name,url  OR  name,time1,time2,...
                parts = line.split(',', 1)
                if len(parts) == 2:
                    name = parts[0].strip()
                    rest = parts[1].strip()
                else:
                    rest = parts[0].strip()
                    name = ''
                # Check if rest is timestamps (no URL) — e.g. "0:07,0:18,1:13(label)"
                # A URL starts with http(s):// or / or contains a dot before any colon
                is_url = bool(re.match(r'^https?://', rest) or re.match(r'^/', rest))
                if not is_url and re.match(r'^\d{1,2}:\d{2}', rest):
                    # This line is timestamps for a previous entry with the same name
                    time_parts = [p.strip() for p in rest.split(',')]
                    times = []
                    for t in time_parts:
                        if not t:
                            continue
                        tm = re.match(r'^([\d:]+)\s*(?:\(([^)]*)\))?(.*)$', t)
                        if tm:
                            time_str = tm.group(1)
                            label = (tm.group(2) or '').strip()
                            trailing = (tm.group(3) or '').strip()
                            tentry = {'time': time_str}
                            if label:
                                tentry['label'] = label
                            if trailing:
                                tentry['note'] = trailing
                            times.append(tentry)
                    if times and name:
                        # Merge into existing entry with same name
                        merged = False
                        for existing in entries:
                            if existing['name'] == name:
                                existing.setdefault('times', []).extend(times)
                                merged = True
                                break
                        if not merged:
                            # No matching entry found — skip (times without a video)
                            pass
                    continue
                url = rest
                times = []
            if not url:
                continue
            if not name:
                # Derive name from URL
                name = url.rstrip('/').split('/')[-1]
                name = name.split('?')[0]
                if '.' in name:
                    name = name.rsplit('.', 1)[0]
                name = name.replace('_', ' ').replace('-', ' ').strip()
            entry = {'name': name, 'url': url}
            if times:
                entry['times'] = times
            entries.append(entry)
    return entries


def process_playlist_dir(input_dir, output_path):
    """Process a single playlist directory into a JSON file."""
    input_dir = Path(input_dir)
    if not input_dir.is_dir():
        return False

    txt_files = sorted(input_dir.glob('*.txt'))
    if not txt_files:
        print(f'  No .txt files found in {input_dir}')
        return False

    playlists = {}
    for txt_file in txt_files:
        category = txt_file.stem
        entries = parse_playlist_file(txt_file)
        playlists[category] = entries
        print(f'    {category}: {len(entries)} video(s)')

    # Ensure output directory exists
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(playlists, f, indent=2, ensure_ascii=False)

    print(f'  -> Wrote {len(playlists)} categories to {output_path}')
    return True


def main():
    parser = argparse.ArgumentParser(description='Generate playlist JSON files from .txt folders')
    parser.add_argument('-i', '--input', default=None,
                        help='Specific input folder (default: auto-scan playlists/)')
    parser.add_argument('-o', '--output', default=None,
                        help='Output JSON file (default: auto-derived from input folder name)')
    args = parser.parse_args()

    if args.input:
        input_dir = Path(args.input)
        if args.output:
            output_path = args.output
        else:
            output_path = f'./public/{input_dir.name}.json'
        print(f'Processing {input_dir}:')
        success = process_playlist_dir(input_dir, output_path)
        return 0 if success else 1

    # Process playlists/ directory structure into a single nested playlists.json:
    #   { "Home": { category: [...] }, "Chess": { category: [...] }, ... }
    # and a simple topics.json: ["Home", "Chess", ...]
    playlists_dir = Path('playlists')
    if not playlists_dir.is_dir():
        print('No playlists/ directory found.')
        return 1

    all_playlists = {}  # { topic_name: { category: [entries] } }
    topics = []  # [topic_name, ...]

    # 1) Root-level txt files -> "Home" topic
    root_txts = sorted(playlists_dir.glob('*.txt'))
    if root_txts:
        print('Processing playlists/ (root) -> Home:')
        categories = {}
        for txt_file in root_txts:
            category = txt_file.stem
            entries = parse_playlist_file(txt_file)
            categories[category] = entries
            print(f'    {category}: {len(entries)} video(s)')
        all_playlists['Home'] = categories
        topics.append('Home')

    # 2) Each subfolder -> its own topic
    subdirs = sorted([d for d in playlists_dir.iterdir()
                      if d.is_dir() and not d.name.startswith('.')])
    for subdir in subdirs:
        label = subdir.name.replace('_', ' ').replace('-', ' ').title()
        print(f'Processing playlists/{subdir.name}/ -> {label}:')
        txt_files = sorted(subdir.glob('*.txt'))
        if not txt_files:
            print(f'  No .txt files found')
            continue
        categories = {}
        for txt_file in txt_files:
            category = txt_file.stem
            entries = parse_playlist_file(txt_file)
            categories[category] = entries
            print(f'    {category}: {len(entries)} video(s)')
        all_playlists[label] = categories
        topics.append(label)

    # 3) Write single playlists.json
    playlists_path = Path('./public/playlists.json')
    playlists_path.parent.mkdir(parents=True, exist_ok=True)
    with open(playlists_path, 'w', encoding='utf-8') as f:
        json.dump(all_playlists, f, indent=2, ensure_ascii=False)
    print(f'\n-> Wrote {len(all_playlists)} topic(s) to {playlists_path}')

    # 4) Write topics.json (simple list)
    topics_path = Path('./public/topics.json')
    with open(topics_path, 'w', encoding='utf-8') as f:
        json.dump(topics, f, indent=2, ensure_ascii=False)
    print(f'-> Wrote {len(topics)} topic(s) to {topics_path}')

    print(f'Done. Processed {len(all_playlists)} topic(s).')

    # Print rclone commands to sync to Dropbox
    base = Path(__file__).resolve().parent / 'public'
    print(f'\nrclone copy {base / "playlists.json"}  dropbox:/vercel && rclone copy {base / "topics.json"}  dropbox:/vercel')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
