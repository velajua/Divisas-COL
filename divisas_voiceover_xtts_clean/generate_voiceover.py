import argparse
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from src.extract_article import extract_article, save_article_json
from src.build_script import build_voiceover_script, split_script_into_chunks, save_text
from src.audio_merge import merge_wavs, export_mp3


def split_line_to_limit(line: str, max_chars: int) -> list[str]:
    line = line.strip()

    if not line:
        return []

    if len(line) <= max_chars:
        return [line]

    chunks = []
    current = ""

    for word in line.split():
        if len(word) > max_chars:
            if current:
                chunks.append(current)
                current = ""

            for start in range(0, len(word), max_chars):
                chunks.append(word[start:start + max_chars])
            continue

        if current and len(current) + 1 + len(word) > max_chars:
            chunks.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()

    if current:
        chunks.append(current)

    return chunks


def load_txt_lines(txt_path: Path) -> list[str]:
    return [
        line.strip()
        for line in txt_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_txt_chunks(txt_path: Path, max_chars: int) -> list[str]:
    chunks = []

    for line in load_txt_lines(txt_path):
        chunks.extend(split_line_to_limit(line, max_chars=max_chars))

    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a Divisas COL HTML article into a Spanish voiceover."
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--html", help="Input HTML article path.")
    input_group.add_argument("--txt", help="Input plain text path. Each non-empty line becomes its own chunk.")
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

    html_path = Path(args.html) if args.html else None
    txt_path = Path(args.txt) if args.txt else None
    voice_path = Path(args.voice)
    out_dir = Path(args.out_dir)
    chunks_dir = out_dir / "chunks"

    if html_path and not html_path.exists():
        raise FileNotFoundError(f"HTML file not found: {html_path}")

    if txt_path and not txt_path.exists():
        raise FileNotFoundError(f"TXT file not found: {txt_path}")

    if not voice_path.exists():
        raise FileNotFoundError(f"Voice WAV file not found: {voice_path}")

    out_dir.mkdir(parents=True, exist_ok=True)
    chunks_dir.mkdir(parents=True, exist_ok=True)

    if html_path:
        print("Extracting article text from HTML...")
        article = extract_article(html_path)
        save_article_json(article, out_dir / "article.json")

        print("Building voiceover script...")
        script = build_voiceover_script(article, mode=args.mode)
        chunks = split_script_into_chunks(script, max_chars=args.max_chars)
    else:
        print("Reading plain text lines...")
        lines = load_txt_lines(txt_path)
        script = "\n".join(lines)
        chunks = load_txt_chunks(txt_path, max_chars=args.max_chars)

    save_text(script, out_dir / "voiceover_script.txt")

    for index, chunk in enumerate(chunks, start=1):
        save_text(chunk, chunks_dir / f"chunk_{index:03d}.txt")

    if html_path:
        print(f"Saved article JSON: {out_dir / 'article.json'}")
    print(f"Saved script: {out_dir / 'voiceover_script.txt'}")
    print(f"Created {len(chunks)} text chunks.")

    if args.script_only:
        print("Script-only mode enabled. Audio generation skipped.")
        return

    print("Loading XTTS model. First run may download model files.")
    from src.tts_xtts import XTTSVoiceover
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
