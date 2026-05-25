import argparse
import sys
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from reel_workflow import (  # noqa: E402
    clean_audio,
    create_reel_project,
    list_reel_projects,
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
    elif args.command == "list":
        for project in list_reel_projects(root):
            print(f"{project['slug']}\t{project['status']}\t{project['title']}")


if __name__ == "__main__":
    main()
