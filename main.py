"""Silicon Verdict: makes one Motion Graphics video (62-90 s, English) and, unless told otherwise, uploads it to YouTube.

    .venv/bin/python main.py --motion-format myth --export-only
    .venv/bin/python main.py --motion-format any --topic "How TRIM keeps SSDs fast"
    .venv/bin/python main.py help

The daily batch of four videos is `scripts/genera_batch.py`; this is the single-video entry point.
"""
import argparse
import logging
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure venv bin (where static ffmpeg/ffprobe live) is in PATH
venv_bin = BASE_DIR / ".venv" / "bin"
if venv_bin.is_dir() and str(venv_bin) not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"{venv_bin}:{os.environ.get('PATH', '')}"

# Configure root logger with console and file logging
(BASE_DIR / "logs").mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(BASE_DIR / "logs" / "pipeline.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("silicon_verdict")

MOTION_FORMATS = ["auto", "any", "myth", "tier", "whatif", "easter", "evolution", "versus", "hardware", "simple", "fix", "decode", "top5", "eli5", "fails", "numbers", "quiz", "stop", "rumor", "review", "news", "priced"]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Silicon Verdict: one Motion Graphics video, rendered and (optionally) uploaded.")
    parser.add_argument("--topic", type=str, help="A fixed subject. Without it the story bank, then the LLM, picks one.")
    parser.add_argument("--motion-kind", type=str, choices=["auto", "curiosity", "game"], default="auto",
                        help="curiosity (a tech idea), game (an engineering fact about a game, with real footage) or auto (alternates; a game needs unused, non-blacklisted footage).")
    parser.add_argument("--motion-format", type=str, choices=MOTION_FORMATS, default="auto",
                        help="Content format (see guide/formats.md). any = a weighted random one, never news; auto = the classic explainer.")
    parser.add_argument("--export-only", action="store_true", help="Render and write the files under output/ but do not upload.")
    parser.add_argument("--dry-run", action="store_true", help="Everything but the upload.")
    parser.add_argument("--privacy", type=str, choices=["public", "unlisted", "private"], default="public", help="YouTube privacy of the upload (default: public).")
    parser.add_argument("--help-commands", "--commands", action="store_true", help="List the chat triggers and commands.")
    return parser.parse_args(argv)


def main() -> int:
    if any(arg in ("help", "ayuda", "--help-commands", "--commands") for arg in sys.argv[1:]):
        from scripts.help import print_help
        print_help()
        return 0

    args = parse_args()
    from services.motion_pipeline import run_motion_pipeline
    try:
        run_motion_pipeline(topic=args.topic, export_only=args.export_only, dry_run=args.dry_run, privacy=args.privacy, kind=args.motion_kind, fmt=args.motion_format)
    except Exception as exc:
        logger.error("Motion Graphics pipeline failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
