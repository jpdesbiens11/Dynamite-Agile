"""Zip the Dynamite | Agile source code into a backup folder.

The live "data" folder (database, attachments, logs) is never included:
copying an open SQLite database through OneDrive can corrupt it.

Default destination: <home>/Backups/Dynamite_Agile
Usage:
    python tools/backup_code.py
    python tools/backup_code.py --dest "D:/Backups"
"""
import argparse
import sys
import zipfile
from datetime import datetime
from pathlib import Path

VERSION = "0.1.0"
PROJECT_DIR = Path(__file__).resolve().parent.parent
EXCLUDED_DIRS = {"data", "__pycache__", ".git", ".spyproject", ".ipynb_checkpoints"}


def default_destination():
    return Path.home() / "Backups" / "Dynamite_Agile"


def collect_files(root):
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if path.is_file() and not any(part in EXCLUDED_DIRS for part in relative.parts):
            yield path, relative


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="backup_code",
        description="Dynamite | Agile code backup v{}. Zips the source code, "
                    "never the live data folder.".format(VERSION))
    parser.add_argument("--dest", type=Path, default=None,
                        help="Destination folder (default: ~/Backups/Dynamite_Agile).")
    args = parser.parse_args(argv)

    dest = args.dest or default_destination()
    if args.dest is None and not dest.parent.parent.exists():
        print("OneDrive folder not found: {}\nUse --dest to choose another folder.".format(
            dest.parent.parent), file=sys.stderr)
        return 1
    try:
        dest.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print("Cannot create {}: {}".format(dest, exc), file=sys.stderr)
        return 1

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = dest / "Dynamite_Agile_code_{}.zip".format(stamp)
    count = 0
    with zipfile.ZipFile(str(zip_path), "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, relative in collect_files(PROJECT_DIR):
            archive.write(str(path), str(Path("Dynamite_Agile") / relative))
            count += 1
    print("Backup created: {} ({} files)".format(zip_path, count))
    return 0


if __name__ == "__main__":
    sys.exit(main())
