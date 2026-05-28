import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
ASS = PROJECT / "subtitles.ass"
CHUNKS = ROOT / "chunks"
TIMED = ROOT / "timed_chunks"
OUT = ROOT / "voiceover_timed_to_ass.wav"
REPORT = ROOT / "timing_report.json"
SAMPLE_RATE = 24000


def parse_ass_time(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, centis = rest.split(".")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(centis) / 100


def clean_ass_text(value: str) -> str:
    value = re.sub(r"\{[^}]*\}", "", value)
    return value.replace(r"\N", " ").strip()


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


def read_reel_sub_cues() -> list[dict]:
    cues = []
    for line in ASS.read_text(encoding="utf-8").splitlines():
        if not line.startswith("Dialogue:"):
            continue
        fields = line.removeprefix("Dialogue:").strip().split(",", 9)
        if len(fields) != 10 or fields[3] != "ReelSub":
            continue
        cues.append(
            {
                "index": len(cues) + 1,
                "start": parse_ass_time(fields[1]),
                "end": parse_ass_time(fields[2]),
                "text": clean_ass_text(fields[9]),
            }
        )
    return cues


def make_silence(path: Path, duration: float) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=r={SAMPLE_RATE}:cl=mono",
            "-t",
            f"{duration:.6f}",
            str(path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> None:
    TIMED.mkdir(exist_ok=True)
    concat_file = TIMED / "concat.txt"
    cues = read_reel_sub_cues()
    report = []
    cursor = 0.0
    segment_number = 1

    with concat_file.open("w", encoding="utf-8") as concat:
        for cue in cues:
            if cue["start"] > cursor:
                gap_duration = cue["start"] - cursor
                gap = TIMED / f"segment_{segment_number:03d}_silence.wav"
                make_silence(gap, gap_duration)
                concat.write(f"file '{gap.resolve().as_posix()}'\n")
                report.append(
                    {
                        "type": "silence",
                        "start": cursor,
                        "end": cue["start"],
                        "target_duration": gap_duration,
                        "actual_duration": ffprobe_duration(gap),
                    }
                )
                segment_number += 1

            index = cue["index"]
            source = CHUNKS / f"chunk_{index:03d}.wav"
            target = TIMED / f"segment_{segment_number:03d}_chunk_{index:03d}.wav"
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
                    str(SAMPLE_RATE),
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
                    "type": "voice",
                    "index": index,
                    "text": cue["text"],
                    "start": cue["start"],
                    "end": cue["end"],
                    "target_duration": target_duration,
                    "source_duration": source_duration,
                    "tempo": tempo,
                    "actual_duration": actual_duration,
                    "delta": actual_duration - target_duration,
                }
            )
            cursor = cue["end"]
            segment_number += 1

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
            "type": "output",
            "output": str(OUT),
            "target_duration": cues[-1]["end"],
            "actual_duration": ffprobe_duration(OUT),
        }
    )
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
