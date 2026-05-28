import json
import re
import struct
import subprocess
import sys
import zlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ReelWorkflowError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReelProject:
    slug: str
    project_dir: Path
    reel_json: Path
    script_path: Path
    subtitles_path: Path


@dataclass(frozen=True)
class SubtitleCue:
    index: int
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class TimedTTSResult:
    voice_lines: Path
    raw_voiceover: Path
    timed_voiceover: Path
    clean_voiceover: Path
    output_video: Path
    timing_report: Path
    target_duration: float


DAILY_FX_SCENES = [
    {
        "id": "hook",
        "duration_seconds": 3.5,
        "subtitle": "El dólar no se mueve solo.",
        "voiceover_text": "El dólar no se mueve solo.",
        "visual_prompt": (
            "vertical 9:16 finance news graphic, Colombian peso and US dollar exchange board, "
            "serious LATAM editorial style, high contrast, no fake logos"
        ),
    },
    {
        "id": "data",
        "duration_seconds": 4.5,
        "subtitle": "Cuando el Gobierno gasta más, la moneda paga la factura.",
        "voiceover_text": "Cuando el Gobierno gasta más, la moneda paga la factura.",
        "visual_prompt": (
            "vertical 9:16 chart graphic showing USD COP pressure, fiscal deficit headline, "
            "clean financial dashboard aesthetic"
        ),
    },
    {
        "id": "comparison",
        "duration_seconds": 4.0,
        "subtitle": "La pregunta real: ¿cuánto compra tu salario hoy?",
        "voiceover_text": "La pregunta real: cuánto compra tu salario hoy.",
        "visual_prompt": (
            "vertical 9:16 grocery basket and Colombian peso comparison, purchasing power theme, "
            "documentary economic realism"
        ),
    },
    {
        "id": "interpretation",
        "duration_seconds": 5.0,
        "subtitle": "El mercado castiga el relato cuando no ve disciplina.",
        "voiceover_text": "El mercado castiga el relato cuando no ve disciplina.",
        "visual_prompt": (
            "vertical 9:16 split scene of congress spending debate and falling currency chart, "
            "right leaning economic realism, not partisan logos"
        ),
    },
    {
        "id": "cta",
        "duration_seconds": 3.5,
        "subtitle": "¿Dólar arriba o abajo esta semana?",
        "voiceover_text": "Dólar arriba o abajo esta semana. Te leo.",
        "visual_prompt": (
            "vertical 9:16 final question screen, USD COP ticker, comment prompt, modern financial "
            "news reel design"
        ),
    },
]


TEMPLATES = {
    "daily_fx": {
        "title": "Peso Watch",
        "niche": "right-leaning LATAM FX reality",
        "format": "daily_fx_comparison",
        "cta": "¿Dólar arriba o abajo esta semana?",
        "scenes": DAILY_FX_SCENES,
    }
}


