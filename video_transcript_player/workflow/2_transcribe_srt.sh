#!/bin/bash
# Step 2: Transcribe MP3 → SRT via OpenAI Whisper API
# Handles large files by splitting into 10-min segments and merging.
#
# Usage:
#   bash 2_transcribe_srt.sh -i <input.mp3> [-l <language>] [-o <output.srt>]
#
# Options:
#   -i  Input MP3 file (required)
#   -l  Language code: zh, en, ko, es, etc. (default: zh)
#   -o  Output SRT path (default: same name as input, .srt extension)
#
# Requires: ffmpeg, curl, OPENAI_API_KEY env var

set -e

LANGUAGE="zh"
OUTPUT=""

while getopts "i:l:o:" opt; do
  case $opt in
    i) INPUT="$OPTARG" ;;
    l) LANGUAGE="$OPTARG" ;;
    o) OUTPUT="$OPTARG" ;;
    *) echo "Usage: bash 2_transcribe_srt.sh -i <input.mp3> [-l language] [-o output.srt]"; exit 1 ;;
  esac
done

if [ -z "$INPUT" ]; then
  echo "Error: -i input.mp3 is required"
  exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
  echo "Error: OPENAI_API_KEY is not set. Run: export OPENAI_API_KEY='sk-...'"
  exit 1
fi

BASENAME=$(basename "$INPUT" | sed 's/\.[^.]*$//')
DIR=$(dirname "$INPUT")
OUTPUT="${OUTPUT:-${DIR}/${BASENAME}.srt}"
SEGMENT_DURATION=600  # 10 minutes
TMPDIR_SEG=$(mktemp -d)

# Language-specific Whisper prompt hints
PROMPT=""
case "$LANGUAGE" in
  zh) PROMPT="請用繁體中文轉錄。請勿使用簡體中文。Use Traditional Chinese characters only, not Simplified Chinese." ;;
  *)  PROMPT="" ;;
esac

# Check file size — split if > 24MB
FILE_SIZE_MB=$(du -m "$INPUT" | cut -f1)
echo "Input: $INPUT (${FILE_SIZE_MB}MB)"

if [ "$FILE_SIZE_MB" -le 24 ]; then
  SEGMENTS=("$INPUT")
  OFFSETS=(0)
else
  echo "Splitting into ${SEGMENT_DURATION}s segments..."
  ffmpeg -y -i "$INPUT" -f segment -segment_time "$SEGMENT_DURATION" -c copy "${TMPDIR_SEG}/segment_%03d.mp3" 2>/dev/null
  SEGMENTS=($(ls "${TMPDIR_SEG}"/segment_*.mp3 | sort))
  OFFSETS=()
  for i in "${!SEGMENTS[@]}"; do
    OFFSETS+=($((i * SEGMENT_DURATION)))
  done
fi

# Transcribe each segment
SRT_FILES=()
for i in "${!SEGMENTS[@]}"; do
  SEG="${SEGMENTS[$i]}"
  OFFSET="${OFFSETS[$i]}"
  SEG_SRT="${TMPDIR_SEG}/seg_$(printf '%03d' $i).srt"

  echo "  Transcribing segment $i (offset ${OFFSET}s)..."
  CURL_ARGS=(
    -s https://api.openai.com/v1/audio/transcriptions
    -H "Authorization: Bearer $OPENAI_API_KEY"
    -H "Content-Type: multipart/form-data"
    -F file="@$SEG"
    -F model="whisper-1"
    -F language="$LANGUAGE"
    -F response_format="srt"
  )
  if [ -n "$PROMPT" ]; then
    CURL_ARGS+=(-F prompt="$PROMPT")
  fi

  curl "${CURL_ARGS[@]}" -o "$SEG_SRT"
  SRT_FILES+=("$SEG_SRT")
done

# Merge segments with timestamp offset
echo "Merging into: $OUTPUT"
python3 - "${SRT_FILES[@]}" "${OFFSETS[@]}" -- "$OUTPUT" <<'PYEOF'
import sys
import re

def parse_srt_time(ts):
    m = re.match(r'(\d+):(\d{2}):(\d{2})[,.](\d{1,3})', ts.strip())
    if not m: return 0
    h, mnt, s, ms = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4).ljust(3,'0'))
    return h*3600000 + mnt*60000 + s*1000 + ms

def fmt_time(ms):
    h = ms // 3600000
    mnt = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    ms = ms % 1000
    return f"{h:02d}:{mnt:02d}:{s:02d},{ms:03d}"

args = sys.argv[1:]
sep = args.index('--')
files = args[:sep - len([a for a in args if re.match(r'^\d+$', a)])]
offsets = [int(x) for x in args if re.match(r'^\d+$', x)]
output = args[-1]

entries = []
counter = 1

for fpath, offset_s in zip(files, offsets):
    offset_ms = offset_s * 1000
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    blocks = re.split(r'\n\s*\n', content.strip())
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 2: continue
        ts_idx = next((i for i, l in enumerate(lines) if '-->' in l), -1)
        if ts_idx == -1: continue
        m = re.match(r'(.+?)\s*-->\s*(.+)', lines[ts_idx])
        if not m: continue
        start = parse_srt_time(m.group(1)) + offset_ms
        end   = parse_srt_time(m.group(2)) + offset_ms
        text  = '\n'.join(lines[ts_idx+1:]).strip()
        if not text: continue
        entries.append((start, end, text))

entries.sort(key=lambda x: x[0])

with open(output, 'w', encoding='utf-8') as f:
    for i, (start, end, text) in enumerate(entries, 1):
        f.write(f"{i}\n{fmt_time(start)} --> {fmt_time(end)}\n{text}\n\n")

print(f"  {len(entries)} cues written to {output}")
PYEOF

rm -rf "$TMPDIR_SEG"
echo "Done: $OUTPUT"
