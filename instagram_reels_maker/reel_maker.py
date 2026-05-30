import argparse
import sys
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from reel_workflow import (  # noqa: E402
    clean_audio,
    create_reel_project,
    finalize_audio,
    generate_audio_first_final,
    generate_timed_tts_final,
    list_reel_projects,
    publish_reel,
    regenerate_subtitles,
    render_reel,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create and render Divisas COL marketing reels.")
    parser.add_argument(
        "--root",
        default=str(CURRENT_DIR),
        help="Workflow root. Defaults to the divisas_voiceover_xtts_clean folder.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_parser = subparsers.add_parser("new", help="Create a reel project from a template.")
    new_parser.add_argument("--slug", required=True)
    new_parser.add_argument("--template", default="daily_fx")
    new_parser.add_argument("--title")

    subtitles_parser = subparsers.add_parser("subtitles", help="Regenerate subtitles from reel.json.")
    subtitles_parser.add_argument("--project", required=True)

    clean_parser = subparsers.add_parser("clean-audio", help="Clean a project's voiceover audio.")
    clean_parser.add_argument("--project", required=True)

    render_parser = subparsers.add_parser("render", help="Render a project's final MP4.")
    render_parser.add_argument("--project", required=True)
    render_parser.add_argument("--raw-audio", action="store_true", help="Use raw voiceover instead of clean audio.")

    finalize_parser = subparsers.add_parser(
        "finalize-audio",
        help="Clean a standalone voiceover and add it to a silent draft reel.",
    )
    finalize_parser.add_argument("--video", required=True, help="Silent draft reel MP4.")
    finalize_parser.add_argument("--voice", required=True, help="Voiceover WAV or audio file to clean.")
    finalize_parser.add_argument("--out", required=True, help="Final MP4 with cleaned voiceover audio.")
    finalize_parser.add_argument("--clean-out", help="Optional path for the cleaned voiceover WAV.")

    timed_tts_parser = subparsers.add_parser(
        "timed-tts-final",
        help="Generate XTTS voice lines from subtitle cues and add timed audio to a silent draft.",
    )
    timed_tts_parser.add_argument("--project", required=True, help="Reel project slug.")
    timed_tts_parser.add_argument("--voice", required=True, help="Reference voice WAV file.")
    timed_tts_parser.add_argument(
        "--video",
        help="Silent draft reel MP4. Defaults to the project's drafts\\final.mp4.",
    )
    timed_tts_parser.add_argument(
        "--out",
        help="Final MP4 with timed TTS audio. Defaults to the project's drafts\\final_timed_tts.mp4.",
    )
    timed_tts_parser.add_argument(
        "--sample-dir-name",
        default="tts_timed_sample",
        help="Project subfolder for generated voice lines, chunks, timed WAVs, and timing report.",
    )

    audio_first_parser = subparsers.add_parser(
        "audio-first-final",
        help="Generate short-line TTS first, derive timeline from natural audio, and rebuild the final reel.",
    )
    audio_first_parser.add_argument("--project", required=True, help="Reel project slug.")
    audio_first_parser.add_argument(
        "--tts-backend",
        default="edge-tts",
        choices=["edge-tts", "windows-sapi", "xtts"],
        help="TTS backend for short voice lines. Edge TTS uses neural Microsoft voices.",
    )
    audio_first_parser.add_argument("--voice", help="Reference voice WAV file. Required only for --tts-backend xtts.")
    audio_first_parser.add_argument("--voice-name", help="Windows SAPI voice name, for example Microsoft Sabina.")
    audio_first_parser.add_argument(
        "--voice-pool",
        default="es-MX-DaliaNeural,es-ES-AlvaroNeural",
        help="Comma-separated Edge TTS voices rotated by complete sentence inside each reel.",
    )
    audio_first_parser.add_argument("--sapi-rate", type=int, default=0, help="Windows SAPI speech rate from -10 to 10.")
    audio_first_parser.add_argument(
        "--video",
        help="Legacy silent draft path to record in metadata. Audio-first rendering rebuilds from images.",
    )
    audio_first_parser.add_argument(
        "--out",
        help="Final MP4 with audio-first TTS. Defaults to the project's final\\final_audio_first.mp4.",
    )
    audio_first_parser.add_argument(
        "--sample-dir-name",
        default="audio_first",
        help="Project subfolder for generated short-line voice chunks and timing report.",
    )

    publish_parser = subparsers.add_parser(
        "publish-reel",
        help="Publish a final audio-first reel to Instagram Reels.",
    )
    publish_parser.add_argument("--project", required=True, help="Reel project slug.")
    publish_parser.add_argument(
        "--tunnel-provider",
        choices=["auto", "cloudflare", "ngrok"],
        default="auto",
        help="Tunnel provider used to expose the final MP4 to Meta.",
    )
    publish_parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Ignore final\\publish-state.json and publish again.",
    )
    publish_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Prepare caption, publish script, and manifest without calling Meta.",
    )

    subparsers.add_parser("list", help="List reel projects from history.")

    args = parser.parse_args()
    root = Path(args.root)

    if args.command == "new":
        project = create_reel_project(
            root=root,
            slug=args.slug,
            template=args.template,
            title=args.title,
        )
        print(f"Created reel project: {project.project_dir}")
    elif args.command == "subtitles":
        subtitles_path = regenerate_subtitles(root=root, slug=args.project)
        print(f"Saved subtitles: {subtitles_path}")
    elif args.command == "clean-audio":
        clean_path = clean_audio(root=root, slug=args.project)
        print(f"Saved clean audio: {clean_path}")
    elif args.command == "render":
        output_path = render_reel(root=root, slug=args.project, use_clean_audio=not args.raw_audio)
        print(f"Saved reel: {output_path}")
    elif args.command == "finalize-audio":
        clean_path = finalize_audio(
            video_file=args.video,
            voiceover_file=args.voice,
            output_file=args.out,
            clean_audio_file=args.clean_out,
        )
        print(f"Saved clean audio: {clean_path}")
        print(f"Saved final reel: {Path(args.out)}")
    elif args.command == "timed-tts-final":
        result = generate_timed_tts_final(
            root=root,
            slug=args.project,
            voice_wav=args.voice,
            draft_video=args.video,
            output_video=args.out,
            sample_dir_name=args.sample_dir_name,
        )
        print(f"Saved voice lines: {result.voice_lines}")
        print(f"Saved raw TTS voiceover: {result.raw_voiceover}")
        print(f"Saved timed TTS voiceover: {result.timed_voiceover}")
        print(f"Saved clean timed TTS: {result.clean_voiceover}")
        print(f"Saved timing report: {result.timing_report}")
        print(f"Saved final reel: {result.output_video}")
    elif args.command == "audio-first-final":
        result = generate_audio_first_final(
            root=root,
            slug=args.project,
            voice_wav=args.voice,
            draft_video=args.video,
            output_video=args.out,
            sample_dir_name=args.sample_dir_name,
            tts_backend=args.tts_backend,
            voice_name=args.voice_name,
            voice_pool=[voice.strip() for voice in args.voice_pool.split(",") if voice.strip()],
            sapi_rate=args.sapi_rate,
        )
        print(f"Saved voice lines: {result.voice_lines}")
        print(f"Saved natural TTS voiceover: {result.raw_voiceover}")
        print(f"Saved clean voiceover: {result.clean_voiceover}")
        print(f"Saved subtitles: {result.subtitles_path}")
        print(f"Saved timing report: {result.timing_report}")
        print(f"Saved final reel: {result.output_video}")
    elif args.command == "publish-reel":
        result = publish_reel(
            root=root,
            slug=args.project,
            tunnel_provider=args.tunnel_provider,
            reset_state=args.reset_state,
            dry_run=args.dry_run,
        )
        print(f"Saved publish manifest: {result.manifest_path}")
        print(f"Saved publish script: {result.publish_script_path}")
        print(f"Saved publish caption: {result.caption_path}")
        print(f"Reel video: {result.video_path}")
        if result.video_url:
            print(f"Public video URL: {result.video_url}")
        if result.published_id:
            print(f"Published Instagram reel: {result.published_id}")
    elif args.command == "list":
        for project in list_reel_projects(root):
            print(f"{project['slug']}\t{project['status']}\t{project['title']}")


if __name__ == "__main__":
    main()