def create_reel_project(
    root: str | Path,
    slug: str,
    template: str = "daily_fx",
    title: str | None = None,
) -> ReelProject:
    root = Path(root)
    if template not in TEMPLATES:
        raise ReelWorkflowError(f"Unknown template: {template}")

    project_dir = root / "reels" / "projects" / slug
    if project_dir.exists():
        raise ReelWorkflowError(f"Reel project already exists: {project_dir}")

    template_data = TEMPLATES[template]
    images_dir = project_dir / "images"
    prompts_dir = project_dir / "prompts"
    render_dir = project_dir / "render"
    images_dir.mkdir(parents=True)
    prompts_dir.mkdir(parents=True)
    render_dir.mkdir(parents=True)

    scenes = []
    for index, scene in enumerate(template_data["scenes"], start=1):
        scene_id = scene["id"]
        image_name = f"{index:03d}_{scene_id}.png"
        prompt_name = f"{index:03d}_{scene_id}.txt"
        scene_data = dict(scene)
        scene_data["image"] = f"images/{image_name}"
        scene_data["prompt_file"] = f"prompts/{prompt_name}"
        scenes.append(scene_data)

        (prompts_dir / prompt_name).write_text(scene["visual_prompt"], encoding="utf-8")
        write_placeholder_png(
            images_dir / image_name,
            title=scene_id.upper(),
            subtitle=scene["subtitle"],
            seed=index,
        )

    reel_data = {
        "slug": slug,
        "title": title or template_data["title"],
        "status": "draft",
        "template": template,
        "niche": template_data["niche"],
        "format": template_data["format"],
        "created_at": utc_now(),
        "voiceover": {
            "mode": "provided_or_xtts",
            "file": "voiceover.wav",
            "clean_file": "voiceover_clean.wav",
        },
        "scenes": scenes,
        "cta": template_data["cta"],
        "outputs": {},
    }

    reel_json = project_dir / "reel.json"
    script_path = project_dir / "script.txt"
    subtitles_path = project_dir / "subtitles.srt"

    write_json(reel_json, reel_data)
    script_path.write_text(build_script_from_scenes(scenes), encoding="utf-8")
    subtitles_path.write_text(generate_subtitles(scenes), encoding="utf-8")
    update_history(root, slug=slug, title=reel_data["title"], status="draft")

    return ReelProject(
        slug=slug,
        project_dir=project_dir,
        reel_json=reel_json,
        script_path=script_path,
        subtitles_path=subtitles_path,
    )


def build_script_from_scenes(scenes: list[dict[str, Any]]) -> str:
    lines = [scene.get("voiceover_text", "").strip() for scene in scenes]
    return "\n".join(line for line in lines if line)


def generate_subtitles(scenes: list[dict[str, Any]]) -> str:
    blocks = []
    cursor = 0.0

    for index, scene in enumerate(scenes, start=1):
        duration = float(scene.get("duration_seconds", 0))
        if duration <= 0:
            raise ReelWorkflowError(f"Scene {scene.get('id', index)} must have a positive duration.")

        start = cursor
        end = cursor + duration
        text = str(scene.get("subtitle") or scene.get("voiceover_text") or "").strip()
        blocks.append(f"{index}\n{format_srt_time(start)} --> {format_srt_time(end)}\n{text}\n")
        cursor = end

    return "\n".join(blocks).strip() + "\n"


def regenerate_subtitles(root: str | Path, slug: str) -> Path:
    project_dir = get_project_dir(root, slug)
    reel_data = read_json(project_dir / "reel.json")
    subtitles_path = project_dir / "subtitles.srt"
    subtitles_path.write_text(generate_subtitles(reel_data["scenes"]), encoding="utf-8")
    return subtitles_path


def build_clean_audio_command(input_audio: str | Path, output_audio: str | Path) -> list[str]:
    filters = ",".join(
        [
            "highpass=f=80",
            "lowpass=f=12000",
            "afftdn=nf=-25",
            "dynaudnorm=f=150:g=15",
            "loudnorm=I=-16:TP=-1.5:LRA=11",
        ]
    )
    return ["ffmpeg", "-y", "-i", str(input_audio), "-af", filters, str(output_audio)]


def build_timed_chunk_command(
    source_audio: str | Path,
    output_audio: str | Path,
    tempo: float,
    target_duration: float,
    sample_rate: int = 24000,
) -> list[str]:
    filters = (
        f"{build_atempo_filter(tempo)},"
        f"apad,"
        f"atrim=start=0:end={target_duration:.6f},"
        "asetpts=N/SR/TB"
    )
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(source_audio),
        "-af",
        filters,
        "-ar",
        str(sample_rate),
        "-ac",
        "1",
        str(output_audio),
    ]


def build_silence_command(output_audio: str | Path, duration: float, sample_rate: int = 24000) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"anullsrc=r={sample_rate}:cl=mono",
        "-t",
        f"{duration:.6f}",
        str(output_audio),
    ]


def build_finalize_audio_command(
    video_file: str | Path,
    audio_file: str | Path,
    output_file: str | Path,
) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(video_file),
        "-i",
        str(audio_file),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(output_file),
    ]


