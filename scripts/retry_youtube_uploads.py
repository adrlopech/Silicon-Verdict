#!/usr/bin/env python3
"""Uploads again the videos of a genera batch manifest that YouTube refused (uploadLimitExceeded: a daily limit on uploads that frees up after about 24 hours).

  python scripts/retry_youtube_uploads.py data/batch_2026-11-11.json

Each entry without a video_id is sent with its publishAt (title, description and hashtags come from the manifest, so no .txt next to the file is needed);
the manifest is updated with the new ids. Exit code 1 if something is still refused."""
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from services.youtube import upload_video_resumable  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = Path(sys.argv[1])
    batch = json.loads(path.read_text())
    failed = 0
    for e in batch:
        if e.get("video_id"):
            continue
        try:
            url = upload_video_resumable(file_path=e["video"], title=e["title"], description=e.get("description") or e["caption"], tags=[h.lstrip("#") for h in e["hashtags"]], privacy_status="public", is_short=True, publish_at=e["publish_at"])
            e["video_id"] = str(url).rsplit("/", 1)[-1]
            print(f"{e['format']:<10} {e['publish_at']}  ok {url}")
        except Exception as exc:  # noqa: BLE001 - report and carry on with the next one
            failed += 1
            print(f"{e['format']:<10} {e['publish_at']}  FAILED: {str(exc)[-150:]}")
    path.write_text(json.dumps(batch, ensure_ascii=False, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
