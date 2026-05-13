import argparse
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from extract_article import extract_article, save_article_json
from build_script import build_voiceover_script, split_script_into_chunks, save_text
from audio_merge import merge_wavs, export_mp3


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a Divisas COL HTML article into a Spanish voiceover."
    )
    parser.add_argument("--html", required=True, help="Input HTML article path.")
    parser.add_argument("--voice", required=True, help="Reference voice WAV file.")
    parser.add_argument("--out-dir", default="output", help="Output directory.")
    parser.add_argument("--mode", choices=["full", "short"], default="full")
    parser.add_argument("--language", default="es")
    parser.add_argument("--max-chars", type=int, default=850)
    parser.add_argument("--silence-ms", type=int, default=450)
    parser.add_argument("--format", choices=["wav", "mp3", "both"], default="mp3")
    parser.add_argument("--gpu", action="store_true")
    parser.add_argument("--script-only", action="store_true")
    args = parser.parse_args()

    html_path = Path(args.html)
    voice_path = Path(args.voice)
    out_dir = Path(args.out_dir)
    chunks_dir = out_dir / "chunks"

    if not html_path.exists():
        raise FileNotFoundError(f"HTML file not found: {html_path}")

    if not voice_path.exists():
        raise FileNotFoundError(f"Voice WAV file not found: {voice_path}")

    out_dir.mkdir(parents=True, exist_ok=True)
    chunks_dir.mkdir(parents=True, exist_ok=True)

    print("Extracting article text from HTML...")
    article = extract_article(html_path)
    save_article_json(article, out_dir / "article.json")

    print("Building voiceover script...")
    script = build_voiceover_script(article, mode=args.mode)
    save_text(script, out_dir / "voiceover_script.txt")

    chunks = split_script_into_chunks(script, max_chars=args.max_chars)

    for index, chunk in enumerate(chunks, start=1):
        save_text(chunk, chunks_dir / f"chunk_{index:03d}.txt")

    print(f"Saved article JSON: {out_dir / 'article.json'}")
    print(f"Saved script: {out_dir / 'voiceover_script.txt'}")
    print(f"Created {len(chunks)} text chunks.")

    if args.script_only:
        print("Script-only mode enabled. Audio generation skipped.")
        return

    print("Loading XTTS model. First run may download model files.")
    from tts_xtts import XTTSVoiceover
    engine = XTTSVoiceover(use_gpu=args.gpu)
    
    wav_files = []

    for index, chunk in enumerate(chunks, start=1):
        wav_path = chunks_dir / f"chunk_{index:03d}.wav"
        print(f"Generating audio chunk {index}/{len(chunks)}...")
        engine.synthesize_chunk(
            text=chunk,
            voice_wav=voice_path,
            output_wav=wav_path,
            language=args.language,
        )
        wav_files.append(wav_path)

    final_wav = out_dir / "voiceover.wav"

    print("Merging audio chunks...")
    merge_wavs(wav_files, final_wav, silence_ms=args.silence_ms)
    print(f"Saved WAV: {final_wav}")

    if args.format in {"mp3", "both"}:
        final_mp3 = out_dir / "voiceover.mp3"
        print("Exporting MP3...")
        export_mp3(final_wav, final_mp3)
        print(f"Saved MP3: {final_mp3}")

    print("Done.")


if __name__ == "__main__":
    main()
