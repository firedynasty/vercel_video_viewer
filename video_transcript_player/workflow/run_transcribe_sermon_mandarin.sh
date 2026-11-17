#!/usr/bin/env bash
# Mandarin sermon audio -> timed bilingual subtitles (zh + en).
#
# Usage:
#   ./run_transcribe_sermon_mandarin.sh "<audio file>" [video_id] [-y]
#
#   audio file  .m4a/.mp3/etc. (e.g. a YouTube download in ~/Downloads)
#   video_id    11-char YouTube id; if omitted, taken from the [brackets] in the file name
#   -y          skip the cost confirmation
#
# Output: ../youtube/<id>/<id>.mp3, <id>_zh.srt, <id>_en.srt, <id>_zh_en.srt
# Steps already done (output file exists) are skipped, so re-running resumes.
# Requires: ffmpeg, python3 + openai, OPENAI_API_KEY in the environment.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

AUDIO="" ; ID="" ; YES=0
for arg in "$@"; do
  case "$arg" in
    -y) YES=1 ;;
    *)  if [ -z "$AUDIO" ]; then AUDIO="$arg"; elif [ -z "$ID" ]; then ID="$arg"; fi ;;
  esac
done

if [ -z "$AUDIO" ]; then
  echo "Usage: $0 \"<audio file>\" [video_id] [-y]" >&2
  exit 1
fi
if [ ! -f "$AUDIO" ]; then
  echo "Audio file not found: $AUDIO" >&2
  exit 1
fi

if [ -z "$ID" ]; then
  if [[ "$AUDIO" =~ \[([A-Za-z0-9_-]{11})\] ]]; then
    ID="${BASH_REMATCH[1]}"
  else
    echo "Could not find an 11-character video id in the file name; pass it as the 2nd argument." >&2
    exit 1
  fi
fi

for cmd in ffmpeg ffprobe python3; do
  command -v "$cmd" >/dev/null || { echo "Missing: $cmd" >&2; exit 1; }
done
if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "OPENAI_API_KEY is not set in this shell." >&2
  exit 1
fi

OUT="../youtube/$ID"
BASE="$OUT/$ID"
mkdir -p "$OUT"

# Cost estimate (Whisper ~ $0.006 per audio minute) and confirmation
SECS="$(ffprobe -v error -show_entries format=duration -of csv=p=0 -i "$AUDIO" | cut -d. -f1)"
MINS=$(( (SECS + 59) / 60 ))
COST="$(python3 -c "print(f'{$MINS*0.006:.2f}')")"
echo "Video id : $ID"
echo "Audio    : $AUDIO"
echo "Length   : ${MINS} min  -> Whisper about \$${COST} (+ a few cents for translation)"
echo "Output   : $OUT/"
if [ "$YES" -ne 1 ]; then
  read -r -p "Proceed? [y/N] " ans
  case "$ans" in y|Y|yes|YES) ;; *) echo "Cancelled."; exit 0 ;; esac
fi

# 1. Convert to mp3 (Whisper limit handling in step 2 only works on mp3; also plain file name)
if [ -f "$BASE.mp3" ]; then
  echo "[1/4] mp3 exists, skipping"
else
  echo "[1/4] Converting to mp3..."
  ffmpeg -loglevel error -y -i "$AUDIO" -vn -b:a 128k "$BASE.mp3"
fi

# 2. Whisper -> Chinese srt
if [ -s "${BASE}_zh.srt" ]; then
  echo "[2/4] ${ID}_zh.srt exists, skipping"
else
  echo "[2/4] Transcribing with Whisper (this can take several minutes)..."
  bash 2_transcribe_srt.sh -i "$BASE.mp3" -l zh -o "${BASE}_zh.srt"
  [ -s "${BASE}_zh.srt" ] || { echo "Transcription produced no .srt" >&2; exit 1; }
fi

# 3. Translate to English
if [ -s "${BASE}_en.srt" ]; then
  echo "[3/4] ${ID}_en.srt exists, skipping"
else
  echo "[3/4] Translating to English..."
  python3 3_translate_srt.py -i "${BASE}_zh.srt" -t en -o "${BASE}_en.srt"
fi

# 4. Merge bilingual
echo "[4/4] Merging bilingual srt..."
python3 4_merge_bilingual.py -a "${BASE}_zh.srt" -b "${BASE}_en.srt" -o "${BASE}_zh_en.srt"

echo
echo "Done. Files in $SCRIPT_DIR/$OUT/"
ls -1 "$OUT"
echo
echo "Player Embed Link: https://www.youtube.com/watch?v=$ID"
echo "Load SRT: ${ID}_zh.srt   + Subs 2: ${ID}_en.srt   (or ${ID}_zh_en.srt alone)"
