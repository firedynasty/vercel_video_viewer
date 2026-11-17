#!/bin/bash
# Full pipeline: MP4 → MP3 → SRT (transcription) → optional translated SRT
#
# Usage:
#   bash run_all.sh -i <input.mp4> [-l <source_lang>] [-t <target_lang>] [-o <output_dir>]
#
# Options:
#   -i  Input MP4 file (required)
#   -l  Source language code for Whisper transcription (default: zh)
#   -t  Target language for translation (optional — skip if not provided)
#   -o  Output directory (default: same directory as input video)
#
# Examples:
#   bash run_all.sh -i sermon.mp4 -l zh -t en
#   bash run_all.sh -i lecture.mp4 -l en -t zh
#   bash run_all.sh -i video.mp4 -l en              # transcribe only, no translation
#
# Requires: ffmpeg, curl, python3, openai pip package, OPENAI_API_KEY env var

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_LANG="zh"
TARGET_LANG=""
OUTPUT_DIR=""

while getopts "i:l:t:o:" opt; do
  case $opt in
    i) INPUT="$OPTARG" ;;
    l) SOURCE_LANG="$OPTARG" ;;
    t) TARGET_LANG="$OPTARG" ;;
    o) OUTPUT_DIR="$OPTARG" ;;
    *) echo "Usage: bash run_all.sh -i <input.mp4> [-l lang] [-t lang] [-o output_dir]"; exit 1 ;;
  esac
done

if [ -z "$INPUT" ]; then
  echo "Error: -i input.mp4 is required"
  exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
  echo "Error: OPENAI_API_KEY is not set. Run: export OPENAI_API_KEY='sk-...'"
  exit 1
fi

BASENAME=$(basename "$INPUT" | sed 's/\.[^.]*$//')
OUTPUT_DIR="${OUTPUT_DIR:-$(dirname "$INPUT")}"
mkdir -p "$OUTPUT_DIR"

MP3="${OUTPUT_DIR}/${BASENAME}.mp3"
SRT="${OUTPUT_DIR}/${BASENAME}.srt"

echo "=============================="
echo " Video Transcript Pipeline"
echo "=============================="
echo " Input:   $INPUT"
echo " Source:  $SOURCE_LANG"
echo " Target:  ${TARGET_LANG:-none}"
echo " Output:  $OUTPUT_DIR"
echo "=============================="

echo ""
echo "▶ Step 1: Extract audio"
bash "$SCRIPT_DIR/1_extract_audio.sh" "$INPUT" "$OUTPUT_DIR"

echo ""
echo "▶ Step 2: Transcribe to SRT ($SOURCE_LANG)"
bash "$SCRIPT_DIR/2_transcribe_srt.sh" -i "$MP3" -l "$SOURCE_LANG" -o "$SRT"

if [ -n "$TARGET_LANG" ]; then
  echo ""
  echo "▶ Step 3: Translate SRT to $TARGET_LANG"
  TRANSLATED_SRT="${OUTPUT_DIR}/${BASENAME}_${TARGET_LANG}.srt"
  python3 "$SCRIPT_DIR/3_translate_srt.py" -i "$SRT" -t "$TARGET_LANG" -o "$TRANSLATED_SRT"
fi

echo ""
echo "=============================="
echo " Done!"
echo "=============================="
echo " SRT:        $SRT"
[ -n "$TARGET_LANG" ] && echo " Translated: ${OUTPUT_DIR}/${BASENAME}_${TARGET_LANG}.srt"
echo ""
echo " Open video_transcript_player/index.html and load:"
echo "   Video: $INPUT"
echo "   SRT:   $SRT"