def build_exact_timed_finalize_audio_command(
    video_file: str | Path,
    audio_file: str | Path,
    output_file: str | Path,
    target_duration: float,
    video_duration: float,
) -> list[str]:
    base = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_file),
        "-i",
        str(audio_file),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
    ]
    duration_args = ["-t", f"{target_duration:.6f}"]
    audio_args = ["-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output_file)]

    if video_duration < target_duration:
        pad_duration = target_duration - video_duration
        return (
            base
            + [
                "-vf",
                f"tpad=stop_mode=clone:stop_duration={pad_duration:.6f}",
            ]
            + duration_args
            + [
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
            ]
            + audio_args
        )

    return base + duration_args + ["-c:v", "copy"] + audio_args


def clean_audio(root: str | Path, slug: str) -> Path:
    project_dir = get_project_dir(root, slug)
    reel_data = read_json(project_dir / "reel.json")
    input_audio = project_dir / reel_data["voiceover"]["file"]
    output_audio = project_dir / reel_data["voiceover"].get("clean_file", "voiceover_clean.wav")

    if not input_audio.exists():
        raise ReelWorkflowError(f"Voiceover file not found: {input_audio}")

    subprocess.run(build_clean_audio_command(input_audio, output_audio), check=True)
    return output_audio


def finalize_audio(
    video_file: str | Path,
    voiceover_file: str | Path,
    output_file: str | Path,
    clean_audio_file: str | Path | None = None,
) -> Path:
    video_path = Path(video_file)
    voiceover_path = Path(voiceover_file)
    output_path = Path(output_file)
    clean_path = Path(clean_audio_file) if clean_audio_file is not None else voiceover_path.with_name(
        f"{voiceover_path.stem}_clean.wav"
    )

    if not video_path.exists():
        raise ReelWorkflowError(f"Draft video file not found: {video_path}")
    if not voiceover_path.exists():
        raise ReelWorkflowError(f"Voiceover file not found: {voiceover_path}")

    clean_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(build_clean_audio_command(voiceover_path, clean_path), check=True)
    subprocess.run(build_finalize_audio_command(video_path, clean_path, output_path), check=True)
    return clean_path


def generate_timed_tts_final(
    root: str | Path,
    slug: str,
    voice_wav: str | Path,
    draft_video: str | Path | None = None,
    output_video: str | Path | None = None,
    sample_dir_name: str = "tts_timed_sample",
) -> TimedTTSResult:
    root = Path(root)
    project_dir = get_project_dir(root, slug)
    voice_path = Path(voice_wav)
    draft_path = Path(draft_video) if draft_video is not None else project_dir / "drafts" / "final.mp4"
    output_path = Path(output_video) if output_video is not None else project_dir / "drafts" / "final_timed_tts.mp4"

    if not draft_path.exists():
        raise ReelWorkflowError(f"Draft video file not found: {draft_path}")
    if not voice_path.exists():
        raise ReelWorkflowError(f"Voice WAV file not found: {voice_path}")

    cues = load_subtitle_cues(project_dir)
    sample_dir = project_dir / sample_dir_name
    chunks_dir = sample_dir / "chunks"
    timed_dir = sample_dir / "timed_chunks"
    voice_lines = project_dir / "tts_timed_voice_lines.txt"
    raw_voiceover = sample_dir / "voiceover.wav"
    timed_voiceover = sample_dir / "voiceover_timed_to_subtitles.wav"
    clean_voiceover = sample_dir / "voiceover_timed_to_subtitles_clean.wav"
    timing_report = sample_dir / "timing_report.json"

    sample_dir.mkdir(parents=True, exist_ok=True)
    timed_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    voice_lines.write_text("\n".join(cue.text for cue in cues) + "\n", encoding="utf-8")

    generator = Path(__file__).resolve().parents[1] / "generate_voiceover.py"
    subprocess.run(
        [
            sys.executable,
            str(generator),
            "--txt",
            str(voice_lines),
            "--voice",
            str(voice_path),
            "--out-dir",
            str(sample_dir),
            "--format",
            "wav",
            "--silence-ms",
            "0",
        ],
        check=True,
    )

    target_duration = write_timed_voiceover_from_chunks(
        cues=cues,
        chunks_dir=chunks_dir,
        timed_dir=timed_dir,
        output_wav=timed_voiceover,
        report_path=timing_report,
    )
    subprocess.run(build_clean_audio_command(timed_voiceover, clean_voiceover), check=True)
    video_duration = ffprobe_duration(draft_path)
    subprocess.run(
        build_exact_timed_finalize_audio_command(
            video_file=draft_path,
            audio_file=clean_voiceover,
            output_file=output_path,
            target_duration=target_duration,
            video_duration=video_duration,
        ),
        check=True,
    )

    return TimedTTSResult(
        voice_lines=voice_lines,
        raw_voiceover=raw_voiceover,
        timed_voiceover=timed_voiceover,
        clean_voiceover=clean_voiceover,
        output_video=output_path,
        timing_report=timing_report,
        target_duration=target_duration,
    )


def build_render_command(
    concat_file: str | Path,
    subtitles_file: str | Path,
    audio_file: str | Path,
    output_file: str | Path,
) -> list[str]:
    subtitle_filter = escape_subtitle_filter_path(subtitles_file)
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        f"subtitles='{subtitle_filter}':force_style='FontName=Arial,FontSize=64,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=4,"
        "Alignment=2,MarginV=170'"
    )
    return [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-i",
        str(audio_file),
        "-vf",
        vf,
        "-shortest",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(output_file),
    ]


