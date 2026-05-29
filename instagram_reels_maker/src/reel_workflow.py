import json
import importlib.util
import re
import shutil
import struct
import subprocess
import sys
import time
import unicodedata
import zlib
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ReelWorkflowError(RuntimeError):
    pass


AUDIO_FIRST_WORKFLOW_VERSION = "audio_first_short_line_v1"
DEFAULT_AUDIO_FIRST_LINE_GAP_SECONDS = 0.06
DEFAULT_AUDIO_FIRST_CONTINUATION_GAP_SECONDS = 0.02
DEFAULT_AUDIO_FIRST_SCENE_GAP_SECONDS = 0.12
DEFAULT_EDGE_TTS_VOICE_POOL = ["es-MX-DaliaNeural", "es-ES-AlvaroNeural"]
MAX_AUDIO_FIRST_LINE_CHARS = 75
MAX_AUDIO_FIRST_LINE_WORDS = 9
DEFAULT_REEL_PUBLISH_PORT = 8765
REEL_PUBLISH_HASHTAGS = [
    "#DivisasCOL",
    "#DolarColombia",
    "#PesoColombiano",
    "#USDCOP",
    "#Dolar",
    "#Colombia",
    "#EconomiaColombiana",
    "#MercadoCambiario",
    "#FinanzasPersonales",
    "#FinanzasColombia",
    "#NoticiasEconomicas",
    "#AnalisisEconomico",
    "#DolarHoy",
    "#ReelsColombia",
]
HASHTAG_STOPWORDS = {
    "para",
    "pero",
    "como",
    "esta",
    "este",
    "estos",
    "estas",
    "sobre",
    "entre",
    "cuando",
    "donde",
    "desde",
    "porque",
    "solo",
    "bajo",
}


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


@dataclass(frozen=True)
class AudioFirstTimeline:
    cues: list[SubtitleCue]
    target_duration: float
    voiceover: Path
    timing_report: Path


@dataclass(frozen=True)
class AudioFirstResult:
    voice_lines: Path
    raw_voiceover: Path
    clean_voiceover: Path
    output_video: Path
    subtitles_path: Path
    timing_report: Path
    target_duration: float


@dataclass(frozen=True)
class ReelPublishResult:
    manifest_path: Path
    state_path: Path
    caption_path: Path
    publish_script_path: Path
    video_path: Path
    video_url: str
    published_id: str | None = None
    creation_id: str | None = None


DAILY_FX_SCENES = [
    {
        "id": "hook",
        "duration_seconds": 3.5,
        "subtitle": "El dólar no se mueve solo.",
        "voiceover_lines": ["El dólar no se mueve solo."],
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
        "voiceover_lines": ["Cuando el Gobierno gasta más,", "la moneda paga la factura."],
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
        "voiceover_lines": ["La pregunta real:", "¿cuánto compra tu salario hoy?"],
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
        "voiceover_lines": ["El mercado castiga el relato", "cuando no ve disciplina."],
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
        "voiceover_lines": ["Dólar arriba o abajo esta semana.", "Te leo."],
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

        write_text_lf(prompts_dir / prompt_name, scene["visual_prompt"])
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
        "workflow_version": AUDIO_FIRST_WORKFLOW_VERSION,
        "template": template,
        "niche": template_data["niche"],
        "format": template_data["format"],
        "created_at": utc_now(),
        "voiceover": {
            "mode": "audio_first_short_lines",
            "file": "audio_first/voiceover_natural.wav",
            "clean_file": "audio_first/voiceover_natural_clean.wav",
            "script_file": "script.txt",
            "voice_lines_file": "audio_first_voice_lines.txt",
            "line_gap_seconds": DEFAULT_AUDIO_FIRST_LINE_GAP_SECONDS,
            "scene_gap_seconds": DEFAULT_AUDIO_FIRST_SCENE_GAP_SECONDS,
        },
        "scenes": scenes,
        "cta": template_data["cta"],
        "outputs": {},
    }

    reel_json = project_dir / "reel.json"
    script_path = project_dir / "script.txt"
    subtitles_path = project_dir / "subtitles.srt"

    write_json(reel_json, reel_data)
    write_text_lf(script_path, build_script_from_scenes(scenes))
    write_text_lf(subtitles_path, generate_subtitles(scenes))
    update_history(root, slug=slug, title=reel_data["title"], status="draft")

    return ReelProject(
        slug=slug,
        project_dir=project_dir,
        reel_json=reel_json,
        script_path=script_path,
        subtitles_path=subtitles_path,
    )


def build_script_from_scenes(scenes: list[dict[str, Any]]) -> str:
    lines = []
    for scene in scenes:
        voiceover_lines = scene.get("voiceover_lines")
        if voiceover_lines:
            lines.extend(str(line).strip() for line in voiceover_lines)
        else:
            lines.append(scene.get("voiceover_text", "").strip())
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


def generate_subtitles_from_cues(cues: list[SubtitleCue]) -> str:
    blocks = []
    for index, cue in enumerate(cues, start=1):
        blocks.append(
            f"{index}\n{format_srt_time(cue.start)} --> {format_srt_time(cue.end)}\n{cue.text}\n"
        )
    return "\n".join(blocks).strip() + "\n"


def ends_complete_sentence(text: str) -> bool:
    return text.rstrip().endswith((".", "!", "?", "…"))


def regenerate_subtitles(root: str | Path, slug: str) -> Path:
    project_dir = get_project_dir(root, slug)
    reel_data = read_json(project_dir / "reel.json")
    subtitles_path = project_dir / "subtitles.srt"
    write_text_lf(subtitles_path, generate_subtitles(reel_data["scenes"]))
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
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(input_audio),
        "-af",
        filters,
        "-ar",
        "48000",
        "-ac",
        "1",
        str(output_audio),
    ]


