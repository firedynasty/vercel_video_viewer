#!/bin/bash
# Step 1: Extract audio from MP4 → MP3
# Usage: bash 1_extract_audio.sh <input.mp4> [output_dir]
# Requires: ffmpeg

set -e

INPUT="${1:?Usage: bash 1_extract_audio.sh <input.mp4> [output_dir]}"
OUTPUT_DIR="${2:-$(dirname "$INPUT")}"
BASENAME=$(basename "$INPUT" | sed 's/\.[^.]*$//')
OUTPUT="${OUTPUT_DIR}/${BASENAME}.mp3"

mkdir -p "$OUTPUT_DIR"

echo "Extracting audio from: $INPUT"
ffmpeg -y -i "$INPUT" -vn -acodec libmp3lame -b:a 128k "$OUTPUT"
echo "Done: $OUTPUT"
