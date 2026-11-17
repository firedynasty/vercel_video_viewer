# vercel_video_viewer

Video transcript player: a YouTube video or local file, with bilingual subtitles and word-by-word gloss cards (pinyin, Mandarin and Cantonese speech).

- `public/video_transcript_player.html`: the player (served at `/`)
- `public/worksheet.html` and `public/worksheets/`: practice worksheets made from transcripts (served at `/worksheet`)
- `video_transcript_player/workflow/`: scripts that make the subtitles and glosses

## Workflow

Run from `video_transcript_player/workflow/`:

```bash
# 1. Audio to SRTs (Whisper + English). Writes ../youtube/<ID>/<ID>_zh.srt, _en.srt, _zh_en.srt
./run_transcribe_sermon_mandarin.sh "<audio file>" [<ID>] [-y]

# 2. Optional: shift the times if the audio was trimmed (e.g. starts at 21:00). Writes *_shifted.srt
python3 shift_srt.py -d 21 ../youtube/<ID>/<ID>_zh.srt ../youtube/<ID>/<ID>_en.srt ../youtube/<ID>/<ID>_zh_en.srt

# 3. Gloss (needs OPENAI_API_KEY). Writes <name>.gloss.json next to the SRT
./run_gloss.sh <ID>
```

In the player, click **+ Gloss** and load the `.gloss.json`. The YouTube video embeds automatically. Press **G** to open the gloss card.

`video_transcript_player/youtube/` (SRTs, audio, gloss files) is gitignored and stays local.
