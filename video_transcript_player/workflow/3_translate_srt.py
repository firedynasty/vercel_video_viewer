#!/usr/bin/env python3
"""
Step 3: Translate an SRT file to another language using GPT-4.1-mini.

Usage:
    python3 3_translate_srt.py -i <input.srt> [-o <output.srt>] [-t <target_language>]

Options:
    -i  Input SRT file (required)
    -o  Output SRT path (default: <input>_<lang>.srt)
    -t  Target language: en, zh, ko, es, ja, etc. (default: en)
    --batch-size  Lines per API call (default: 20)

Examples:
    python3 3_translate_srt.py -i chinese.srt -t en
    python3 3_translate_srt.py -i english.srt -t zh -o chinese.srt

Requires: OPENAI_API_KEY env var
"""

import argparse
import os
import re
import time
from pathlib import Path

from openai import OpenAI

BATCH_SIZE = 20
MODEL = "gpt-4.1-mini"


def parse_srt_time(ts):
    m = re.match(r'(\d+):(\d{2}):(\d{2})[,.](\d{1,3})', ts.strip())
    if not m:
        return 0
    h, mnt, s, ms = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4).ljust(3, '0'))
    return h * 3600000 + mnt * 60000 + s * 1000 + ms


def fmt_time(ms):
    h = ms // 3600000
    mnt = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    ms = ms % 1000
    return f"{h:02d}:{mnt:02d}:{s:02d},{ms:03d}"


def parse_srt(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read().replace('\r', '')
    entries = []
    blocks = re.split(r'\n\s*\n', content.strip())
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 2:
            continue
        ts_idx = next((i for i, l in enumerate(lines) if '-->' in l), -1)
        if ts_idx == -1:
            continue
        m = re.match(r'(.+?)\s*-->\s*(.+)', lines[ts_idx])
        if not m:
            continue
        start = parse_srt_time(m.group(1))
        end = parse_srt_time(m.group(2))
        text = '\n'.join(lines[ts_idx + 1:]).strip()
        if text:
            entries.append({'start': start, 'end': end, 'text': text})
    return entries


def translate_batch(client, texts, target_lang):
    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    f"You are a professional translator. "
                    f"Translate each numbered line to {target_lang}. "
                    f"Keep the same numbering. Return only the numbered translations, nothing else."
                ),
            },
            {"role": "user", "content": numbered},
        ],
    )
    raw = response.choices[0].message.content.strip()
    # Parse by actual number to prevent off-by-one shifts if GPT skips/adds lines
    translations_map = {}
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        match = re.match(r"^(\d+)\.\s*(.+)", line)
        if match:
            translations_map[int(match.group(1))] = match.group(2).strip()
    return [translations_map.get(i + 1, "") for i in range(len(texts))]


def main():
    parser = argparse.ArgumentParser(description="Translate an SRT file to another language")
    parser.add_argument("-i", "--input", required=True, help="Input SRT file")
    parser.add_argument("-o", "--output", help="Output SRT path (default: <input>_<lang>.srt)")
    parser.add_argument("-t", "--target", default="en", help="Target language code (default: en)")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help=f"Lines per API call (default: {BATCH_SIZE})")
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY is not set.")
        return

    if not os.path.exists(args.input):
        print(f"Error: File not found: {args.input}")
        return

    input_path = Path(args.input)
    output_path = args.output or str(input_path.parent / f"{input_path.stem}_{args.target}.srt")

    client = OpenAI(api_key=api_key)

    print(f"Reading: {args.input}")
    entries = parse_srt(args.input)
    print(f"  {len(entries)} cues found")

    lang_names = {
        "en": "English", "zh": "Traditional Chinese", "ko": "Korean",
        "es": "Spanish", "ja": "Japanese", "fr": "French", "de": "German",
        "pt": "Portuguese", "it": "Italian", "ru": "Russian", "ar": "Arabic",
    }
    target_lang = lang_names.get(args.target, args.target)

    results = []
    batch_size = args.batch_size
    for i in range(0, len(entries), batch_size):
        batch = entries[i: i + batch_size]
        texts = [e['text'] for e in batch]
        print(f"  Translating lines {i+1}–{min(i+batch_size, len(entries))}...")
        translations = translate_batch(client, texts, target_lang)
        for j, entry in enumerate(batch):
            results.append({**entry, 'text': translations[j]})
        time.sleep(0.2)

    with open(output_path, 'w', encoding='utf-8') as f:
        for i, entry in enumerate(results, 1):
            f.write(f"{i}\n{fmt_time(entry['start'])} --> {fmt_time(entry['end'])}\n{entry['text']}\n\n")

    print(f"Done: {output_path}")


if __name__ == "__main__":
    main()
