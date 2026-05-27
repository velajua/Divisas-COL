import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
SRT = PROJECT / "subtitles.srt"
CHUNKS = ROOT / "chunks"
TIMED = ROOT / "timed_chunks"
OUT = ROOT / "voiceover_timed_to_srt.wav"
REPORT = ROOT / "timing_report.json"


def parse_time(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, millis = rest.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def ffprobe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def atempo_filter(factor: float) -> str:
    parts = []
    while factor > 2.0:
        parts.append("atempo=2.0")
        factor /= 2.0
    while factor < 0.5:
        parts.append("atempo=0.5")
        factor /= 0.5
    parts.append(f"atempo={factor:.8f}")
    return ",".join(parts)


def timing_filter(tempo: float, target_duration: float) -> str:
    return (
        f"{atempo_filter(tempo)},"
        f"apad,"
        f"atrim=start=0:end={target_duration:.6f},"
        "asetpts=N/SR/TB"
    )


def read_cues() -> list[dict]:
    blocks = re.split(r"\r?\n\r?\n", SRT.read_text(encoding="utf-8").strip())
    cues = []
    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 3:
            continue
        start_raw, end_raw = [part.strip() for part in lines[1].split("-->")]
        cues.append(
            {
                "index": int(lines[0]),
                "start": parse_time(start_raw),
                "end": parse_time(end_raw),
                "text": " ".join(line.strip() for line in lines[2:] if line.strip()),
            }
        )
    return cues


def main() -> None:
    TIMED.mkdir(exist_ok=True)
    concat_file = TIMED / "concat.txt"
    cues = read_cues()
    report = []

    with concat_file.open("w", encoding="utf-8") as concat:
        for cue in cues:
            index = cue["index"]
            source = CHUNKS / f"chunk_{index:03d}.wav"
            target = TIMED / f"chunk_{index:03d}.wav"
            target_duration = cue["end"] - cue["start"]
            source_duration = ffprobe_duration(source)
            tempo = source_duration / target_duration
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(source),
                    "-af",
                    timing_filter(tempo, target_duration),
                    "-ar",
                    "24000",
                    "-ac",
                    "1",
                    str(target),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            actual_duration = ffprobe_duration(target)
            concat.write(f"file '{target.resolve().as_posix()}'\n")
            report.append(
                {
                    "index": index,
                    "text": cue["text"],
                    "target_duration": target_duration,
                    "source_duration": source_duration,
                    "tempo": tempo,
                    "actual_duration": actual_duration,
                    "delta": actual_duration - target_duration,
                }
            )

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            str(OUT),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    report.append(
        {
            "output": str(OUT),
            "target_duration": cues[-1]["end"],
            "actual_duration": ffprobe_duration(OUT),
        }
    )
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
