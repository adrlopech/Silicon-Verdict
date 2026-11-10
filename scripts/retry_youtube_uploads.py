#!/usr/bin/env python3
"""Uploads again the videos of a genera batch manifest that YouTube refused (uploadLimitExceeded: a daily limit on uploads that frees up after about 24 hours).

  python scripts/retry_youtube_uploads.py data/batch_2026-11-11.json

Each entry without a video_id is sent with its publishAt; the manifest is updated with the new ids."""
import json
import re
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def main() -> int:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = Path(sys.argv[1])
    batch = json.loads(path.read_text())
    failed = 0
    for e in batch:
        if e.get("video_id"):
            continue
        r = subprocess.run([sys.executable, str(BASE / "scripts" / "upload_existing.py"), e["video"], "--publish-at", e["publish_at"]], cwd=BASE, capture_output=True, text=True)
        m = re.search(r"youtu\.be/([\w-]+)", r.stdout)
        print(f"{e['format']:<10} {e['publish_at']}  " + (f"ok https://youtu.be/{m[1]}" if m else "FAILED: " + (r.stdout + r.stderr)[-140:].replace("\n", " ")))
        if m:
            e["video_id"] = m[1]
        else:
            failed += 1
    path.write_text(json.dumps(batch, ensure_ascii=False, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
