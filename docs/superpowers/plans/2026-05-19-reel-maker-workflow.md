# Reel Maker Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, file-based marketing reel workflow inside `divisas_voiceover_xtts_clean`.

**Architecture:** Add a reusable workflow module that owns reel project JSON, subtitles, prompt files, placeholder images, audio cleanup, and FFmpeg command construction. Add a thin CLI wrapper for commands used day to day.

**Tech Stack:** Python 3.11, standard library JSON/path/subprocess/PNG writing, FFmpeg for audio/video rendering, pytest for tests.

---

### Task 1: Project Creation And History

**Files:**
- Create: `tests/test_reel_workflow.py`
- Create: `divisas_voiceover_xtts_clean/src/reel_workflow.py`
- Create: `divisas_voiceover_xtts_clean/reel_maker.py`

- [ ] Write tests for creating a daily FX reel project with `reel.json`, `script.txt`, `subtitles.srt`, image prompt files, placeholder images, and `history.json`.
- [ ] Run `python -m pytest tests/test_reel_workflow.py -q` and verify the tests fail because `reel_workflow` does not exist.
- [ ] Implement `create_reel_project`, subtitle generation, history updates, and placeholder image generation.
- [ ] Re-run `python -m pytest tests/test_reel_workflow.py -q` and verify project creation passes.

### Task 2: Render And Audio Commands

**Files:**
- Modify: `tests/test_reel_workflow.py`
- Modify: `divisas_voiceover_xtts_clean/src/reel_workflow.py`
- Modify: `divisas_voiceover_xtts_clean/reel_maker.py`

- [ ] Add tests for clean-audio command construction and render command construction without executing FFmpeg.
- [ ] Run the targeted tests and verify they fail because command builders are missing.
- [ ] Implement `build_clean_audio_command`, `build_render_command`, `clean_audio`, and `render_reel`.
- [ ] Add CLI subcommands: `new`, `subtitles`, `clean-audio`, `render`, and `list`.
- [ ] Re-run tests and verify they pass.

### Task 3: Documentation

**Files:**
- Modify: `divisas_voiceover_xtts_clean/README.md`

- [ ] Document the new reel folder structure and commands.
- [ ] Run `python -m pytest tests/test_generate_voiceover_txt.py tests/test_reel_workflow.py -q`.
