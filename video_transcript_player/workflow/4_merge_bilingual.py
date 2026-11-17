#!/usr/bin/env python3
"""
Merge two SRTs with matching cues into one bilingual SRT (first file's text on top).

Usage:
    python3 4_merge_bilingual.py -a chinese.srt -b english.srt -o chinese_english.srt
"""

import argparse
import re


def parse_srt(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read().replace('\r', '')
    cues = []
    for block in re.split(r'\n\s*\n', content.strip()):
        lines = block.strip().split('\n')
        idx = next((i for i, l in enumerate(lines) if '-->' in l), -1)
        if idx == -1:
            continue
        cues.append((lines[idx].strip(), '\n'.join(lines[idx + 1:]).strip()))
    return cues


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-a", required=True, help="SRT whose text goes on top (e.g. Chinese)")
    p.add_argument("-b", required=True, help="SRT whose text goes below (e.g. English)")
    p.add_argument("-o", required=True, help="Output SRT")
    args = p.parse_args()

    a, b = parse_srt(args.a), parse_srt(args.b)
    if len(a) != len(b):
        print(f"Warning: cue counts differ ({len(a)} vs {len(b)}); merging the first {min(len(a), len(b))}")

    with open(args.o, 'w', encoding='utf-8') as f:
        for i, ((ts, ta), (_, tb)) in enumerate(zip(a, b), 1):
            f.write(f"{i}\n{ts}\n{ta}\n{tb}\n\n")
    print(f"Done: {args.o}")


if __name__ == "__main__":
    main()
