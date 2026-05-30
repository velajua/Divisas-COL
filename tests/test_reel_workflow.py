import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
REEL_SRC = REPO_ROOT / "instagram_reels_maker" / "src"
sys.path.insert(0, str(REEL_SRC))

import reel_workflow
from reel_workflow import (
    AUDIO_FIRST_WORKFLOW_VERSION,
    ReelWorkflowError,
    cleanup_audio_first_text_intermediates,
    build_audio_first_voiceover,
    build_audio_first_render,
    cleanup_stale_reel_artifacts,
    build_exact_timed_finalize_audio_command,
    build_silence_command,
    build_timed_chunk_command,
    build_clean_audio_command,
    build_trim_silence_command,
    build_finalize_audio_command,
    build_render_command,
    create_reel_project,
    finalize_audio,
    generate_audio_first_final,
    generate_tts_chunks,
    generate_timed_tts_final,
    generate_subtitles,
    list_reel_projects,
    load_subtitle_cues,
    prepare_reel_publish,
    publish_reel,
    validate_short_voiceover_lines,
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
    assert reel_json["workflow_version"] == AUDIO_FIRST_WORKFLOW_VERSION
    assert reel_json["format"] == "daily_fx_comparison"
    assert reel_json["voiceover"]["mode"] == "audio_first_short_lines"
    assert len(reel_json["scenes"]) == 5
    assert reel_json["scenes"][0]["voiceover_lines"] == ["El dólar no se mueve solo."]
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


def test_validate_short_voiceover_lines_rejects_long_lines():
    scenes = [
        {
            "id": "hook",
            "voiceover_lines": [
                "Esta linea tiene demasiadas palabras para mantener buena calidad de audio."
            ],
        }
    ]

    with pytest.raises(ReelWorkflowError, match="9 words or fewer"):
        validate_short_voiceover_lines(scenes)


def test_validate_short_voiceover_lines_accepts_short_lines():
    scenes = [
        {"id": "hook", "voiceover_lines": ["Deuda record en TES.", "Peso bajo examen."]}
    ]

    validate_short_voiceover_lines(scenes)


def test_build_audio_first_voiceover_uses_measured_chunks_without_tempo(tmp_path: Path, monkeypatch):
    project_dir = tmp_path / "project"
    chunks_dir = project_dir / "audio_first" / "chunks"
    chunks_dir.mkdir(parents=True)
    for index in range(1, 4):
        (chunks_dir / f"chunk_{index:03d}.wav").write_bytes(b"voice")
    scenes = [
        {"id": "hook", "voiceover_lines": ["Deuda record en TES.", "Peso bajo examen."]},
        {"id": "cta", "voiceover_lines": ["La deuda cobra."]},
    ]
    durations = {
        chunks_dir / "chunk_001.wav": 1.2,
        chunks_dir / "chunk_002.wav": 1.0,
        chunks_dir / "chunk_003.wav": 0.8,
        project_dir / "audio_first" / "voiceover_natural.wav": 3.4,
    }
    commands = []

    def fake_run(command, check):
        commands.append(command)
        if command == build_clean_audio_command(
            project_dir / "audio_first" / "voiceover_natural.wav",
            project_dir / "audio_first" / "voiceover_natural_clean.wav",
        ):
            (project_dir / "audio_first" / "voiceover_natural_clean.wav").write_bytes(b"clean")

    def fake_duration(path):
        return durations[Path(path)]

    monkeypatch.setattr(reel_workflow.subprocess, "run", fake_run)
    monkeypatch.setattr(reel_workflow, "ffprobe_duration", fake_duration)

    timeline = build_audio_first_voiceover(
        scenes=scenes,
        chunks_dir=chunks_dir,
        output_wav=project_dir / "audio_first" / "voiceover_natural.wav",
        report_path=project_dir / "audio_first" / "timing_report.json",
    )

    assert [cue.text for cue in timeline.cues] == [
        "Deuda record en TES.",
        "Peso bajo examen.",
        "La deuda cobra.",
    ]
    assert [(cue.start, cue.end) for cue in timeline.cues] == [
        (0.0, 1.2),
        (1.26, 2.26),
        (2.38, 3.18),
    ]
    assert scenes[0]["duration_seconds"] == 2.38
    assert scenes[1]["duration_seconds"] == 0.8
    assert not any("atempo" in " ".join(command) for command in commands)
    assert any(command == build_silence_command(project_dir / "audio_first" / "segments" / "segment_002_silence.wav", 0.06) for command in commands)


def test_audio_first_voiceover_uses_tighter_gap_for_unfinished_sentence(tmp_path: Path, monkeypatch):
    project_dir = tmp_path / "project"
    chunks_dir = project_dir / "audio_first" / "chunks"
    chunks_dir.mkdir(parents=True)
    for index in range(1, 3):
        (chunks_dir / f"chunk_{index:03d}.wav").write_bytes(b"voice")
    scenes = [
        {
            "id": "hook",
            "voiceover_lines": ["Cuando el dolar sube,", "el bolsillo lo siente."],
        }
    ]
    durations = {
        chunks_dir / "chunk_001.wav": 1.0,
        chunks_dir / "chunk_002.wav": 1.0,
        project_dir / "audio_first" / "voiceover_natural.wav": 2.02,
    }
    commands = []

    def fake_duration(path):
        return durations[Path(path)]

    def fake_run(command, check):
        commands.append(command)
        Path(command[-1]).parent.mkdir(parents=True, exist_ok=True)
        Path(command[-1]).write_bytes(b"audio")

    monkeypatch.setattr(reel_workflow.subprocess, "run", fake_run)
    monkeypatch.setattr(reel_workflow, "ffprobe_duration", fake_duration)

    timeline = build_audio_first_voiceover(
        scenes=scenes,
        chunks_dir=chunks_dir,
        output_wav=project_dir / "audio_first" / "voiceover_natural.wav",
        report_path=project_dir / "audio_first" / "timing_report.json",
    )

    assert [(cue.start, cue.end) for cue in timeline.cues] == [(0.0, 1.0), (1.02, 2.02)]
    assert any(
        command == build_silence_command(project_dir / "audio_first" / "segments" / "segment_002_silence.wav", 0.02)
        for command in commands
    )


def test_generate_tts_chunks_uses_windows_sapi_backend_without_xtts_voice(tmp_path: Path, monkeypatch):
    sample_dir = tmp_path / "audio_first"
    voice_lines = tmp_path / "audio_first_voice_lines.txt"
    voice_lines.write_text("Deuda record en TES.\nPeso bajo examen.\n", encoding="utf-8")
    calls = []

    def fake_sapi(lines, chunks_dir, voice_name=None, rate=0, volume=100):
        calls.append((lines, chunks_dir, voice_name, rate, volume))

    monkeypatch.setattr(reel_workflow, "generate_windows_sapi_chunks", fake_sapi)

    generate_tts_chunks(
        backend="windows-sapi",
        voice_lines=voice_lines,
        sample_dir=sample_dir,
        voice_wav=None,
        voice_name="Microsoft Sabina",
        sapi_rate=1,
    )

    assert calls == [
        (
            ["Deuda record en TES.", "Peso bajo examen."],
            sample_dir / "chunks",
            "Microsoft Sabina",
            1,
            100,
        )
    ]


def test_audio_first_default_gaps_are_short_for_fluent_delivery():
    assert reel_workflow.DEFAULT_AUDIO_FIRST_LINE_GAP_SECONDS == 0.06
    assert reel_workflow.DEFAULT_AUDIO_FIRST_CONTINUATION_GAP_SECONDS == 0.02
    assert reel_workflow.DEFAULT_AUDIO_FIRST_SCENE_GAP_SECONDS == 0.12


def test_generate_tts_chunks_uses_edge_tts_backend_with_voice_pool(tmp_path: Path, monkeypatch):
    sample_dir = tmp_path / "audio_first"
    voice_lines = tmp_path / "audio_first_voice_lines.txt"
    voice_lines.write_text("Peso otra vez en alerta.\nDolar mirando al techo.\n", encoding="utf-8")
    calls = []

    def fake_edge(lines, chunks_dir, voice_pool):
        calls.append((lines, chunks_dir, voice_pool))

    monkeypatch.setattr(reel_workflow, "generate_edge_tts_chunks", fake_edge)

    generate_tts_chunks(
        backend="edge-tts",
        voice_lines=voice_lines,
        sample_dir=sample_dir,
        voice_wav=None,
        voice_pool=["es-MX-DaliaNeural", "es-ES-AlvaroNeural"],
    )

    assert calls == [
        (
            ["Peso otra vez en alerta.", "Dolar mirando al techo."],
            sample_dir / "chunks",
            ["es-MX-DaliaNeural", "es-ES-AlvaroNeural"],
        )
    ]


def test_edge_tts_voice_pool_rotates_by_complete_sentence(tmp_path: Path, monkeypatch):
    chunks_dir = tmp_path / "chunks"
    calls = []

    async def fake_save_edge_tts(text, voice_name, output_path):
        calls.append((text, voice_name, output_path.name))
        output_path.write_bytes(b"mp3")

    def fake_run(command, check):
        Path(command[-1]).write_bytes(b"wav")

    monkeypatch.setattr(reel_workflow, "save_edge_tts_mp3", fake_save_edge_tts)
    monkeypatch.setattr(reel_workflow.subprocess, "run", fake_run)

    reel_workflow.generate_edge_tts_chunks(
        ["Linea uno", "continua aqui.", "Linea dos.", "Linea tres"],
        chunks_dir,
        voice_pool=["es-MX-DaliaNeural", "es-ES-AlvaroNeural"],
    )

    assert calls == [
        ("Linea uno", "es-MX-DaliaNeural", "chunk_001_edge.mp3"),
        ("continua aqui.", "es-MX-DaliaNeural", "chunk_002_edge.mp3"),
        ("Linea dos.", "es-ES-AlvaroNeural", "chunk_003_edge.mp3"),
        ("Linea tres", "es-MX-DaliaNeural", "chunk_004_edge.mp3"),
    ]
    assert (chunks_dir / "voice_assignments.json").exists()


def test_trim_silence_command_crops_edge_padding_before_timing(tmp_path: Path):
    source = tmp_path / "raw.wav"
    output = tmp_path / "trimmed.wav"

    command = build_trim_silence_command(source, output)

    command_text = " ".join(command)
    assert command[:4] == ["ffmpeg", "-y", "-i", str(source)]
    assert "silenceremove=start_periods=1" in command_text
    assert "stop_periods=-1" in command_text
    assert command[-1] == str(output)


def test_edge_tts_chunks_are_trimmed_before_measurement(tmp_path: Path, monkeypatch):
    chunks_dir = tmp_path / "chunks"
    commands = []

    async def fake_save_edge_tts(text, voice_name, output_path):
        output_path.write_bytes(b"mp3")

    def fake_run(command, check):
        commands.append(command)
        Path(command[-1]).write_bytes(b"audio")

    monkeypatch.setattr(reel_workflow, "save_edge_tts_mp3", fake_save_edge_tts)
    monkeypatch.setattr(reel_workflow.subprocess, "run", fake_run)

    reel_workflow.generate_edge_tts_chunks(["Linea uno."], chunks_dir, voice_pool=["es-MX-DaliaNeural"])

    raw_wav = chunks_dir / "chunk_001_raw.wav"
    final_wav = chunks_dir / "chunk_001.wav"
    assert commands[0][-1] == str(raw_wav)
    assert commands[1] == build_trim_silence_command(raw_wav, final_wav)


def test_audio_first_render_rebuilds_video_from_measured_scene_durations(tmp_path: Path, monkeypatch):
    project_dir = tmp_path / "project"
    clean_audio = project_dir / "audio_first" / "voiceover_natural_clean.wav"
    subtitles = project_dir / "subtitles.srt"
    output_video = project_dir / "final" / "final_audio_first.mp4"
    image = project_dir / "images" / "001_hook.png"
    image.parent.mkdir(parents=True)
    clean_audio.parent.mkdir(parents=True)
    image.write_bytes(b"image")
    clean_audio.write_bytes(b"audio")
    subtitles.write_text("1\n00:00:00,000 --> 00:00:02,350\nDeuda record en TES.\n", encoding="utf-8")
    scenes = [
        {
            "id": "hook",
            "image": "images/001_hook.png",
            "duration_seconds": 2.35,
            "voiceover_lines": ["Deuda record en TES."],
        }
    ]
    commands = []

    def fake_run(command, check):
        commands.append(command)

    monkeypatch.setattr(reel_workflow.subprocess, "run", fake_run)

    rendered = build_audio_first_render(
        project_dir=project_dir,
        scenes=scenes,
        subtitles_path=subtitles,
        clean_voiceover=clean_audio,
        output_video=output_video,
    )

    concat_file = project_dir / "render" / "audio_first_concat.txt"
    assert rendered == output_video
    assert "duration 2.350" in concat_file.read_text(encoding="utf-8")
    assert commands == [
        build_render_command(
            concat_file=concat_file,
            subtitles_file=subtitles,
            audio_file=clean_audio,
            output_file=output_video,
        )
    ]


def test_audio_first_render_places_subtitles_near_bottom(tmp_path: Path):
    command = build_render_command(
        concat_file=tmp_path / "concat.txt",
        subtitles_file=tmp_path / "subtitles.srt",
        audio_file=tmp_path / "voice.wav",
        output_file=tmp_path / "final.mp4",
    )

    filter_args = command[command.index("-vf") + 1]
    assert "Alignment=2" in filter_args
    assert "MarginV=80" in filter_args


def test_generate_audio_first_final_updates_reel_metadata_subtitles_and_rebuilds_video(tmp_path: Path, monkeypatch):
    root = tmp_path / "maker"
    project_dir = root / "reels" / "projects" / "peso-watch"
    chunks_dir = project_dir / "audio_first" / "chunks"
    voice_sample = root / "voice_samples" / "voice.wav"
    chunks_dir.mkdir(parents=True)
    voice_sample.parent.mkdir()
    voice_sample.write_bytes(b"voice")
    image = project_dir / "images" / "001_hook.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"image")
    for index in range(1, 3):
        (chunks_dir / f"chunk_{index:03d}.wav").write_bytes(b"voice")
    (project_dir / "reel.json").write_text(
        json.dumps(
            {
                "slug": "peso-watch",
                "title": "Peso Watch",
                "status": "draft",
                "voiceover": {"mode": "provided_or_xtts"},
                "scenes": [
                    {
                        "id": "hook",
                        "image": "images/001_hook.png",
                        "voiceover_lines": ["Deuda record en TES.", "Peso bajo examen."],
                    }
                ],
                "outputs": {},
            }
        ),
        encoding="utf-8",
    )
    durations = {
        chunks_dir / "chunk_001.wav": 1.2,
        chunks_dir / "chunk_002.wav": 1.0,
        project_dir / "audio_first" / "voiceover_natural.wav": 2.35,
    }
    commands = []

    def fake_run(command, check):
        commands.append(command)
        if command == build_clean_audio_command(
            project_dir / "audio_first" / "voiceover_natural.wav",
            project_dir / "audio_first" / "voiceover_natural_clean.wav",
        ):
            (project_dir / "audio_first" / "voiceover_natural_clean.wav").write_bytes(b"clean")

    def fake_duration(path):
        return durations[Path(path)]

    monkeypatch.setattr(reel_workflow.subprocess, "run", fake_run)
    monkeypatch.setattr(reel_workflow, "ffprobe_duration", fake_duration)

    result = generate_audio_first_final(
        root=root,
        slug="peso-watch",
        voice_wav=voice_sample,
        tts_backend="xtts",
    )

    reel_json = json.loads((project_dir / "reel.json").read_text(encoding="utf-8"))
    assert reel_json["workflow_version"] == AUDIO_FIRST_WORKFLOW_VERSION
    assert reel_json["voiceover"]["mode"] == "audio_first_short_lines"
    assert reel_json["voiceover"]["file"] == "audio_first/voiceover_natural.wav"
    assert reel_json["voiceover"]["clean_file"] == "audio_first/voiceover_natural_clean.wav"
    assert reel_json["scenes"][0]["duration_seconds"] == 2.26
    assert "00:00:00,000 --> 00:00:01,200" in (project_dir / "subtitles.srt").read_text(encoding="utf-8")
    assert commands[0][1].endswith("generate_voiceover.py")
    assert "--silence-ms" in commands[0]
    assert "0" in commands[0]
    assert not any("atempo" in " ".join(command) for command in commands)
    assert commands[-1] == build_render_command(
        project_dir / "render" / "audio_first_concat.txt",
        project_dir / "subtitles.srt",
        project_dir / "audio_first" / "voiceover_natural_clean.wav",
        project_dir / "final" / "final_audio_first.mp4",
    )
    assert reel_json["outputs"]["audio_first_render_manifest"] == "render/audio_first_concat.txt"
    assert result.output_video == project_dir / "final" / "final_audio_first.mp4"


def test_prepare_reel_publish_writes_manifest_caption_and_script(tmp_path: Path):
    root = tmp_path / "maker"
    project_dir = root / "reels" / "projects" / "peso-watch"
    final_video = project_dir / "final" / "final_audio_first.mp4"
    final_video.parent.mkdir(parents=True)
    final_video.write_bytes(b"video")
    (project_dir / "reel.json").write_text(
        json.dumps(
            {
                "slug": "peso-watch",
                "title": "Peso bajo examen",
                "outputs": {"audio_first_video": "final/final_audio_first.mp4"},
                "scenes": [
                    {"voiceover_lines": ["El peso queda bajo examen."], "subtitle": "Peso bajo examen"},
                    {"voiceover_lines": ["El mercado mira la deuda."], "subtitle": "Mercado y deuda"},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = prepare_reel_publish(root=root, slug="peso-watch", base_url="https://example.com/reels")

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    caption = result.caption_path.read_text(encoding="utf-8")
    publish_script = result.publish_script_path.read_text(encoding="utf-8")
    reel_json = json.loads((project_dir / "reel.json").read_text(encoding="utf-8"))
    assert manifest["media_type"] == "REELS"
    assert manifest["public_path"] == "reels/projects/peso-watch/final/final_audio_first.mp4"
    assert manifest["video_url"] == "https://example.com/reels/final_audio_first.mp4"
    assert "Peso bajo examen" in caption
    assert "#DivisasCOL" in caption
    assert "#DolarColombia" in caption
    assert "python reel_maker.py publish-reel --project peso-watch" in publish_script
    assert reel_json["outputs"]["publish_manifest"] == "final/publish-manifest.json"
    assert reel_json["outputs"]["publish_script"] == "final/publish-script.txt"


def test_publish_reel_uses_meta_reels_container_and_state(tmp_path: Path, monkeypatch):
    root = tmp_path / "instagram_reels_maker"
    project_dir = root / "reels" / "projects" / "peso-watch"
    final_video = project_dir / "final" / "final_audio_first.mp4"
    final_video.parent.mkdir(parents=True)
    final_video.write_bytes(b"video")
    (project_dir / "reel.json").write_text(
        json.dumps(
            {
                "slug": "peso-watch",
                "title": "Peso Watch",
                "outputs": {"audio_first_video": "final/final_audio_first.mp4"},
                "scenes": [{"voiceover_lines": ["El dólar no se mueve solo."]}],
            }
        ),
        encoding="utf-8",
    )
    calls = []

    class FakeResponse:
        ok = True
        headers = {"content-type": "video/mp4"}

        def raise_for_status(self):
            return None

        def json(self):
            return {"id": "creation-1"}

    class FakeRequests:
        class RequestException(Exception):
            pass

        @staticmethod
        def get(url, headers=None, timeout=15):
            calls.append(("get", url, headers, timeout))
            return FakeResponse()

    class FakeTunnel:
        def poll(self):
            return None

    class FakeServer:
        def shutdown(self):
            calls.append(("shutdown",))

    class FakePublishModule:
        DEFAULT_TUNNEL_TIMEOUT_SECONDS = 10
        requests = FakeRequests
        os = type("FakeOS", (), {"environ": {"INSTAGRAM_USER_ID": "ig-1", "META_PAGE_ACCESS_TOKEN": "token"}})

        @staticmethod
        def load_dotenv(path):
            calls.append(("dotenv", path))

        @staticmethod
        def validate_config():
            return True

        @staticmethod
        def run_http_server(public_dir, port):
            calls.append(("serve", public_dir, port))
            return FakeServer()

        @staticmethod
        def start_tunnel_for_publish(repo_root, port, provider, timeout_seconds):
            calls.append(("tunnel", repo_root, port, provider, timeout_seconds))
            return FakeTunnel(), "https://public.example"

        @staticmethod
        def graph_url(path):
            return f"https://graph.example/{path}"

        @staticmethod
        def sanitize_caption(caption):
            return caption

        @staticmethod
        def post_with_meta_retry(url, data, timeout):
            calls.append(("container", url, data, timeout))
            return FakeResponse()

        @staticmethod
        def wait_for_container_finished(container_id, token):
            calls.append(("wait", container_id, token))

        @staticmethod
        def publish_container(ig_user_id, token, creation_id):
            calls.append(("publish", ig_user_id, token, creation_id))
            return {"id": "published-1"}

        @staticmethod
        def terminate_process(tunnel):
            calls.append(("terminate", tunnel))

    monkeypatch.setattr(reel_workflow, "load_instagram_publish_module", lambda workflow_root: FakePublishModule)

    result = publish_reel(root=root, slug="peso-watch", tunnel_provider="cloudflare")

    state = json.loads((project_dir / "final" / "publish-state.json").read_text(encoding="utf-8"))
    manifest = json.loads((project_dir / "final" / "publish-manifest.json").read_text(encoding="utf-8"))
    container_call = next(call for call in calls if call[0] == "container")
    assert container_call[2]["media_type"] == "REELS"
    assert container_call[2]["video_url"] == "https://public.example/final_audio_first.mp4"
    assert container_call[2]["share_to_feed"] == "true"
    assert state["published_id"] == "published-1"
    assert state["creation_id"] == "creation-1"
    assert manifest["video_url"] == "https://public.example/final_audio_first.mp4"
    assert result.published_id == "published-1"


def test_cleanup_stale_reel_artifacts_preserves_source_assets(tmp_path: Path):
    project_dir = tmp_path / "project"
    for path in [
        project_dir / "reel.json",
        project_dir / "script.txt",
        project_dir / "caption.txt",
        project_dir / "review_notes.md",
        project_dir / "images" / "001_hook.png",
        project_dir / "prompts" / "001_hook.txt",
        project_dir / "drafts" / "final.mp4",
        project_dir / "subtitles.ass",
        project_dir / "tts_timed_sample" / "timing_report.json",
        project_dir / "tts_ass_line_sample" / "make_timed_voiceover.py",
        project_dir / "tts_srt_line_sample" / "chunks" / "chunk_001.txt",
        project_dir / "chunks" / "chunk_001.txt",
        project_dir / "drafts" / "final_timed_tts.mp4",
        project_dir / "drafts" / "preview_10s.png",
        project_dir / "render" / "clips" / "clip_001.mp4",
        project_dir / "render" / "clips.txt",
        project_dir / "render" / "concat.txt",
        project_dir / "render" / "video_only.mp4",
        project_dir / "render" / "render_cards.py",
        project_dir / "render" / "overlay_headlines.py",
        project_dir / "render" / "subtitle_filter.txt",
        project_dir / "render" / "preview_08s.png",
        project_dir / "srt_voice_lines.txt",
        project_dir / "tts_timed_voice_lines.txt",
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")

    removed = cleanup_stale_reel_artifacts(project_dir)

    assert (project_dir / "reel.json").exists()
    assert (project_dir / "script.txt").exists()
    assert (project_dir / "caption.txt").exists()
    assert (project_dir / "review_notes.md").exists()
    assert (project_dir / "images" / "001_hook.png").exists()
    assert (project_dir / "prompts" / "001_hook.txt").exists()
    assert not (project_dir / "drafts" / "final.mp4").exists()
    assert not (project_dir / "tts_timed_sample").exists()
    assert not (project_dir / "tts_ass_line_sample").exists()
    assert not (project_dir / "tts_srt_line_sample").exists()
    assert not (project_dir / "chunks").exists()
    assert not (project_dir / "drafts" / "final_timed_tts.mp4").exists()
    assert not (project_dir / "drafts" / "preview_10s.png").exists()
    assert not (project_dir / "render" / "clips").exists()
    assert not (project_dir / "render" / "clips.txt").exists()
    assert not (project_dir / "render" / "concat.txt").exists()
    assert not (project_dir / "render" / "video_only.mp4").exists()
    assert not (project_dir / "render" / "render_cards.py").exists()
    assert not (project_dir / "render" / "overlay_headlines.py").exists()
    assert not (project_dir / "render" / "subtitle_filter.txt").exists()
    assert not (project_dir / "render" / "preview_08s.png").exists()
    assert not (project_dir / "subtitles.ass").exists()
    assert "tts_timed_sample" in "\n".join(removed)


def test_cleanup_audio_first_text_intermediates_keeps_timing_report(tmp_path: Path):
    sample_dir = tmp_path / "audio_first"
    for path in [
        sample_dir / "voiceover_script.txt",
        sample_dir / "chunks" / "chunk_001.txt",
        sample_dir / "segments" / "concat.txt",
        sample_dir / "timing_report.json",
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")

    removed = cleanup_audio_first_text_intermediates(sample_dir)

    assert not (sample_dir / "voiceover_script.txt").exists()
    assert not (sample_dir / "chunks" / "chunk_001.txt").exists()
    assert not (sample_dir / "segments" / "concat.txt").exists()
    assert (sample_dir / "timing_report.json").exists()
    assert removed == ["voiceover_script.txt", "segments/concat.txt", "chunks/chunk_001.txt"]


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
    vf = command[command.index("-vf") + 1]
    assert "subtitles=" in vf
    assert "fps=30" in vf
    assert "FontSize=12" in vf


def test_select_windows_sapi_voice_prefers_spanish_neural_or_natural_names():
    class FakeToken:
        def __init__(self, description: str):
            self.description = description

        def GetDescription(self):
            return self.description

    class FakeVoice:
        def GetVoices(self):
            return [
                FakeToken("Microsoft Zira Desktop - English"),
                FakeToken("Microsoft Sabina Desktop - Spanish (Mexico)"),
                FakeToken("Microsoft Helena Natural - Spanish (Spain)"),
            ]

    selected = reel_workflow.select_windows_sapi_voice(FakeVoice())

    assert selected.GetDescription() == "Microsoft Helena Natural - Spanish (Spain)"


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
