import argparse, fnmatch, os
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".vscode",
    "__pycache__",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    "venv",
    ".venv",
    "env",
    "build",
    "dist",
    "node_modules",
}
DEFAULT_EXCLUDE_GLOBS = [
    "*.zip",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.log",
    ".DS_Store",
    "Thumbs.db",
    ".git*",
]


def is_within(child: Path, parent: Path) -> bool:
    child = child.resolve()
    parent = parent.resolve()
    try:
        return os.path.commonpath([str(parent), str(child)]) == str(parent)
    except Exception:
        return False


def zip_dir(
    src: Path,
    dst: Path = None,
    exclude_dirs: set[str] = None,
    exclude_globs: list[str] = None,
) -> Path:
    src = src.resolve()
    if not src.is_dir():
        raise ValueError(f"Source is not a directory: {src}")

    exclude_dirs = set(DEFAULT_EXCLUDE_DIRS if exclude_dirs is None else exclude_dirs)
    exclude_globs = list(
        DEFAULT_EXCLUDE_GLOBS if exclude_globs is None else exclude_globs
    )

    if dst is None:
        dst = src / f"{src.name}.zip"  # Same folder as src
    dst = dst.resolve()

    output_inside_src = is_within(dst, src)

    with ZipFile(dst, "w", compression=ZIP_DEFLATED) as zf:
        for path in src.rglob("*"):
            rel = path.relative_to(src)

            if any(part in exclude_dirs for part in rel.parts):
                continue
            if path.is_dir():
                continue
            if any(fnmatch.fnmatch(path.name, pat) for pat in exclude_globs):
                continue
            if output_inside_src and path.resolve() == dst:
                continue

            zf.write(path, rel.as_posix())

    return dst


def main():
    p = argparse.ArgumentParser(description="Zip a folder for GCP Cloud Functions.")
    p.add_argument(
        "--src", default=".", help="Source folder to zip (default: current directory)."
    )
    p.add_argument("--out", help="Output zip path (default: <src>/<src>.zip).")
    args = p.parse_args()

    src = Path(args.src)
    out = Path(args.out) if args.out else None
    zip_path = zip_dir(src, out)
    print(f"Created: {zip_path}")


if __name__ == "__main__":
    main()