def build_trim_silence_command(
    input_audio: str | Path,
    output_audio: str | Path,
    sample_rate: int = 24000,
    noise_threshold: str = "-45dB",
    min_silence_duration: float = 0.03,
) -> list[str]:
    filters = (
        f"silenceremove=start_periods=1:start_duration={min_silence_duration:.3f}:"
        f"start_threshold={noise_threshold}:stop_periods=-1:"
        f"stop_duration={min_silence_duration:.3f}:stop_threshold={noise_threshold},"
        "asetpts=N/SR/TB"
    )
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(input_audio),
        "-af",
        filters,
        "-ar",
        str(sample_rate),
        "-ac",
        "1",
        str(output_audio),
    ]


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


def build_concat_audio_command(concat_file: str | Path, output_audio: str | Path) -> list[str]:
    return [
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


def validate_short_voiceover_lines(scenes: list[dict[str, Any]]) -> None:
    for scene_index, scene in enumerate(scenes, start=1):
        lines = scene.get("voiceover_lines")
        scene_id = scene.get("id", scene_index)
        if not isinstance(lines, list) or not lines:
            raise ReelWorkflowError(f"Scene {scene_id} must define non-empty voiceover_lines.")

        for line_index, line in enumerate(lines, start=1):
            text = str(line).strip()
            if not text:
                raise ReelWorkflowError(f"Scene {scene_id} voiceover line {line_index} is empty.")
            if len(text) > MAX_AUDIO_FIRST_LINE_CHARS:
                raise ReelWorkflowError(
                    f"Scene {scene_id} voiceover line {line_index} must be "
                    f"{MAX_AUDIO_FIRST_LINE_CHARS} characters or fewer."
                )

            word_count = len(re.findall(r"\b[\wáéíóúÁÉÍÓÚñÑ]+\b", text))
            if word_count > MAX_AUDIO_FIRST_LINE_WORDS:
                raise ReelWorkflowError(
                    f"Scene {scene_id} voiceover line {line_index} must be "
                    f"{MAX_AUDIO_FIRST_LINE_WORDS} words or fewer."
                )


def flatten_voiceover_lines(scenes: list[dict[str, Any]]) -> list[str]:
    lines = []
    for scene in scenes:
        lines.extend(str(line).strip() for line in scene.get("voiceover_lines", []) if str(line).strip())
    return lines


def generate_tts_chunks(
    backend: str,
    voice_lines: str | Path,
    sample_dir: str | Path,
    voice_wav: str | Path | None = None,
    voice_name: str | None = None,
    voice_pool: list[str] | None = None,
    sapi_rate: int = 0,
) -> None:
    backend_name = backend.lower().replace("_", "-")
    voice_lines_path = Path(voice_lines)
    sample_path = Path(sample_dir)
    chunks_dir = sample_path / "chunks"

    if backend_name in {"windows-sapi", "sapi"}:
        lines = [line.strip() for line in voice_lines_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        generate_windows_sapi_chunks(lines, chunks_dir, voice_name=voice_name, rate=sapi_rate)
        return

    if backend_name in {"edge-tts", "edge"}:
        lines = [line.strip() for line in voice_lines_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        generate_edge_tts_chunks(lines, chunks_dir, voice_pool=voice_pool)
        return

    if backend_name != "xtts":
        raise ReelWorkflowError(f"Unknown TTS backend: {backend}")
    if voice_wav is None:
        raise ReelWorkflowError("XTTS audio-first generation requires --voice.")

    voice_path = Path(voice_wav)
    if not voice_path.exists():
        raise ReelWorkflowError(f"Voice WAV file not found: {voice_path}")

    generator = Path(__file__).resolve().parents[1] / "generate_voiceover.py"
    subprocess.run(
        [
            sys.executable,
            str(generator),
            "--txt",
            str(voice_lines_path),
            "--voice",
            str(voice_path),
            "--out-dir",
            str(sample_path),
            "--format",
            "wav",
            "--silence-ms",
            "0",
        ],
        check=True,
    )


async def save_edge_tts_mp3(text: str, voice_name: str, output_path: Path) -> None:
    try:
        import edge_tts  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ReelWorkflowError(
            "Edge neural TTS requires edge-tts. Install instagram_reels_maker requirements first."
        ) from exc

    communicate = edge_tts.Communicate(text, voice_name)
    await communicate.save(str(output_path))


def generate_edge_tts_chunks(
    lines: list[str],
    chunks_dir: str | Path,
    voice_pool: list[str] | None = None,
    sample_rate: int = 24000,
) -> None:
    if not lines:
        raise ReelWorkflowError("No voiceover lines found for Edge TTS generation.")

    voices = [voice.strip() for voice in (voice_pool or DEFAULT_EDGE_TTS_VOICE_POOL) if voice.strip()]
    if not voices:
        raise ReelWorkflowError("Edge TTS voice pool must include at least one voice.")

    chunks_path = Path(chunks_dir)
    chunks_path.mkdir(parents=True, exist_ok=True)
    assignments = []

    sentence_index = 0
    for index, line in enumerate(lines, start=1):
        voice_name = voices[sentence_index % len(voices)]
        mp3_path = chunks_path / f"chunk_{index:03d}_edge.mp3"
        raw_wav_path = chunks_path / f"chunk_{index:03d}_raw.wav"
        output_path = chunks_path / f"chunk_{index:03d}.wav"
        asyncio.run(save_edge_tts_mp3(line, voice_name, mp3_path))
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(mp3_path),
                "-ar",
                str(sample_rate),
                "-ac",
                "1",
                str(raw_wav_path),
            ],
            check=True,
        )
        subprocess.run(build_trim_silence_command(raw_wav_path, output_path, sample_rate=sample_rate), check=True)
        mp3_path.unlink(missing_ok=True)
        raw_wav_path.unlink(missing_ok=True)
        assignments.append(
            {
                "index": index,
                "sentence_index": sentence_index + 1,
                "text": line,
                "voice": voice_name,
                "source": str(output_path),
            }
        )
        if ends_complete_sentence(line):
            sentence_index += 1

    write_text_lf(chunks_path / "voice_assignments.json", json.dumps(assignments, ensure_ascii=False, indent=2) + "\n")


def generate_windows_sapi_chunks(
    lines: list[str],
    chunks_dir: str | Path,
    voice_name: str | None = None,
    rate: int = 0,
    volume: int = 100,
    sample_rate: int = 24000,
) -> None:
    if not lines:
        raise ReelWorkflowError("No voiceover lines found for Windows SAPI generation.")

    try:
        import win32com.client  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ReelWorkflowError(
            "Windows SAPI TTS requires pywin32. Install instagram_reels_maker requirements first."
        ) from exc

    chunks_path = Path(chunks_dir)
    chunks_path.mkdir(parents=True, exist_ok=True)
    voice = win32com.client.Dispatch("SAPI.SpVoice")
    selected_voice = select_windows_sapi_voice(voice, voice_name)
    if selected_voice is not None:
        voice.Voice = selected_voice
    voice.Rate = rate
    voice.Volume = volume

    for index, line in enumerate(lines, start=1):
        raw_path = chunks_path / f"chunk_{index:03d}_sapi.wav"
        output_path = chunks_path / f"chunk_{index:03d}.wav"
        stream = win32com.client.Dispatch("SAPI.SpFileStream")
        stream.Open(str(raw_path), 3, False)
        try:
            voice.AudioOutputStream = stream
            voice.Speak(line)
        finally:
            stream.Close()

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(raw_path),
                "-ar",
                str(sample_rate),
                "-ac",
                "1",
                str(output_path),
            ],
            check=True,
        )
        raw_path.unlink(missing_ok=True)


