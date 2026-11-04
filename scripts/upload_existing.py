#!/usr/bin/env python3
"""Uploads an already-rendered master video to YouTube using its .txt metadata.

Usage:
  python scripts/upload_existing.py "output/youtube/<Video title>/<YYYY-MM-DD_HH-MM-SS>.mp4"
  python scripts/upload_existing.py <video.mp4> --privacy unlisted
"""
import argparse
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from services.youtube import upload_video_resumable  # noqa: E402


def read_section(text: str, name: str) -> str:
    m = re.search(rf"\[{re.escape(name)}\]\n(.*?)(?:\n\n\[|\n={{10,}})", text, flags=re.S)
    return m.group(1).strip() if m else ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"])
    args = ap.parse_args()

    video = Path(args.video).resolve()
    from services.output_layout import mirror_path
    meta = mirror_path(video, "tiktok").with_suffix(".txt")
    if not video.is_file() or not meta.is_file():
        sys.exit(f"Missing video or metadata: {video} / {meta}")

    text = meta.read_text(encoding="utf-8")
    title = read_section(text, "SUGGESTED TITLE")
    description = read_section(text, "DESCRIPTION")
    hashtags = read_section(text, "TECHNICAL HASHTAGS").split()
    tags = [h.lstrip("#") for h in hashtags]

    print(f"Uploading {video.name}\n  title: {title}\n  privacy: {args.privacy}")
    url = upload_video_resumable(
        file_path=str(video),
        title=title,
        description=description,
        tags=tags,
        privacy_status=args.privacy,
        is_short=True,
    )
    print(f"Published: {url}")


if __name__ == "__main__":
    main()
