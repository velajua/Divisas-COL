# Divisas COL - HTML to Voiceover

This project converts one Divisas COL HTML article into a Spanish voiceover using local CPU-friendly Coqui XTTS v2.

The workflow is:

```text
HTML article
  -> extract important article text
  -> build a spoken narration script
  -> split script into chunks
  -> generate WAV audio per chunk
  -> merge chunks
  -> export final MP3
```

---

## 1. Requirements

You need:

1. Python 3.10 or 3.11
2. FFmpeg installed
3. A clean WAV sample of your voice

Recommended voice sample:

```text
15-30 seconds
WAV format
no music
low background noise
normal speaking voice
Spanish preferred
```

Put your voice file here:

```text
voice_samples/my_voice.wav
```

Put your HTML file here:

```text
input/entry.html
```

---

## 2. Create virtual environment

Open Command Prompt in this folder.

Run:

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

First install can take a while because Coqui TTS downloads dependencies.

---

## 3. Install FFmpeg

### Option A - using winget

```bat
winget install Gyan.FFmpeg
```

Close and reopen Command Prompt after installing.

Check:

```bat
ffmpeg -version
```

### Option B - using Chocolatey

```bat
choco install ffmpeg
```

Check:

```bat
ffmpeg -version
```

---

## 4. Test script extraction only

This does NOT generate audio yet.

```bat
python generate_voiceover.py --html input\entry.html --voice voice_samples\my_voice.wav --out-dir output --script-only
```

Expected output:

```text
output\article.json
output\voiceover_script.txt
output\chunks\chunk_001.txt
output\chunks\chunk_002.txt
...
```

Open:

```text
output\voiceover_script.txt
```

Review if the narration looks good.

---

## 5. Generate full voiceover

```bat
python generate_voiceover.py --html input\entry.html --voice voice_samples\my_voice.wav --out-dir output --format mp3
```

Final files:

```text
output\voiceover.wav
output\voiceover.mp3
```

---

## 6. Faster short version

For shorter social media narration:

```bat
python generate_voiceover.py --html input\entry.html --voice voice_samples\my_voice.wav --out-dir output --mode short --format mp3
```

---

## 7. Important CPU notes

This is designed to run without RTX/GPU.

On CPU, it may be slow. That is normal.

The script generates audio paragraph by paragraph because long text in one shot is slower and often worse quality.

---

## 8. Common problems

### Problem: `ffmpeg not found`

FFmpeg is not installed or not in PATH.

Run:

```bat
ffmpeg -version
```

If that fails, install FFmpeg and reopen Command Prompt.

---

### Problem: `ModuleNotFoundError`

Make sure your virtual environment is active:

```bat
.venv\Scripts\activate
pip install -r requirements.txt
```

---

### Problem: voice sounds bad

Use a better reference WAV.

Best sample format:

```text
16-bit WAV
mono or stereo
15-30 seconds
no music
no background noise
clear speaking
```

---

### Problem: first run takes forever

The model downloads the first time. Later runs reuse the downloaded model.

---

## 9. Files in this project

```text
generate_voiceover.py      Main script
requirements.txt           Python dependencies
src\extract_article.py      Extracts content from Divisas COL HTML
src\build_script.py         Builds narration script
src\tts_xtts.py             Runs XTTS voice generation
src\audio_merge.py          Merges WAV chunks and exports MP3
input\                     Put HTML files here
voice_samples\             Put your voice WAV here
output\                    Generated files go here
```

---

## 10. Main command

Use this most of the time:

```bat
python generate_voiceover.py --html input\entry.html --voice voice_samples\my_voice.wav --out-dir output --format mp3
```

---

## 11. Marketing reel maker workflow

This folder can also run a file-based reel workflow for daily forex and LATAM purchasing-power content.

The workflow is:

```text
reel template
  -> editable reel.json structure
  -> script.txt for voiceover
  -> subtitles.srt
  -> image prompts + placeholder scene images
  -> silent review draft
  -> timed XTTS lines from final subtitles
  -> cleaned timed TTS + final preview MP4
  -> optional later supplied human voiceover
  -> cleaned human voiceover + final final MP4
```

Create a new reel project:

```bat
python reel_maker.py new --template daily_fx --slug peso-watch-2026-05-19
```

Generated files:

```text
reels\projects\peso-watch-2026-05-19\reel.json
reels\projects\peso-watch-2026-05-19\script.txt
reels\projects\peso-watch-2026-05-19\subtitles.srt
reels\projects\peso-watch-2026-05-19\images\
reels\projects\peso-watch-2026-05-19\prompts\
reels\history.json
```

