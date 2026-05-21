import json
from pathlib import Path

import pytest


from divisas_voiceover_xtts_clean.src.reel_workflow import (
    ReelWorkflowError,
    build_clean_audio_command,
    build_render_command,
    create_reel_project,
    generate_subtitles,
    list_reel_projects,
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


def test_build_clean_audio_command_targets_voiceover_file(tmp_path: Path):
    input_audio = tmp_path / "raw.wav"
    output_audio = tmp_path / "clean.wav"

    command = build_clean_audio_command(input_audio, output_audio)

    assert command[:4] == ["ffmpeg", "-y", "-i", str(input_audio)]
    assert "-af" in command
    assert str(output_audio) == command[-1]


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


def test_list_reel_projects_reads_history(tmp_path: Path):
    root = tmp_path / "voiceover"
    create_reel_project(root=root, slug="peso-watch", template="daily_fx")

    projects = list_reel_projects(root)

    assert projects == [{"slug": "peso-watch", "status": "draft", "title": "Peso Watch"}]