def select_windows_sapi_voice(voice: Any, voice_name: str | None = None) -> Any | None:
    tokens = list(voice.GetVoices())
    if not tokens:
        return None

    if voice_name:
        wanted = voice_name.lower()
        for token in tokens:
            if wanted in token.GetDescription().lower():
                return token
        raise ReelWorkflowError(f"Windows SAPI voice not found: {voice_name}")

    return max(tokens, key=score_windows_sapi_voice)


def score_windows_sapi_voice(token: Any) -> int:
    description = token.GetDescription().lower()
    score = 0

    if any(marker in description for marker in ("spanish", "espanol", "español", "es-")):
        score += 100
    if any(marker in description for marker in ("natural", "neural", "online")):
        score += 50
    if "helena" in description:
        score += 30
    if "sabina" in description:
        score += 25
    if "pablo" in description:
        score += 20
    if "desktop" in description:
        score -= 5

    return score


def build_audio_first_voiceover(
    scenes: list[dict[str, Any]],
    chunks_dir: str | Path,
    output_wav: str | Path,
    report_path: str | Path,
    line_gap_seconds: float = DEFAULT_AUDIO_FIRST_LINE_GAP_SECONDS,
    continuation_gap_seconds: float = DEFAULT_AUDIO_FIRST_CONTINUATION_GAP_SECONDS,
    scene_gap_seconds: float = DEFAULT_AUDIO_FIRST_SCENE_GAP_SECONDS,
) -> AudioFirstTimeline:
    validate_short_voiceover_lines(scenes)

    chunks_path = Path(chunks_dir)
    output_path = Path(output_wav)
    report_file = Path(report_path)
    segments_dir = output_path.parent / "segments"
    concat_file = segments_dir / "concat.txt"
    cues = []
    report = []
    cursor = 0.0
    chunk_index = 1
    segment_index = 1

    segments_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with concat_file.open("w", encoding="utf-8") as concat:
        for scene_index, scene in enumerate(scenes):
            scene_start = cursor
            scene_lines = [str(line).strip() for line in scene["voiceover_lines"] if str(line).strip()]

            for line_index, line in enumerate(scene_lines):
                source = chunks_path / f"chunk_{chunk_index:03d}.wav"
                if not source.exists():
                    raise ReelWorkflowError(f"Generated TTS chunk not found: {source}")

                duration = ffprobe_duration(source)
                if duration <= 0:
                    raise ReelWorkflowError(f"Generated TTS chunk has no duration: {source}")

                start = round(cursor, 6)
                end = round(cursor + duration, 6)
                concat.write(f"file '{escape_concat_path(source)}'\n")
                cues.append(SubtitleCue(index=len(cues) + 1, start=start, end=end, text=line))
                report.append(
                    {
                        "type": "voice",
                        "index": chunk_index,
                        "scene_id": scene.get("id", scene_index + 1),
                        "text": line,
                        "start": start,
                        "end": end,
                        "duration": duration,
                        "source": str(source),
                    }
                )
                cursor = end
                chunk_index += 1
                segment_index += 1

                if line_index < len(scene_lines) - 1:
                    gap_seconds = line_gap_seconds if ends_complete_sentence(line) else continuation_gap_seconds
                    gap_scope = "line" if ends_complete_sentence(line) else "continuation"
                    gap_path = segments_dir / f"segment_{segment_index:03d}_silence.wav"
                    subprocess.run(build_silence_command(gap_path, gap_seconds), check=True)
                    concat.write(f"file '{escape_concat_path(gap_path)}'\n")
                    report.append(
                        {
                            "type": "silence",
                            "scope": gap_scope,
                            "start": cursor,
                            "end": round(cursor + gap_seconds, 6),
                            "target_duration": gap_seconds,
                            "source": str(gap_path),
                        }
                    )
                    cursor = round(cursor + gap_seconds, 6)
                    segment_index += 1

            if scene_index < len(scenes) - 1:
                gap_path = segments_dir / f"segment_{segment_index:03d}_silence.wav"
                subprocess.run(build_silence_command(gap_path, scene_gap_seconds), check=True)
                concat.write(f"file '{escape_concat_path(gap_path)}'\n")
                report.append(
                    {
                        "type": "silence",
                        "scope": "scene",
                        "start": cursor,
                        "end": round(cursor + scene_gap_seconds, 6),
                        "target_duration": scene_gap_seconds,
                        "source": str(gap_path),
                    }
                )
                cursor = round(cursor + scene_gap_seconds, 6)
                segment_index += 1

            scene["start_seconds"] = round(scene_start, 6)
            scene["end_seconds"] = round(cursor, 6)
            scene["duration_seconds"] = round(cursor - scene_start, 6)
            scene["subtitle"] = " ".join(scene_lines)

    subprocess.run(build_concat_audio_command(concat_file, output_path), check=True)
    measured_duration = ffprobe_duration(output_path)
    target_duration = round(measured_duration, 6)
    report.append(
        {
            "type": "output",
            "output": str(output_path),
            "target_duration": target_duration,
            "actual_duration": measured_duration,
        }
    )
    write_text_lf(report_file, json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    return AudioFirstTimeline(
        cues=cues,
        target_duration=target_duration,
        voiceover=output_path,
        timing_report=report_file,
    )


def generate_audio_first_final(
    root: str | Path,
    slug: str,
    voice_wav: str | Path | None = None,
    draft_video: str | Path | None = None,
    output_video: str | Path | None = None,
    sample_dir_name: str = "audio_first",
    tts_backend: str = "windows-sapi",
    voice_name: str | None = None,
    voice_pool: list[str] | None = None,
    sapi_rate: int = 0,
) -> AudioFirstResult:
    root = Path(root)
    project_dir = get_project_dir(root, slug)
    reel_path = project_dir / "reel.json"
    reel_data = read_json(reel_path)
    scenes = reel_data["scenes"]
    validate_short_voiceover_lines(scenes)

    output_path = Path(output_video) if output_video is not None else project_dir / "final" / "final_audio_first.mp4"
    sample_dir = project_dir / sample_dir_name
    chunks_dir = sample_dir / "chunks"
    voice_lines = project_dir / "audio_first_voice_lines.txt"
    raw_voiceover = sample_dir / "voiceover_natural.wav"
    clean_voiceover = sample_dir / "voiceover_natural_clean.wav"
    timing_report = sample_dir / "timing_report.json"
    subtitles_path = project_dir / "subtitles.srt"

    sample_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_text_lf(voice_lines, "\n".join(flatten_voiceover_lines(scenes)) + "\n")
    generate_tts_chunks(
        backend=tts_backend,
        voice_lines=voice_lines,
        sample_dir=sample_dir,
        voice_wav=voice_wav,
        voice_name=voice_name,
        voice_pool=voice_pool,
        sapi_rate=sapi_rate,
    )

    timeline = build_audio_first_voiceover(
        scenes=scenes,
        chunks_dir=chunks_dir,
        output_wav=raw_voiceover,
        report_path=timing_report,
    )
    cleanup_audio_first_text_intermediates(sample_dir)
    write_text_lf(subtitles_path, generate_subtitles_from_cues(timeline.cues))
    subprocess.run(build_clean_audio_command(raw_voiceover, clean_voiceover), check=True)
    build_audio_first_render(
        project_dir=project_dir,
        scenes=scenes,
        subtitles_path=subtitles_path,
        clean_voiceover=clean_voiceover,
        output_video=output_path,
    )

    reel_data["workflow_version"] = AUDIO_FIRST_WORKFLOW_VERSION
    reel_data["status"] = "rendered"
    reel_data["target_duration_seconds"] = timeline.target_duration
    reel_data["voiceover"] = {
        **reel_data.get("voiceover", {}),
        "mode": "audio_first_short_lines",
        "file": f"{sample_dir_name}/voiceover_natural.wav",
        "clean_file": f"{sample_dir_name}/voiceover_natural_clean.wav",
        "script_file": "script.txt",
        "voice_lines_file": "audio_first_voice_lines.txt",
        "timing_report": f"{sample_dir_name}/timing_report.json",
        "tts_backend": tts_backend,
        "voice_name": voice_name,
        "voice_pool": voice_pool if voice_pool is not None else DEFAULT_EDGE_TTS_VOICE_POOL if tts_backend.lower().replace("_", "-") in {"edge-tts", "edge"} else None,
        "line_gap_seconds": DEFAULT_AUDIO_FIRST_LINE_GAP_SECONDS,
        "continuation_gap_seconds": DEFAULT_AUDIO_FIRST_CONTINUATION_GAP_SECONDS,
        "scene_gap_seconds": DEFAULT_AUDIO_FIRST_SCENE_GAP_SECONDS,
    }
    reel_data.setdefault("outputs", {})
    reel_data["outputs"]["audio_first_video"] = str(output_path.relative_to(project_dir)).replace("\\", "/")
    reel_data["outputs"]["audio_first_render_manifest"] = "render/audio_first_concat.txt"
    if draft_video is not None:
        reel_data["outputs"]["legacy_draft_video"] = str(Path(draft_video).relative_to(project_dir)).replace("\\", "/")
    reel_data["rendered_at"] = utc_now()
    write_json(reel_path, reel_data)
    update_history(root, slug=slug, title=reel_data["title"], status="rendered")

    return AudioFirstResult(
        voice_lines=voice_lines,
        raw_voiceover=raw_voiceover,
        clean_voiceover=clean_voiceover,
        output_video=output_path,
        subtitles_path=subtitles_path,
        timing_report=timing_report,
        target_duration=timeline.target_duration,
    )


def build_audio_first_render(
    project_dir: str | Path,
    scenes: list[dict[str, Any]],
    subtitles_path: str | Path,
    clean_voiceover: str | Path,
    output_video: str | Path,
) -> Path:
    project_path = Path(project_dir)
    subtitles_file = Path(subtitles_path)
    audio_file = Path(clean_voiceover)
    output_path = Path(output_video)
    concat_file = project_path / "render" / "audio_first_concat.txt"

    if not audio_file.exists():
        raise ReelWorkflowError(f"Clean voiceover file not found: {audio_file}")
    if not subtitles_file.exists():
        raise ReelWorkflowError(f"Subtitles file not found: {subtitles_file}")

    write_concat_file(project_path, scenes, concat_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        build_render_command(
            concat_file=concat_file,
            subtitles_file=subtitles_file,
            audio_file=audio_file,
            output_file=output_path,
        ),
        check=True,
    )
    return output_path


def cleanup_audio_first_text_intermediates(sample_dir: str | Path) -> list[str]:
    sample_path = Path(sample_dir)
    removed = []
    for path in [sample_path / "voiceover_script.txt", sample_path / "segments" / "concat.txt"]:
        if path.exists():
            path.unlink()
            removed.append(str(path.relative_to(sample_path)).replace("\\", "/"))

    chunks_dir = sample_path / "chunks"
    if chunks_dir.exists():
        for path in chunks_dir.glob("chunk_*.txt"):
            path.unlink()
            removed.append(str(path.relative_to(sample_path)).replace("\\", "/"))

    return removed


def cleanup_stale_reel_artifacts(project_dir: str | Path) -> list[str]:
    project_path = Path(project_dir)
    removed = []

    stale_dirs = [
        "tts_timed_sample",
        "tts_ass_line_sample",
        "tts_srt_line_sample",
        "chunks",
        "render/clips",
    ]
    stale_files = [
        "srt_voice_lines.txt",
        "ass_voice_lines.txt",
        "tts_timed_voice_lines.txt",
        "voiceover_script.txt",
        "subtitles.ass",
        "render/subtitle_filter.txt",
        "render/clips.txt",
        "render/concat.txt",
        "render/video_only.mp4",
        "render/render_cards.py",
        "render/overlay_headlines.py",
        "drafts/final.mp4",
        "drafts/final_timed_tts.mp4",
        "drafts/final_timed_tts_exact.mp4",
    ]

    for directory in stale_dirs:
        path = project_path / directory
        if path.exists():
            shutil.rmtree(path)
            removed.append(directory)

    for pattern in ["drafts/preview_*.png", "render/preview_*.png"]:
        for path in project_path.glob(pattern):
            if path.is_file():
                path.unlink()
                removed.append(str(path.relative_to(project_path)).replace("\\", "/"))

    for filename in stale_files:
        path = project_path / filename
        if path.exists():
            path.unlink()
            removed.append(filename)

    return removed


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
    write_text_lf(voice_lines, "\n".join(cue.text for cue in cues) + "\n")

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
        "fps=30,"
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        f"subtitles='{subtitle_filter}':force_style='FontName=Arial,FontSize=12,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=1.5,"
        "Alignment=2,MarginV=80'"
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


def prepare_reel_publish(
    root: str | Path,
    slug: str,
    base_url: str | None = None,
) -> ReelPublishResult:
    project_dir = get_project_dir(root, slug)
    reel_path = project_dir / "reel.json"
    reel_data = read_json(reel_path)
    video_path = project_dir / reel_data.get("outputs", {}).get("audio_first_video", "final/final_audio_first.mp4")
    if not video_path.exists():
        raise ReelWorkflowError(
            f"Final audio-first reel not found: {video_path}. Run audio-first-final before publishing."
        )

    caption = build_reel_publish_caption(reel_data)
    caption_path = project_dir / "caption.txt"
    write_text_lf(caption_path, caption + "\n")

    final_dir = project_dir / "final"
    manifest_path = final_dir / "publish-manifest.json"
    state_path = final_dir / "publish-state.json"
    publish_script_path = final_dir / "publish-script.txt"
    video_url = build_public_file_url(base_url, video_path.name)
    manifest = {
        "project": slug,
        "title": reel_data.get("title", slug),
        "media_type": "REELS",
        "source_reel": str(reel_path.relative_to(Path(root))).replace("\\", "/"),
        "public_path": str(video_path.relative_to(Path(root))).replace("\\", "/"),
        "video_url": video_url,
        "caption": caption,
        "prepared_at": utc_now(),
    }
    write_json(manifest_path, manifest)
    write_text_lf(
        publish_script_path,
        "\n".join(
            [
                f"Project: {slug}",
                f"Video: {video_path}",
                f"Manifest: {manifest_path}",
                "",
                "Publish command:",
                f"python reel_maker.py publish-reel --project {slug}",
                "",
                "Caption:",
                caption,
                "",
            ]
        ),
    )

    reel_data.setdefault("outputs", {})
    reel_data["outputs"]["publish_manifest"] = str(manifest_path.relative_to(project_dir)).replace("\\", "/")
    reel_data["outputs"]["publish_script"] = str(publish_script_path.relative_to(project_dir)).replace("\\", "/")
    reel_data["outputs"]["publish_caption"] = "caption.txt"
    write_json(reel_path, reel_data)

    return ReelPublishResult(
        manifest_path=manifest_path,
        state_path=state_path,
        caption_path=caption_path,
        publish_script_path=publish_script_path,
        video_path=video_path,
        video_url=video_url,
    )


def publish_reel(
    root: str | Path,
    slug: str,
    tunnel_provider: str = "auto",
    reset_state: bool = False,
    dry_run: bool = False,
) -> ReelPublishResult:
    workflow_root = Path(root).resolve()
    repo_root = workflow_root.parent
    publish_module = load_instagram_publish_module(workflow_root)
    publish_module.load_dotenv(repo_root / ".env")
    prepared = prepare_reel_publish(workflow_root, slug)

    if dry_run:
        return prepared
    if not publish_module.validate_config():
        raise ReelWorkflowError("Missing Instagram publishing configuration.")

    if reset_state and prepared.state_path.exists():
        prepared.state_path.unlink()
    state = read_reel_publish_state(prepared.state_path)
    if state.get("published_id") and not reset_state:
        return ReelPublishResult(
            manifest_path=prepared.manifest_path,
            state_path=prepared.state_path,
            caption_path=prepared.caption_path,
            publish_script_path=prepared.publish_script_path,
            video_path=prepared.video_path,
            video_url=state.get("video_url", prepared.video_url),
            published_id=state.get("published_id"),
            creation_id=state.get("creation_id"),
        )

    final_dir = prepared.video_path.parent
    server = publish_module.run_http_server(final_dir, DEFAULT_REEL_PUBLISH_PORT)
    tunnel = None
    try:
        tunnel, public_url = publish_module.start_tunnel_for_publish(
            repo_root,
            DEFAULT_REEL_PUBLISH_PORT,
            tunnel_provider,
            timeout_seconds=publish_module.DEFAULT_TUNNEL_TIMEOUT_SECONDS,
        )
        video_url = build_public_file_url(public_url, prepared.video_path.name)
        manifest = read_json(prepared.manifest_path)
        manifest["video_url"] = video_url
        manifest["public_base_url"] = public_url
        manifest["prepared_at"] = utc_now()
        write_json(prepared.manifest_path, manifest)

        wait_for_public_video(publish_module, video_url)
        creation_id = create_reel_container(
            publish_module=publish_module,
            ig_user_id=publish_module.os.environ["INSTAGRAM_USER_ID"],
            token=publish_module.os.environ["META_PAGE_ACCESS_TOKEN"],
            video_url=video_url,
            caption=manifest["caption"],
        )
        publish_module.wait_for_container_finished(creation_id, publish_module.os.environ["META_PAGE_ACCESS_TOKEN"])
        publish_result = publish_module.publish_container(
            publish_module.os.environ["INSTAGRAM_USER_ID"],
            publish_module.os.environ["META_PAGE_ACCESS_TOKEN"],
            creation_id,
        )
        published_id = str(publish_result.get("id", ""))
        write_json(
            prepared.state_path,
            {
                "project": slug,
                "published_id": published_id,
                "creation_id": creation_id,
                "video_url": video_url,
                "published_at": utc_now(),
            },
        )
        return ReelPublishResult(
            manifest_path=prepared.manifest_path,
            state_path=prepared.state_path,
            caption_path=prepared.caption_path,
            publish_script_path=prepared.publish_script_path,
            video_path=prepared.video_path,
            video_url=video_url,
            published_id=published_id,
            creation_id=creation_id,
        )
    finally:
        if tunnel and tunnel.poll() is None:
            publish_module.terminate_process(tunnel)
        server.shutdown()


def build_reel_publish_caption(reel_data: dict[str, Any]) -> str:
    title = str(reel_data.get("title") or reel_data.get("slug") or "Reel Divisas COL").strip()
    lines = flatten_voiceover_lines(reel_data.get("scenes", []))
    spoken = summarize_voiceover_for_caption(lines)
    body = (
        f"{title}\n\n"
        f"{spoken}\n\n"
        "Análisis rápido de Divisas COL para leer mejor el dólar, el peso colombiano "
        "y las señales que está mirando el mercado.\n\n"
        "Guárdalo y compártelo con alguien que siga el dólar en Colombia.\n"
        "Fuente: divisascol.com\n\n"
        ".\n.\n.\n.\n.\n.\n\n"
    )
    return body + " ".join(build_reel_hashtags(reel_data))


def build_reel_hashtags(reel_data: dict[str, Any], max_hashtags: int = 30) -> list[str]:
    hashtags = list(REEL_PUBLISH_HASHTAGS)
    text_parts = [str(reel_data.get("title") or ""), str(reel_data.get("slug") or "").replace("-", " ")]
    words = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]+", " ".join(text_parts))
    for word in words:
        normalized = normalize_hashtag_word(word)
        if len(normalized) < 4 or normalized.lower() in HASHTAG_STOPWORDS or any(char.isdigit() for char in normalized):
            continue
        hashtag = f"#{normalized}"
        if hashtag not in hashtags:
            hashtags.append(hashtag)
        if len(hashtags) >= max_hashtags:
            break
    return hashtags[:max_hashtags]


