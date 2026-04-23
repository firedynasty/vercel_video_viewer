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
                # Simple format: name,url
                parts = line.split(',', 1)
                if len(parts) == 2:
                    name = parts[0].strip()
                    url = parts[1].strip()
                else:
                    url = parts[0].strip()
                    name = ''
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
                        help='Specific input folder (default: auto-scan all playlists*/ dirs)')
    parser.add_argument('-o', '--output', default=None,
                        help='Output JSON file (default: auto-derived from input folder name)')
    args = parser.parse_args()

    if args.input:
        # Process a single specified directory
        input_dir = Path(args.input)
        if args.output:
            output_path = args.output
        else:
            # Derive output: playlists/ -> public/playlists.json
            output_path = f'./public/{input_dir.name}.json'
        print(f'Processing {input_dir}:')
        success = process_playlist_dir(input_dir, output_path)
        return 0 if success else 1

    # Auto-scan: find all playlists*/ directories
    base = Path('.')
    playlist_dirs = sorted(base.glob('playlists*/'))
    playlist_dirs = [d for d in playlist_dirs if d.is_dir() and not d.name.startswith('.')]

    if not playlist_dirs:
        print('No playlists*/ directories found.')
        return 1

    total = 0
    for pdir in playlist_dirs:
        output_path = f'./public/{pdir.name}.json'
        print(f'Processing {pdir}/:')
        if process_playlist_dir(pdir, output_path):
            total += 1

    print(f'\nDone. Processed {total} playlist directory(ies).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
