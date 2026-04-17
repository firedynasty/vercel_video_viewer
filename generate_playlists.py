#!/usr/bin/env python3
"""Generate playlists.json from .txt files in a folder.

Each .txt file becomes a category (filename stem = key).
Each line in a .txt file: name, URL
"""

import argparse
import json
import os
from pathlib import Path


def parse_playlist_file(filepath):
    entries = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # Split on first comma
            parts = line.split(',', 1)
            if len(parts) == 2:
                name = parts[0].strip()
                url = parts[1].strip()
            else:
                # Single value - treat as URL, derive name
                url = parts[0].strip()
                name = ''
            if not url:
                continue
            if not name:
                # Derive name from URL
                name = url.rstrip('/').split('/')[-1]
                name = name.split('?')[0]
                # Remove extension
                if '.' in name:
                    name = name.rsplit('.', 1)[0]
                name = name.replace('_', ' ').replace('-', ' ').strip()
            entries.append({'name': name, 'url': url})
    return entries


def main():
    parser = argparse.ArgumentParser(description='Generate playlists.json from .txt files')
    parser.add_argument('-i', '--input', default='./playlists/', help='Input folder with .txt files')
    parser.add_argument('-o', '--output', default='./public/playlists.json', help='Output JSON file')
    args = parser.parse_args()

    input_dir = Path(args.input)
    if not input_dir.is_dir():
        print(f'Error: {input_dir} is not a directory')
        return 1

    playlists = {}
    txt_files = sorted(input_dir.glob('*.txt'))

    if not txt_files:
        print(f'No .txt files found in {input_dir}')
        return 1

    for txt_file in txt_files:
        category = txt_file.stem
        entries = parse_playlist_file(txt_file)
        playlists[category] = entries
        print(f'  {category}: {len(entries)} video(s)')

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(playlists, f, indent=2, ensure_ascii=False)

    print(f'\nWrote {len(playlists)} categories to {output_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