def summarize_voiceover_for_caption(lines: list[str], max_chars: int = 420) -> str:
    summary_lines: list[str] = []
    for line in lines:
        candidate = " ".join([*summary_lines, line])
        if len(candidate) > max_chars:
            break
        summary_lines.append(line)
    if summary_lines:
        return " ".join(summary_lines)
    fallback = " ".join(lines)
    if len(fallback) <= max_chars:
        return fallback
    fallback = fallback[: max_chars - 3].rsplit(" ", 1)[0].rstrip()
    return f"{fallback}..."


def normalize_hashtag_word(value: str) -> str:
    text = unicodedata.normalize("NFKD", value)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^A-Za-z0-9]", "", text)
    return text[:1].upper() + text[1:] if text else ""


def build_public_file_url(base_url: str | None, filename: str) -> str:
    if not base_url:
        return ""
    return f"{base_url.rstrip('/')}/{filename}"


def load_instagram_publish_module(workflow_root: str | Path) -> Any:
    module_path = Path(workflow_root).resolve().parent / "instagram_publish.py"
    if not module_path.exists():
        raise ReelWorkflowError(f"Instagram publish helper not found: {module_path}")
    spec = importlib.util.spec_from_file_location("instagram_publish", module_path)
    if spec is None or spec.loader is None:
        raise ReelWorkflowError(f"Could not load Instagram publish helper: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def wait_for_public_video(publish_module: Any, video_url: str, timeout_seconds: int = 300) -> None:
    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        try:
            response = publish_module.requests.get(video_url, headers={"Range": "bytes=0-1023"}, timeout=15)
            content_type = response.headers.get("content-type", "").lower()
            if response.ok and (content_type.startswith("video/") or content_type == "application/octet-stream"):
                return
            last_error = f"HTTP {response.status_code} {content_type}"
        except publish_module.requests.RequestException as exc:
            last_error = str(exc)
        time.sleep(3)
    raise ReelWorkflowError(f"Public reel URL never became reachable as video: {video_url}. Last error: {last_error}")


def create_reel_container(
    publish_module: Any,
    ig_user_id: str,
    token: str,
    video_url: str,
    caption: str,
) -> str:
    response = publish_module.post_with_meta_retry(
        publish_module.graph_url(f"{ig_user_id}/media"),
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": publish_module.sanitize_caption(caption),
            "share_to_feed": "true",
            "access_token": token,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["id"]


def read_reel_publish_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        state = read_json(path)
    except (json.JSONDecodeError, OSError):
        return {}
    return state if isinstance(state, dict) else {}


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
    write_text_lf(Path(report_path), json.dumps(report, indent=2))
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
    write_text_lf(output_path, "\n".join(lines) + "\n")


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
    write_text_lf(text_path, f"{title}\n{subtitle}\n")


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
    write_text_lf(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def write_text_lf(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
