#!/usr/bin/env python3
"""Refreshes the 'Latest video' card of the portal hero (docs/index.html, between the LATEST markers) with the newest PUBLIC video of the YouTube channel:
its cover (cropped from the thumbnail to 9:16, saved as docs/assets/latest/cover.jpg), title, date and links to YouTube and TikTok.

  python scripts/update_latest_video.py --tiktok-id 7706335532384521494     # the TikTok video id of the same video (the number at the end of its URL)
  python scripts/update_latest_video.py                                      # TikTok link falls back to the profile

TikTok has no API here, so its video id is passed by hand (the profile grid of TikTok Studio / the video URL shows it)."""
import argparse
import html
import re
import sys
import subprocess
from datetime import datetime
from io import BytesIO
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from PIL import Image  # noqa: E402

from services import yt_analytics as ya  # noqa: E402

INDEX = BASE / "docs" / "index.html"
COVER = BASE / "docs" / "assets" / "latest" / "cover.jpg"


def latest_public() -> dict:
    yt, _ = ya._services()
    ids = [i["contentDetails"]["videoId"] for i in yt.playlistItems().list(playlistId=ya.channel()["uploads"], part="contentDetails", maxResults=10).execute()["items"]]
    items = yt.videos().list(id=",".join(ids), part="snippet,status").execute()["items"]
    pub = [v for v in items if v["status"]["privacyStatus"] == "public"]
    return max(pub, key=lambda v: v["snippet"]["publishedAt"])


def save_cover(vid: str) -> None:
    raw = subprocess.run(["curl", "-sfL", f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg"], capture_output=True, check=True).stdout  # curl: the system certificates
    im = Image.open(BytesIO(raw)).convert("RGB")
    w, h = im.size
    cw = round(h * 9 / 16)  # Shorts thumbnails are 16:9 with the vertical frame in the middle
    x = (w - cw) // 2
    COVER.parent.mkdir(parents=True, exist_ok=True)
    im.crop((x, 0, x + cw, h)).save(COVER, quality=88, optimize=True)


def card(v: dict, tiktok_id: str | None) -> str:
    vid = v["id"]
    title = re.sub(r"\s*#[A-Za-z]\w*", "", v["snippet"]["title"]).strip()
    day = datetime.fromisoformat(v["snippet"]["publishedAt"].replace("Z", "+00:00")).strftime("%d %b %Y").lstrip("0")
    yt_url = f"https://www.youtube.com/shorts/{vid}"
    tt_url = f"https://www.tiktok.com/@siliconverdict/video/{tiktok_id}" if tiktok_id else "https://www.tiktok.com/@siliconverdict"
    mono = lambda n: f'<span class="mono" style="--i:url(assets/icons/{n}.svg)"></span>'  # noqa: E731
    return f'''<div class="latest">
            <div class="lt-bar"><span class="lt-dot"></span><b>Latest video</b><em>{html.escape(day)}</em></div>
            <div class="lt-body">
              <a class="lt-cover" href="{yt_url}" target="_blank" rel="noopener" aria-label="Watch {html.escape(title)} on YouTube"><img src="assets/latest/cover.jpg" alt="Cover of {html.escape(title)}" width="404" height="720"><span class="lt-play">{mono('ui-play')}</span></a>
              <div class="lt-info">
                <small>New on both channels</small>
                <h3>{html.escape(title)}</h3>
                <div class="lt-links">
                  <a class="lt-btn" href="{yt_url}" target="_blank" rel="noopener">{mono('m/youtube')}<span>Watch on YouTube</span>{mono('ui-arrow-right')}</a>
                  <a class="lt-btn" href="{tt_url}" target="_blank" rel="noopener">{mono('tiktok')}<span>Watch on TikTok</span>{mono('ui-arrow-right')}</a>
                </div>
              </div>
            </div>
          </div>'''


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tiktok-id", default=None)
    args = ap.parse_args()
    v = latest_public()
    save_cover(v["id"])
    s = INDEX.read_text(encoding="utf-8")
    pat = re.compile(r"(<!-- LATEST:start -->).*?(<!-- LATEST:end -->)", re.S)
    if not pat.search(s):
        sys.exit("LATEST markers not found in docs/index.html")
    INDEX.write_text(pat.sub(lambda m: f"{m.group(1)}\n          {card(v, args.tiktok_id)}\n          {m.group(2)}", s), encoding="utf-8")
    print(f"latest video: {v['snippet']['title'][:60]} ({v['id']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