def render_reel(root: str | Path, slug: str, use_clean_audio: bool = True) -> Path:
    root = Path(root)
    project_dir = get_project_dir(root, slug)
    reel_path = project_dir / "reel.json"
    reel_data = read_json(reel_path)
    render_dir = project_dir / "render"
    render_dir.mkdir(exist_ok=True)

    concat_file = render_dir / "concat.txt"
    write_concat_file(project_dir, reel_data["scenes"], concat_file)
    subtitles_file = regenerate_subtitles(root, slug)

    clean_name = reel_data["voiceover"].get("clean_file", "voiceover_clean.wav")
    raw_name = reel_data["voiceover"]["file"]
    preferred_audio = project_dir / clean_name if use_clean_audio else project_dir / raw_name
    fallback_audio = project_dir / raw_name
    audio_file = preferred_audio if preferred_audio.exists() else fallback_audio
    if not audio_file.exists():
        raise ReelWorkflowError(f"Voiceover file not found: {audio_file}")

    output_file = project_dir / "final.mp4"
    subprocess.run(
        build_render_command(
            concat_file=concat_file,
            subtitles_file=subtitles_file,
            audio_file=audio_file,
            output_file=output_file,
        ),
        check=True,
    )

    reel_data["status"] = "rendered"
    reel_data["rendered_at"] = utc_now()
    reel_data["outputs"]["final_video"] = "final.mp4"
    write_json(reel_path, reel_data)
    update_history(root, slug=slug, title=reel_data["title"], status="rendered")
    return output_file


def load_subtitle_cues(project_dir: str | Path) -> list[SubtitleCue]:
    project_path = Path(project_dir)
    srt_path = project_path / "subtitles.srt"
    ass_path = project_path / "subtitles.ass"

    if srt_path.exists():
        cues = parse_srt_cues(srt_path)
    elif ass_path.exists():
        cues = parse_ass_reel_sub_cues(ass_path)
    else:
        raise ReelWorkflowError(f"No subtitles.srt or subtitles.ass found in {project_path}")

    if not cues:
        raise ReelWorkflowError(f"No subtitle voice cues found in {project_path}")
    return cues


def parse_srt_cues(path: str | Path) -> list[SubtitleCue]:
    text = Path(path).read_text(encoding="utf-8").strip()
    if not text:
        return []

    cues = []
    blocks = re.split(r"\r?\n\r?\n", text)
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        start_raw, end_raw = [part.strip() for part in lines[1].split("-->", 1)]
        cues.append(
            SubtitleCue(
                index=len(cues) + 1,
                start=parse_srt_time(start_raw),
                end=parse_srt_time(end_raw),
                text=" ".join(lines[2:]).strip(),
            )
        )
    return cues


