#!/usr/bin/env python3
"""Refreshes the 'Latest video' card of the portal hero (docs/index.html, between the LATEST markers) with the newest PUBLIC video of the YouTube channel:
its cover (cropped from the thumbnail to 9:16, saved as docs/assets/latest/cover.jpg), title, date and links to YouTube and TikTok.
It also refreshes the 'Latest videos' wall (between the RECENT markers): the next six public videos, their covers saved in docs/assets/recent/ (local copies,
so the portal never loads anything from a third party and its "no tracking" promise holds).

  python scripts/update_latest_video.py                 # reads the channel's public feed (no login), the TikTok button opens the profile, whose first video is the newest
  python scripts/update_latest_video.py --tiktok-id N   # pins the TikTok button to one video (the number at the end of its URL)
  python scripts/update_latest_video.py --api           # same, through the YouTube API (needs data/token.json)

GitHub Actions runs it every 15 minutes (.github/workflows/latest-video.yml) and commits only when a new public video appeared.
The feed lists public videos only, so scheduled (private) ones never show up before they are published. TikTok has no feed or API here."""
import argparse
import html
import re
import sys
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from io import BytesIO
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from PIL import Image  # noqa: E402


INDEX = BASE / "docs" / "index.html"
COVER = BASE / "docs" / "assets" / "latest" / "cover.jpg"


CHANNEL_ID = "UCm0Xb9KY_Hu12j1CijF2KHQ"


RECENT_DIR = BASE / "docs" / "assets" / "recent"
RECENT_COUNT = 6