Edit `reel.json` and `script.txt` with the hook, data point, cut timing, subtitles, visual prompts, and CTA you want. The history file tracks previous reels and render status.

If you provide your own voiceover during the project workflow, place it here:

```text
reels\projects\peso-watch-2026-05-19\voiceover.wav
```

Clean the voiceover for reel background audio:

```bat
python reel_maker.py clean-audio --project peso-watch-2026-05-19
```

Regenerate subtitles after editing scene subtitles or durations:

```bat
python reel_maker.py subtitles --project peso-watch-2026-05-19
```

Render the final vertical reel:

```bat
python reel_maker.py render --project peso-watch-2026-05-19
```

The final file is:

```text
reels\projects\peso-watch-2026-05-19\final.mp4
```

### Silent draft plus later voiceover workflow

For review drafts made outside the project renderer, keep the draft MP4 silent. After the subtitle timing is final, the automated preview path can generate short XTTS voice lines from the subtitle cues, stretch each line to its cue duration, insert subtitle gaps as silence, clean the timed WAV, and mux it into the silent draft. If the silent draft is a few frames shorter than the subtitle-timed audio, the command pads the last video frame so the final preview preserves the full timed voiceover:

```bat
python reel_maker.py timed-tts-final --project peso-watch-2026-05-19 --voice voice_samples\my_voice.wav
```

Defaults:

```text
subtitle source: reels\projects\<slug>\subtitles.srt
ASS fallback:    reels\projects\<slug>\subtitles.ass, using only ReelSub events
silent draft:    reels\projects\<slug>\drafts\final.mp4
sample folder:   reels\projects\<slug>\tts_timed_sample\
final preview:   reels\projects\<slug>\drafts\final_timed_tts.mp4
```

Generated timed TTS files:

```text
reels\projects\<slug>\tts_timed_voice_lines.txt
reels\projects\<slug>\tts_timed_sample\voiceover.wav
reels\projects\<slug>\tts_timed_sample\voiceover_timed_to_subtitles.wav
reels\projects\<slug>\tts_timed_sample\voiceover_timed_to_subtitles_clean.wav
reels\projects\<slug>\tts_timed_sample\timing_report.json
reels\projects\<slug>\drafts\final_timed_tts.mp4
```

Use `--video`, `--out`, or `--sample-dir-name` to override the default paths:

```bat
python reel_maker.py timed-tts-final --project peso-watch-2026-05-19 --voice voice_samples\my_voice.wav --video reels\projects\peso-watch-2026-05-19\drafts\final.mp4 --out reels\projects\peso-watch-2026-05-19\drafts\final_timed_tts.mp4
```

This preview voice is still synthetic. If a human voiceover is ready, point the standalone finalizer at the silent draft and the separate voiceover file:

```bat
python reel_maker.py finalize-audio --video reels\projects\peso-watch-2026-05-19\drafts\final.mp4 --voice reels\projects\peso-watch-2026-05-19\voiceover.wav --out reels\projects\peso-watch-2026-05-19\drafts\final_final.mp4
```

This command:

```text
1. cleans the supplied voiceover with the same reel audio filter chain
2. writes voiceover_clean.wav next to the voiceover by default
3. removes any audio from the draft video
4. writes the final final MP4 with the cleaned voiceover as the only audio track
```

Use `--clean-out` if you want the cleaned WAV somewhere else:

```bat
python reel_maker.py finalize-audio --video path\to\draft.mp4 --voice path\to\voiceover.wav --clean-out path\to\voiceover_clean.wav --out path\to\final_final.mp4
```

List previous reel projects:

```bat
python reel_maker.py list
```

If you want to use the existing XTTS flow instead of recording the voice manually, use the generated `script.txt` as input:

```bat
python generate_voiceover.py --txt reels\projects\peso-watch-2026-05-19\script.txt --voice voice_samples\my_voice.wav --out-dir reels\projects\peso-watch-2026-05-19 --format wav
```



---
set VIRTUAL_ENV=C:\Users\juanv\Downloads\Divisas-COL\divisas_voiceover_xtts_clean\.venv
set PATH=%VIRTUAL_ENV%\Scripts;%PATH%
set PYTHONPATH=
set PYTHONNOUSERSITE=1

python generate_voiceover.py --html input/compras-oficiales-vigilancia-fiscal-y-peso-en-alerta.html --voice voice_samples/20000leguas_09_verne_128kb_clip_36.wav --out-dir output --script-only
python generate_voiceover.py --html input/entry.html --voice voice_samples/1.wav --out-dir output --format wav 

---
