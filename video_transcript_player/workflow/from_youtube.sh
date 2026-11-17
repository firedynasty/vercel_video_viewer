#!/bin/bash
# YouTube link → audio → three SRTs: original language, translation, and both together
#
# Usage:
#   bash from_youtube.sh "<youtube url>" [-l <lang>] [-t <lang>]
#
#   -l  Language spoken in the video: zh, ko, ja, en, ... (default: en)
#   -t  Language to translate into (default: en, or zh when -l is en)
#
# Output: ../youtube/<video_id>/   (example: -l ko -t en)
#   <id>_ko.srt     original language only
#   <id>_en.srt     translation only
#   <id>_ko_en.srt  original on top, translation below, same timings
#
# Requires: yt-dlp, ffmpeg, python3, openai pip package, OPENAI_API_KEY

set -e

URL="${1:?Usage: bash from_youtube.sh \"<youtube url>\" [-l lang] [-t lang]}"
shift

SOURCE_LANG="en"
OTHER_LANG=""
while getopts "l:t:" opt; do
  case $opt in
    l) SOURCE_LANG="$OPTARG" ;;
    t) OTHER_LANG="$OPTARG" ;;
    *) echo "Usage: bash from_youtube.sh \"<url>\" [-l lang] [-t lang]"; exit 1 ;;
  esac
done

if [ -z "$OTHER_LANG" ]; then
  if [ "$SOURCE_LANG" = "en" ]; then OTHER_LANG="zh"; else OTHER_LANG="en"; fi
fi
if [ "$SOURCE_LANG" = "$OTHER_LANG" ]; then
  echo "Error: -l and -t must differ"; exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VIDEO_ID=$(yt-dlp --get-id "$URL")
OUT_DIR="${SCRIPT_DIR}/../youtube/${VIDEO_ID}"
mkdir -p "$OUT_DIR"
BASE="${OUT_DIR}/${VIDEO_ID}"

echo "▶ Downloading audio: $VIDEO_ID"
yt-dlp -x --audio-format mp3 --audio-quality 128K -o "${BASE}.%(ext)s" "$URL"

echo "▶ Transcribing ($SOURCE_LANG)"
bash "$SCRIPT_DIR/2_transcribe_srt.sh" -i "${BASE}.mp3" -l "$SOURCE_LANG" -o "${BASE}_${SOURCE_LANG}.srt"

echo "▶ Translating to $OTHER_LANG"
python3 "$SCRIPT_DIR/3_translate_srt.py" -i "${BASE}_${SOURCE_LANG}.srt" -t "$OTHER_LANG" -o "${BASE}_${OTHER_LANG}.srt"

echo "▶ Merging $SOURCE_LANG + $OTHER_LANG"
python3 "$SCRIPT_DIR/4_merge_bilingual.py" -a "${BASE}_${SOURCE_LANG}.srt" -b "${BASE}_${OTHER_LANG}.srt" -o "${BASE}_${SOURCE_LANG}_${OTHER_LANG}.srt"

echo ""
echo "Done. Files in: $(cd "$OUT_DIR" && pwd)"
ls "$OUT_DIR"/*.srt
echo ""
echo "In the player: Embed Link → $URL, then Load SRT → pick one of the .srt files"