def recent_from_feed() -> list:
    """The public videos of the feed, newest first, in the API's shape."""
    xml = subprocess.run(["curl", "-sfL", f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"], capture_output=True, check=True).stdout
    ns = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
    return [{"id": e.find("yt:videoId", ns).text, "snippet": {"title": e.find("a:title", ns).text, "publishedAt": e.find("a:published", ns).text}} for e in ET.fromstring(xml).findall("a:entry", ns)]


def latest_public() -> dict:
    from services import yt_analytics as ya

    yt, _ = ya._services()
    ids = [i["contentDetails"]["videoId"] for i in yt.playlistItems().list(playlistId=ya.channel()["uploads"], part="contentDetails", maxResults=10).execute()["items"]]
    items = yt.videos().list(id=",".join(ids), part="snippet,status").execute()["items"]
    pub = [v for v in items if v["status"]["privacyStatus"] == "public"]
    return max(pub, key=lambda v: v["snippet"]["publishedAt"])


def save_cover(vid: str, out: Path = COVER, height: int = 0) -> None:
    raw = subprocess.run(["curl", "-sfL", f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg"], capture_output=True, check=True).stdout  # curl: the system certificates
    im = Image.open(BytesIO(raw)).convert("RGB")
    w, h = im.size
    cw = round(h * 9 / 16)  # Shorts thumbnails are 16:9 with the vertical frame in the middle
    x = (w - cw) // 2
    im = im.crop((x, 0, x + cw, h))
    if height and im.height > height:
        im = im.resize((round(height * 9 / 16), height), Image.LANCZOS)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, quality=84, optimize=True, progressive=True)


def _clean_title(t: str) -> str:
    return re.sub(r"\s*#[A-Za-z]\w*", "", t).strip()


def _day(v: dict) -> str:
    return datetime.fromisoformat(v["snippet"]["publishedAt"].replace("Z", "+00:00")).strftime("%d %b %Y").lstrip("0")


def wall(videos: list) -> str:
    """The cards of the 'Latest videos' wall (9:16 covers that open the Short on YouTube)."""
    cards = []
    for v in videos:
        vid, title = v["id"], html.escape(_clean_title(v["snippet"]["title"]))
        cards.append(f'''<a class="vw-card" href="https://www.youtube.com/shorts/{vid}" target="_blank" rel="noopener" data-vid="{vid}"><span class="vw-cover"><img src="assets/recent/{vid}.jpg" alt="Cover of {title}" width="270" height="480" loading="lazy" decoding="async"></span><span class="vw-meta"><em>{html.escape(_day(v))}</em><b>{title}</b></span></a>''')
    return "\n          ".join(cards)


def update_wall(s: str, videos: list) -> str:
    """Rewrites the RECENT block when its videos changed; keeps docs/assets/recent/ to exactly the covers it shows."""
    pat = re.compile(r"(<!-- RECENT:start -->).*?(<!-- RECENT:end -->)", re.S)
    m = pat.search(s)
    if not m:
        return s
    ids = [v["id"] for v in videos]
    if re.findall(r'data-vid="([^"]+)"', m.group(0)) == ids:
        return s
    for v in videos:
        if not (RECENT_DIR / f"{v['id']}.jpg").exists():
            save_cover(v["id"], RECENT_DIR / f"{v['id']}.jpg", height=480)
    for f in RECENT_DIR.glob("*.jpg"):
        if f.stem not in ids:
            f.unlink()
    return pat.sub(lambda mm: f"{mm.group(1)}\n          {wall(videos)}\n          {mm.group(2)}", s)


def card(v: dict, tiktok_id: str | None, fan: list = ()) -> str:
    """The hero card: the latest cover, big, with the two previous covers fanned out behind it (from the 'Latest videos' wall)."""
    vid = v["id"]
    title = _clean_title(v["snippet"]["title"])
    day = _day(v)
    yt_url = f"https://www.youtube.com/shorts/{vid}"
    tt_url = f"https://www.tiktok.com/@siliconverdict/video/{tiktok_id}" if tiktok_id else "https://www.tiktok.com/@siliconverdict"
    mono = lambda n: f'<span class="mono" style="--i:url(assets/icons/{n}.svg)"></span>'  # noqa: E731
    tiktok = '<span class="mono brand tt"><i class="l1"></i><i class="l2"></i><i class="l3"></i></span>'  # the TikTok logo's three layers, coloured like the other icons (docs/site.css)
    return f'''<div class="latest" data-vid="{vid}">
            <div class="lt-bar"><span class="lt-dot"></span><b>Latest video</b><em>{html.escape(day)}</em></div>
            <div class="lt-body">
              <div class="lt-stack">{''.join(f'<img class="lt-fan f{k}" src="assets/recent/{f}.jpg" alt="" width="270" height="480" aria-hidden="true">' for k, f in enumerate(fan[:2], 1))}<a class="lt-cover" href="{yt_url}" target="_blank" rel="noopener" aria-label="Watch {html.escape(title)} on YouTube"><img src="assets/latest/cover.jpg" alt="Cover of {html.escape(title)}" width="404" height="720"><span class="lt-play">{mono('ui-play')}</span></a></div>
              <div class="lt-info">
                <small>New on both channels</small>
                <h3>{html.escape(title)}</h3>
                <div class="lt-links">
                  <a class="lt-btn" href="{yt_url}" target="_blank" rel="noopener">{mono('m/youtube')}<span>Watch on YouTube</span>{mono('ui-arrow-right')}</a>
                  <a class="lt-btn" href="{tt_url}" target="_blank" rel="noopener">{tiktok}<span>Watch on TikTok</span>{mono('ui-arrow-right')}</a>
                </div>
              </div>
            </div>
          </div>'''


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tiktok-id", default=None)
    ap.add_argument("--api", action="store_true", help="use the YouTube API instead of the public feed")
    args = ap.parse_args()
    feed = recent_from_feed()
    if not feed:
        sys.exit("the feed has no videos")
    v = latest_public() if args.api else feed[0]
    s = INDEX.read_text(encoding="utf-8")
    walled = update_wall(s, [x for x in feed if x["id"] != v["id"]][:RECENT_COUNT])
    if walled != s:
        INDEX.write_text(walled, encoding="utf-8")
        s = walled
        print("latest videos wall refreshed")
    pat = re.compile(r"(<!-- LATEST:start -->).*?(<!-- LATEST:end -->)", re.S)
    m = pat.search(s)
    if not m:
        sys.exit("LATEST markers not found in docs/index.html")
    same = f'<div class="latest" data-vid="{v["id"]}"' in m.group(0)
    tiktok_id = args.tiktok_id
    if same and not tiktok_id:  # keep a TikTok link pinned earlier with --tiktok-id
        pinned = re.search(r"tiktok\.com/@siliconverdict/video/(\d+)", m.group(0))
        tiktok_id = pinned.group(1) if pinned else None
    fan = [x["id"] for x in feed if x["id"] != v["id"]][:2]
    block = f"{m.group(1)}\n          {card(v, tiktok_id, fan)}\n          {m.group(2)}"
    if block == m.group(0):
        print("already up to date:", v["id"])
        return 0
    if not same:
        save_cover(v["id"])
    INDEX.write_text(s[:m.start()] + block + s[m.end():], encoding="utf-8")
    print(f"latest video: {v['snippet']['title'][:60]} ({v['id']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
