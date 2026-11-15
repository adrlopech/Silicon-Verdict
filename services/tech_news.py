"""Today's tech headlines, from public RSS feeds, as the SOURCE TEXT of a news-bulletin video ("Tech Briefing").

A story that several outlets cover ranks higher than one that a single outlet publishes. The text lists, for every story, the outlets that reported it, the headline and the feed's own short summary;
the script must paraphrase it (never copy sentences), name the outlet it relies on and hedge anything the outlets only report ("reportedly"). Nothing here is stored: every call reads the feeds again.
"""
import html
import logging
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET

import requests

logger = logging.getLogger(__name__)

FEEDS: Dict[str, str] = {
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "TechCrunch": "https://techcrunch.com/feed/",
    "Engadget": "https://www.engadget.com/rss.xml",
    "Tom's Hardware": "https://www.tomshardware.com/feeds/all",
    "Hacker News": "https://hnrss.org/frontpage",
}
MAX_AGE_HOURS = 48
UA = {"User-Agent": "Mozilla/5.0 (compatible; tech-briefing-reader)"}
_ATOM = "{http://www.w3.org/2005/Atom}"
_TAGS = re.compile(r"<[^>]+>")
_STOP = {"the", "and", "for", "with", "that", "this", "from", "your", "have", "will", "what", "when", "into", "about", "after", "over", "more", "than", "just", "how", "why", "are", "its", "was", "new", "now", "has", "can", "not", "but", "you", "all", "one", "who", "may", "get", "gets", "says", "said"}


def _clean(text: Optional[str], limit: int = 300) -> str:
    t = html.unescape(_TAGS.sub(" ", text or ""))
    t = re.sub(r"\s+", " ", t).strip()
    return t[:limit].rsplit(" ", 1)[0] + "…" if len(t) > limit else t


def _when(item: ET.Element) -> Optional[datetime]:
    raw = (item.findtext("pubDate") or item.findtext(f"{_ATOM}published") or item.findtext(f"{_ATOM}updated") or item.findtext("{http://purl.org/dc/elements/1.1/}date") or "").strip()
    if not raw:
        return None
    try:
        d = parsedate_to_datetime(raw)
    except Exception:
        try:
            d = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def fetch_items(now: Optional[datetime] = None) -> List[dict]:
    """Every recent item of every feed that answers: {outlet, title, summary, when}. A feed that fails is skipped."""
    now = now or datetime.now(timezone.utc)
    out: List[dict] = []
    for outlet, url in FEEDS.items():
        try:
            r = requests.get(url, headers=UA, timeout=15)
            r.raise_for_status()
            root = ET.fromstring(r.content)
        except Exception as exc:
            logger.warning("News feed %s unavailable: %s", outlet, str(exc)[:100])
            continue
        for it in root.findall(".//item") + root.findall(f".//{_ATOM}entry"):
            title = _clean(it.findtext("title") or it.findtext(f"{_ATOM}title"), 160)
            when = _when(it)
            if not title or (when and now - when > timedelta(hours=MAX_AGE_HOURS)):
                continue
            summary = _clean(it.findtext("description") or it.findtext(f"{_ATOM}summary") or it.findtext("{http://purl.org/rss/1.0/modules/content/}encoded"))
            out.append({"outlet": outlet, "title": title, "summary": summary, "when": when or now})
    return out


def _tokens(title: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", title.lower()) if len(w) > 2 and w not in _STOP}


def cluster(items: List[dict]) -> List[dict]:
    """Groups items about the same story (shared words in the headline) and ranks the groups: more outlets first, then the newest."""
    groups: List[dict] = []
    for it in sorted(items, key=lambda x: x["when"], reverse=True):
        toks = _tokens(it["title"])
        for g in groups:
            common = toks & g["tokens"]
            if len(common) >= 3 or (toks and g["tokens"] and len(common) / min(len(toks), len(g["tokens"])) >= 0.6 and len(common) >= 2):
                g["items"].append(it)
                g["tokens"] |= toks
                break
        else:
            groups.append({"items": [it], "tokens": set(toks)})
    for g in groups:
        g["outlets"] = sorted({i["outlet"] for i in g["items"]})
        g["lead"] = max(g["items"], key=lambda i: len(i["summary"]))
        g["when"] = max(i["when"] for i in g["items"])
    return sorted(groups, key=lambda g: (-len(g["outlets"]), -g["when"].timestamp()))


def build_source_text(max_stories: int = 8, now: Optional[datetime] = None, items: Optional[List[dict]] = None) -> str:
    """The SOURCE TEXT of a bulletin: the top stories with their outlets. Raises RuntimeError when fewer than three stories can be read."""
    now = now or datetime.now(timezone.utc)
    groups = cluster(items if items is not None else fetch_items(now))[:max_stories]
    if len(groups) < 3:
        raise RuntimeError("Not enough tech news could be read to make a bulletin (feeds unreachable?).")
    lines = [f"[Tech news read on {now.strftime('%d %B %Y')}, newest and most widely covered stories first]"]
    for n, g in enumerate(groups, 1):
        lead = g["lead"]
        hours = max(0, int((now - g["when"]).total_seconds() // 3600))
        lines.append(f"Story {n} (reported by {', '.join(g['outlets'])}; {hours} hours ago): {lead['title']}. {lead['summary']}".strip())
    return "\n".join(lines)


if __name__ == "__main__":  # python -m services.tech_news: prints today's source text
    logging.basicConfig(level=logging.INFO)
    print(build_source_text())
