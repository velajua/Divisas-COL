import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
REEL_SRC = REPO_ROOT / "instagram_reels_maker" / "src"
sys.path.insert(0, str(REEL_SRC))

import reel_workflow
from reel_workflow import (
    ReelWorkflowError,
    build_exact_timed_finalize_audio_command,
    build_silence_command,
    build_timed_chunk_command,
    build_clean_audio_command,
    build_finalize_audio_command,
    build_render_command,
    create_reel_project,
    finalize_audio,
    generate_timed_tts_final,
    generate_subtitles,
    list_reel_projects,
    load_subtitle_cues,
)


def test_create_daily_fx_project_writes_structure_and_history(tmp_path: Path):
    root = tmp_path / "voiceover"

    project = create_reel_project(
        root=root,
        slug="peso-watch-2026-05-19",
        template="daily_fx",
        title="Peso Watch",
    )

    project_dir = root / "reels" / "projects" / "peso-watch-2026-05-19"
    reel_json = json.loads((project_dir / "reel.json").read_text(encoding="utf-8"))
    history = json.loads((root / "reels" / "history.json").read_text(encoding="utf-8"))

    assert project.slug == "peso-watch-2026-05-19"
    assert reel_json["status"] == "draft"
    assert reel_json["format"] == "daily_fx_comparison"
    assert len(reel_json["scenes"]) == 5
    assert (project_dir / "script.txt").read_text(encoding="utf-8").startswith(
        "El dólar no se mueve solo."
    )
    assert (project_dir / "subtitles.srt").exists()
    assert (project_dir / "images" / "001_hook.png").exists()
    assert (project_dir / "prompts" / "001_hook.txt").exists()
    assert history["projects"][0]["slug"] == "peso-watch-2026-05-19"
    assert history["projects"][0]["status"] == "draft"


def test_create_project_refuses_to_overwrite_existing_project(tmp_path: Path):
    root = tmp_path / "voiceover"
    create_reel_project(root=root, slug="peso-watch", template="daily_fx")

    with pytest.raises(ReelWorkflowError, match="already exists"):
        create_reel_project(root=root, slug="peso-watch", template="daily_fx")


def test_generate_subtitles_uses_scene_durations():
    scenes = [
        {"id": "hook", "duration_seconds": 2.5, "subtitle": "El peso perdió poder."},
        {"id": "data", "duration_seconds": 3, "subtitle": "Un dólar compra más pesos."},
    ]

    subtitles = generate_subtitles(scenes)

    assert "00:00:00,000 --> 00:00:02,500" in subtitles
    assert "El peso perdió poder." in subtitles
    assert "00:00:02,500 --> 00:00:05,500" in subtitles
    assert "Un dólar compra más pesos." in subtitles