def parse_ass_reel_sub_cues(path: str | Path) -> list[SubtitleCue]:
    cues = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.startswith("Dialogue:"):
            continue
        fields = line.removeprefix("Dialogue:").strip().split(",", 9)
        if len(fields) != 10 or fields[3].strip() != "ReelSub":
            continue
        cues.append(
            SubtitleCue(
                index=len(cues) + 1,
                start=parse_ass_time(fields[1].strip()),
                end=parse_ass_time(fields[2].strip()),
                text=clean_ass_text(fields[9]),
            )
        )
    return cues


def write_timed_voiceover_from_chunks(
    cues: list[SubtitleCue],
    chunks_dir: str | Path,
    timed_dir: str | Path,
    output_wav: str | Path,
    report_path: str | Path,
) -> float:
    chunks_path = Path(chunks_dir)
    timed_path = Path(timed_dir)
    output_path = Path(output_wav)
    report = []
    concat_file = timed_path / "concat.txt"
    cursor = 0.0
    segment_number = 1

    timed_path.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with concat_file.open("w", encoding="utf-8") as concat:
        for cue in cues:
            if cue.end <= cue.start:
                raise ReelWorkflowError(f"Subtitle cue {cue.index} must have a positive duration.")
            if cue.start > cursor:
                gap_duration = cue.start - cursor
                gap_path = timed_path / f"segment_{segment_number:03d}_silence.wav"
                subprocess.run(build_silence_command(gap_path, gap_duration), check=True)
                concat.write(f"file '{escape_concat_path(gap_path)}'\n")
                report.append(
                    {
                        "type": "silence",
                        "start": cursor,
                        "end": cue.start,
                        "target_duration": gap_duration,
                        "actual_duration": ffprobe_duration(gap_path),
                    }
                )
                segment_number += 1

            source = chunks_path / f"chunk_{cue.index:03d}.wav"
            target = timed_path / f"segment_{segment_number:03d}_chunk_{cue.index:03d}.wav"
            if not source.exists():
                raise ReelWorkflowError(f"Generated TTS chunk not found: {source}")
            target_duration = cue.end - cue.start
            source_duration = ffprobe_duration(source)
            tempo = source_duration / target_duration
            subprocess.run(
                build_timed_chunk_command(
                    source_audio=source,
                    output_audio=target,
                    tempo=tempo,
                    target_duration=target_duration,
                ),
                check=True,
            )
            actual_duration = ffprobe_duration(target)
            concat.write(f"file '{escape_concat_path(target)}'\n")
            report.append(
                {
                    "type": "voice",
                    "index": cue.index,
                    "text": cue.text,
                    "start": cue.start,
                    "end": cue.end,
                    "target_duration": target_duration,
                    "source_duration": source_duration,
                    "tempo": tempo,
                    "actual_duration": actual_duration,
                    "delta": actual_duration - target_duration,
                }
            )
            cursor = cue.end
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
            str(output_path),
        ],
        check=True,
    )
    target_duration = cues[-1].end
    report.append(
        {
            "type": "output",
            "output": str(output_path),
            "target_duration": target_duration,
            "actual_duration": ffprobe_duration(output_path),
        }
    )
    Path(report_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return target_duration


def list_reel_projects(root: str | Path) -> list[dict[str, str]]:
    history_path = Path(root) / "reels" / "history.json"
    if not history_path.exists():
        return []
    history = read_json(history_path)
    return [
        {
            "slug": project["slug"],
            "status": project["status"],
            "title": project["title"],
        }
        for project in history.get("projects", [])
    ]


def write_concat_file(project_dir: Path, scenes: list[dict[str, Any]], output_path: Path) -> None:
    lines = []
    last_image = None

    for scene in scenes:
        image_path = project_dir / scene["image"]
        if not image_path.exists():
            raise ReelWorkflowError(f"Scene image not found: {image_path}")
        last_image = image_path
        lines.append(f"file '{escape_concat_path(image_path)}'")
        lines.append(f"duration {float(scene['duration_seconds']):.3f}")

    if last_image is not None:
        lines.append(f"file '{escape_concat_path(last_image)}'")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_history(root: Path, slug: str, title: str, status: str) -> None:
    reels_dir = root / "reels"
    reels_dir.mkdir(parents=True, exist_ok=True)
    history_path = reels_dir / "history.json"
    history = read_json(history_path) if history_path.exists() else {"projects": []}

    existing = None
    for project in history["projects"]:
        if project["slug"] == slug:
            existing = project
            break

    if existing is None:
        history["projects"].append(
            {
                "slug": slug,
                "status": status,
                "title": title,
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
        )
    else:
        existing["status"] = status
        existing["title"] = title
        existing["updated_at"] = utc_now()

    write_json(history_path, history)


def get_project_dir(root: str | Path, slug: str) -> Path:
    project_dir = Path(root) / "reels" / "projects" / slug
    if not project_dir.exists():
        raise ReelWorkflowError(f"Reel project not found: {project_dir}")
    return project_dir


def format_srt_time(seconds: float) -> str:
    milliseconds = int(round(seconds * 1000))
    hours = milliseconds // 3_600_000
    milliseconds %= 3_600_000
    minutes = milliseconds // 60_000
    milliseconds %= 60_000
    secs = milliseconds // 1000
    millis = milliseconds % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def parse_srt_time(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, millis = rest.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def parse_ass_time(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, centis = rest.split(".")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(centis) / 100


def clean_ass_text(value: str) -> str:
    value = re.sub(r"\{[^}]*\}", "", value)
    return value.replace(r"\N", " ").strip()


def build_atempo_filter(factor: float) -> str:
    parts = []
    while factor > 2.0:
        parts.append("atempo=2.0")
        factor /= 2.0
    while factor < 0.5:
        parts.append("atempo=0.5")
        factor /= 0.5
    parts.append(f"atempo={factor:.8f}")
    return ",".join(parts)


def ffprobe_duration(path: str | Path) -> float:
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


def write_placeholder_png(path: Path, title: str, subtitle: str, seed: int) -> None:
    width, height = 1080, 1920
    palette = [
        ((13, 25, 37), (226, 59, 46)),
        ((20, 35, 30), (44, 156, 110)),
        ((30, 28, 46), (232, 178, 62)),
        ((28, 32, 40), (88, 166, 255)),
        ((34, 30, 27), (238, 238, 230)),
    ]
    background, accent = palette[(seed - 1) % len(palette)]
    raw_rows = []

    for y in range(height):
        shade = int(18 * (y / height))
        base = tuple(min(255, channel + shade) for channel in background)

        if y in range(145, 175) or y in range(1510, 1535):
            row = bytes([0]) + bytes(accent) * width
        elif abs(y - int(height * 0.62)) < 7 or abs(y - int(height * 0.48)) < 4:
            row = bytes([0]) + bytes(accent) * width
        else:
            row = bytes([0]) + bytes(base) * width

        raw_rows.append(row)

    png_bytes = make_png(width, height, b"".join(raw_rows))
    path.write_bytes(png_bytes)

    text_path = path.with_suffix(".txt")
    text_path.write_text(f"{title}\n{subtitle}\n", encoding="utf-8")


def make_png(width: int, height: int, raw_rows: bytes) -> bytes:
    def chunk(name: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + name
            + data
            + struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            chunk(b"IHDR", header),
            chunk(b"IDAT", zlib.compress(raw_rows, level=6)),
            chunk(b"IEND", b""),
        ]
    )


def escape_concat_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace("'", "'\\''")


def escape_subtitle_filter_path(path: str | Path) -> str:
    return str(Path(path).resolve()).replace("\\", "/").replace(":", "\\:")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
