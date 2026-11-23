#!/usr/bin/env python3
"""Unanswered comments of the last days with a suggested reply each; you approve every reply before it is posted.

  python scripts/comments.py                 # list them and the suggestions, write notes/comments_<date>.md (nothing is posted)
  python scripts/comments.py --post          # ask y/n/edit for each suggestion and post the approved ones
  python scripts/comments.py --days 14

Needs the youtube.force-ssl scope: run scripts/authenticate_yt.py once (guide/publishing.md).
"""
import argparse
import sys
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from services import comments  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--post", action="store_true", help="ask for approval of each reply and post the approved ones")
    args = ap.parse_args()
    try:
        items = comments.unanswered(args.days)
    except comments.CommentsUnavailable as exc:
        print(exc)
        return 1
    if not items:
        print("No unanswered comments.")
        return 0
    from services import yt_analytics as ya
    titles = {v["video_id"]: v["title"] for v in ya.videos(limit=100)}
    lines = [f"# Unanswered comments ({date.today()}, last {args.days} days)", ""]
    posted = 0
    for c in items:
        title = titles.get(c["video_id"], c["video_id"])
        try:
            reply = comments.suggest_reply(c["text"], title)
        except Exception as exc:  # noqa: BLE001
            reply = ""
            print(f"(no suggestion: {exc})")
        lines += [f"## {c['author']} on {title[:60]}", f"> {c['text']}", "", f"Suggested: {reply or '(do not answer)'}", ""]
        print(f"\n{c['author']} on \"{title[:60]}\" ({c['likes']} likes)\n  > {c['text'][:300]}\n  suggested: {reply or '(do not answer)'}")
        if args.post and reply:
            ans = input("  post? [y / n / type your own reply] ").strip()
            if ans.lower() in ("y", "yes", "s", "si"):
                comments.post_reply(c["thread_id"], reply)
                posted += 1
            elif ans and ans.lower() not in ("n", "no"):
                comments.post_reply(c["thread_id"], ans)
                posted += 1
    notes = BASE_DIR / "notes"
    notes.mkdir(exist_ok=True)
    (notes / f"comments_{date.today()}.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{len(items)} unanswered; {posted} posted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