def test_load_subtitle_cues_reads_srt_timing_and_text(tmp_path: Path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "subtitles.srt").write_text(
        "\n".join(
            [
                "1",
                "00:00:00,000 --> 00:00:02,700",
                "Caja en dolares, deuda externa",
                "",
                "2",
                "00:00:02,700 --> 00:00:05,741",
                "y un peso otra vez en alerta.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    cues = load_subtitle_cues(project_dir)

    assert [(cue.index, cue.start, cue.end, cue.text) for cue in cues] == [
        (1, 0.0, 2.7, "Caja en dolares, deuda externa"),
        (2, 2.7, 5.741, "y un peso otra vez en alerta."),
    ]


def test_load_subtitle_cues_falls_back_to_ass_reelsub_events(tmp_path: Path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "subtitles.ass").write_text(
        "\n".join(
            [
                "[Events]",
                "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
                "Dialogue: 2,0:00:00.25,0:00:08.15,DataKicker,,0,0,0,,RIESGO ELECTORAL",
                "Dialogue: 0,0:00:00.00,0:00:04.25,ReelSub,,0,0,0,,Oxford Economics puso numeros\\Nal riesgo electoral",
                "Dialogue: 0,0:00:04.25,0:00:08.17,ReelSub,,0,0,0,,De la Espriella o Cepeda no moverian\\Nigual la economia.",
            ]
        ),
        encoding="utf-8",
    )

    cues = load_subtitle_cues(project_dir)

    assert [(cue.index, cue.start, cue.end, cue.text) for cue in cues] == [
        (1, 0.0, 4.25, "Oxford Economics puso numeros al riesgo electoral"),
        (2, 4.25, 8.17, "De la Espriella o Cepeda no moverian igual la economia."),
    ]


def test_build_clean_audio_command_targets_voiceover_file(tmp_path: Path):
    input_audio = tmp_path / "raw.wav"
    output_audio = tmp_path / "clean.wav"

    command = build_clean_audio_command(input_audio, output_audio)

    assert command[:4] == ["ffmpeg", "-y", "-i", str(input_audio)]
    assert "-af" in command
    assert str(output_audio) == command[-1]


def test_build_timed_audio_commands_pad_or_trim_to_exact_duration(tmp_path: Path):
    source = tmp_path / "chunk.wav"
    target = tmp_path / "timed.wav"

    timed_command = build_timed_chunk_command(
        source_audio=source,
        output_audio=target,
        tempo=1.25,
        target_duration=2.7,
    )
    silence_command = build_silence_command(target, duration=0.54)

    assert timed_command[:4] == ["ffmpeg", "-y", "-i", str(source)]
    assert "-af" in timed_command
    assert "atempo=1.25000000,apad,atrim=start=0:end=2.700000,asetpts=N/SR/TB" in timed_command
    assert str(target) == timed_command[-1]
    assert silence_command[:5] == ["ffmpeg", "-y", "-f", "lavfi", "-i"]
    assert "anullsrc=r=24000:cl=mono" in silence_command
    assert "-t" in silence_command


def test_build_render_command_uses_concat_subtitles_audio_and_output(tmp_path: Path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    concat_file = project_dir / "render" / "concat.txt"
    subtitles_file = project_dir / "subtitles.srt"
    audio_file = project_dir / "voiceover_clean.wav"
    output_file = project_dir / "final.mp4"

    command = build_render_command(
        concat_file=concat_file,
        subtitles_file=subtitles_file,
        audio_file=audio_file,
        output_file=output_file,
    )

    assert command[:6] == ["ffmpeg", "-y", "-f", "concat", "-safe", "0"]
    assert str(concat_file) in command
    assert str(audio_file) in command
    assert str(output_file) == command[-1]
    assert any("subtitles=" in part for part in command)


def test_build_finalize_audio_command_replaces_video_audio(tmp_path: Path):
    video_file = tmp_path / "draft.mp4"
    clean_audio_file = tmp_path / "voiceover_clean.wav"
    output_file = tmp_path / "final_final.mp4"

    command = build_finalize_audio_command(
        video_file=video_file,
        audio_file=clean_audio_file,
        output_file=output_file,
    )

    assert command[:4] == ["ffmpeg", "-y", "-i", str(video_file)]
    assert str(clean_audio_file) in command
    assert "-map" in command
    assert "0:v:0" in command
    assert "1:a:0" in command
    assert "-shortest" in command
    assert str(output_file) == command[-1]


def test_build_exact_timed_finalize_audio_command_pads_short_video(tmp_path: Path):
    video_file = tmp_path / "draft.mp4"
    clean_audio_file = tmp_path / "voiceover_clean.wav"
    output_file = tmp_path / "final_timed_tts.mp4"

    command = build_exact_timed_finalize_audio_command(
        video_file=video_file,
        audio_file=clean_audio_file,
        output_file=output_file,
        target_duration=44.166,
        video_duration=44.133333,
    )

    assert command[:4] == ["ffmpeg", "-y", "-i", str(video_file)]
    assert "-vf" in command
    assert "tpad=stop_mode=clone:stop_duration=0.032667" in command
    assert "-t" in command
    assert "44.166000" in command
    assert "-shortest" not in command
    assert str(output_file) == command[-1]


def test_finalize_audio_cleans_voiceover_then_writes_final_reel(tmp_path: Path, monkeypatch):
    draft_video = tmp_path / "draft.mp4"
    voiceover = tmp_path / "voiceover.wav"
    output_video = tmp_path / "final_final.mp4"
    draft_video.write_bytes(b"video")
    voiceover.write_bytes(b"voice")
    commands = []

    def fake_run(command, check):
        commands.append(command)

    monkeypatch.setattr(reel_workflow.subprocess, "run", fake_run)

    clean_audio_path = finalize_audio(
        video_file=draft_video,
        voiceover_file=voiceover,
        output_file=output_video,
    )

    assert clean_audio_path == tmp_path / "voiceover_clean.wav"
    assert commands[0] == build_clean_audio_command(voiceover, clean_audio_path)
    assert commands[1] == build_finalize_audio_command(draft_video, clean_audio_path, output_video)


def test_generate_timed_tts_final_uses_subtitle_lines_then_finalizes(tmp_path: Path, monkeypatch):
    root = tmp_path / "voiceover"
    project_dir = root / "reels" / "projects" / "peso-watch"
    draft_video = project_dir / "drafts" / "final.mp4"
    voice_sample = root / "voice_samples" / "voice.wav"
    chunks_dir = project_dir / "tts_timed_sample" / "chunks"
    project_dir.mkdir(parents=True)
    draft_video.parent.mkdir()
    voice_sample.parent.mkdir()
    chunks_dir.mkdir(parents=True)
    draft_video.write_bytes(b"video")
    voice_sample.write_bytes(b"voice")
    (project_dir / "subtitles.srt").write_text(
        "1\n00:00:00,000 --> 00:00:02,000\nLinea uno.\n\n"
        "2\n00:00:02,500 --> 00:00:04,000\nLinea dos.\n",
        encoding="utf-8",
    )
    (chunks_dir / "chunk_001.wav").write_bytes(b"one")
    (chunks_dir / "chunk_002.wav").write_bytes(b"two")
    durations = {
        chunks_dir / "chunk_001.wav": 1.0,
        chunks_dir / "chunk_002.wav": 3.0,
        draft_video: 3.9,
        project_dir / "tts_timed_sample" / "timed_chunks" / "segment_001_chunk_001.wav": 2.0,
        project_dir / "tts_timed_sample" / "timed_chunks" / "segment_002_silence.wav": 0.5,
        project_dir / "tts_timed_sample" / "timed_chunks" / "segment_003_chunk_002.wav": 1.5,
        project_dir / "tts_timed_sample" / "voiceover_timed_to_subtitles.wav": 4.0,
    }
    commands = []

    def fake_run(command, check, **kwargs):
        commands.append(command)
        return subprocess_result("1.0")

    def fake_duration(path):
        return durations[Path(path)]

    monkeypatch.setattr(reel_workflow.subprocess, "run", fake_run)
    monkeypatch.setattr(reel_workflow, "ffprobe_duration", fake_duration)

    result = generate_timed_tts_final(root=root, slug="peso-watch", voice_wav=voice_sample)

    voice_lines = project_dir / "tts_timed_voice_lines.txt"
    assert voice_lines.read_text(encoding="utf-8") == "Linea uno.\nLinea dos.\n"
    assert commands[0][1].endswith("generate_voiceover.py")
    assert "--txt" in commands[0]
    assert str(voice_lines) in commands[0]
    assert commands[1] == build_timed_chunk_command(
        chunks_dir / "chunk_001.wav",
        project_dir / "tts_timed_sample" / "timed_chunks" / "segment_001_chunk_001.wav",
        tempo=0.5,
        target_duration=2.0,
    )
    assert commands[2] == build_silence_command(
        project_dir / "tts_timed_sample" / "timed_chunks" / "segment_002_silence.wav",
        duration=0.5,
    )
    assert commands[-2] == build_clean_audio_command(
        project_dir / "tts_timed_sample" / "voiceover_timed_to_subtitles.wav",
        project_dir / "tts_timed_sample" / "voiceover_timed_to_subtitles_clean.wav",
    )
    assert commands[-1] == build_exact_timed_finalize_audio_command(
        draft_video,
        project_dir / "tts_timed_sample" / "voiceover_timed_to_subtitles_clean.wav",
        project_dir / "drafts" / "final_timed_tts.mp4",
        target_duration=4.0,
        video_duration=3.9,
    )
    assert result.output_video == project_dir / "drafts" / "final_timed_tts.mp4"
    assert result.target_duration == 4.0


def test_list_reel_projects_reads_history(tmp_path: Path):
    root = tmp_path / "voiceover"
    create_reel_project(root=root, slug="peso-watch", template="daily_fx")

    projects = list_reel_projects(root)

    assert projects == [{"slug": "peso-watch", "status": "draft", "title": "Peso Watch"}]


class subprocess_result:
    def __init__(self, stdout: str = ""):
        self.stdout = stdout
