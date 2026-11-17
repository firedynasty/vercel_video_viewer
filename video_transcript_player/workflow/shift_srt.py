#!/usr/bin/env python3
"""
Shift every timestamp in one or more .srt files by a delay.

Use when the audio was trimmed (e.g. starting at 21:00 of the video), so the
subtitles start at 0:00 but need to line up with the full YouTube video.

Usage:
    python3 shift_srt.py -d 21 a_zh.srt a_en.srt a_zh_en.srt
    python3 shift_srt.py -d 21:30 a_zh.srt            # 21 min 30 s
    python3 shift_srt.py -d 1:05:00 a_zh.srt          # 1 h 5 min
    python3 shift_srt.py a_zh.srt                     # no -d: asks how many minutes
    python3 shift_srt.py -d 21 a_zh.srt -o out.srt    # -o only with a single input

Delay formats (-d):
    21        -> 21 minutes (decimals ok: 0.5 = 30 s)
    21:30     -> 21 min 30 s
    1:05:00   -> 1 h 5 min 0 s
    -2        -> negative = make subtitles earlier (times clamp at 0)

Output: <name>_shifted.srt next to each input (originals are never changed).
"""

import argparse
import re
import sys
from pathlib import Path

TIME_RE = re.compile(r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{3})")


def parse_delay(text):
    """Return delay in milliseconds from '21', '21:30' or '1:05:00'."""
    text = text.strip()
    sign = -1 if text.startswith("-") else 1
    text = text.lstrip("+-")
    parts = text.split(":")
    try:
        if len(parts) == 1:
            seconds = float(parts[0]) * 60
        elif len(parts) == 2:
            seconds = float(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            seconds = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        else:
            raise ValueError
    except ValueError:
        raise argparse.ArgumentTypeError(f"can't read delay '{text}' (use 21, 21:30 or 1:05:00)")
    return sign * round(seconds * 1000)


def shift_match(m, delay_ms):
    h, mi, s, ms = (int(g) for g in m.groups())
    total = max(0, h * 3600000 + mi * 60000 + s * 1000 + ms + delay_ms)
    h, rem = divmod(total, 3600000)
    mi, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{mi:02d}:{s:02d},{ms:03d}"


def shift_srt(text, delay_ms):
    """Shift only timing lines (those containing '-->'), never the subtitle text."""
    out = []
    count = 0
    for line in text.splitlines():
        if "-->" in line:
            line = TIME_RE.sub(lambda m: shift_match(m, delay_ms), line)
            count += 1
        out.append(line)
    return "\n".join(out) + "\n", count


def main():
    ap = argparse.ArgumentParser(description="Shift .srt timestamps by a delay.")
    ap.add_argument("files", nargs="+", help=".srt file(s) to shift")
    ap.add_argument("-d", "--delay", type=parse_delay,
                    help="delay: minutes (21), MM:SS (21:30) or H:MM:SS; negative = earlier")
    ap.add_argument("-o", "--output", help="output path (single input only)")
    args = ap.parse_args()

    if args.output and len(args.files) != 1:
        ap.error("-o can only be used with one input file")

    delay_ms = args.delay
    if delay_ms is None:
        while True:
            ans = input("Delay subtitles by how many minutes? (e.g. 21 or 21:30): ")
            try:
                delay_ms = parse_delay(ans)
                break
            except argparse.ArgumentTypeError as e:
                print(e)

    print(f"Shifting by {delay_ms / 1000:+.1f} s")
    for f in args.files:
        src = Path(f).expanduser()
        if not src.is_file():
            print(f"  not found: {src}", file=sys.stderr)
            sys.exit(1)
        dst = Path(args.output).expanduser() if args.output else src.with_name(src.stem + "_shifted.srt")
        shifted, n = shift_srt(src.read_text(encoding="utf-8"), delay_ms)
        dst.write_text(shifted, encoding="utf-8")
        print(f"  {src.name} -> {dst.name}  ({n} cues)")


if __name__ == "__main__":
    main()
