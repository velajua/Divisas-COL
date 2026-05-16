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
set VIRTUAL_ENV=C:\Users\juanv\Downloads\Divisas-COL\divisas_voiceover_xtts_clean\.venv
set PATH=%VIRTUAL_ENV%\Scripts;%PATH%
set PYTHONPATH=
set PYTHONNOUSERSITE=1

python generate_voiceover.py --html input/compras-oficiales-vigilancia-fiscal-y-peso-en-alerta.html --voice voice_samples/20000leguas_09_verne_128kb_clip_36.wav --out-dir output --script-only
python generate_voiceover.py --html input/entry.html --voice voice_samples/1.wav --out-dir output --format wav 

---
