"""YouTube Analytics client: the channel's real numbers (views, engaged views, average view, retention curve, traffic).

Uses the OAuth token of data/token.json, which needs the scopes youtube.readonly and yt-analytics.readonly (granted by `python scripts/authenticate_yt.py`).
Only reads; nothing here writes to YouTube. Every function returns plain dicts and lists so the report and the sync can use them.
"""
import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from config.settings import settings

logger = logging.getLogger(__name__)

NEEDED_SCOPES = ("https://www.googleapis.com/auth/yt-analytics.readonly", "https://www.googleapis.com/auth/youtube.readonly")


class AnalyticsUnavailable(RuntimeError):
    """The token is missing or lacks the analytics scopes (run scripts/authenticate_yt.py)."""


def _creds():
    from google.oauth2.credentials import Credentials

    path = settings.resolve_token_path()
    if not path.is_file():
        raise AnalyticsUnavailable(f"no token at {path}: run `python scripts/authenticate_yt.py`")
    creds = Credentials.from_authorized_user_file(str(path))
    missing = [s.rsplit("/", 1)[-1] for s in NEEDED_SCOPES if s not in (creds.scopes or [])]
    if missing:
        raise AnalyticsUnavailable(f"the token lacks the scopes {missing}: run `python scripts/authenticate_yt.py` and approve them")
    return creds


def _services():
    from googleapiclient.discovery import build

    creds = _creds()
    return build("youtube", "v3", credentials=creds, cache_discovery=False), build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)


def _query(analytics, days: int, **kw) -> Dict[str, Any]:
    end = date.today()
    return analytics.reports().query(ids="channel==MINE", startDate=str(end - timedelta(days=days)), endDate=str(end), **kw).execute()


def _rows(res: Dict[str, Any]) -> List[Dict[str, Any]]:
    names = [h["name"] for h in res.get("columnHeaders", [])]
    return [dict(zip(names, r)) for r in res.get("rows", [])]


def channel() -> Dict[str, Any]:
    yt, _ = _services()
    item = yt.channels().list(mine=True, part="id,snippet,statistics,contentDetails").execute()["items"][0]
    st = item["statistics"]
    return {"id": item["id"], "title": item["snippet"]["title"], "subscribers": int(st.get("subscriberCount", 0)), "videos": int(st.get("videoCount", 0)), "views": int(st.get("viewCount", 0)),
            "uploads": item["contentDetails"]["relatedPlaylists"]["uploads"]}


def videos(limit: int = 50) -> List[Dict[str, Any]]:
    """The channel's uploads (newest first) with title, publish date, length in seconds and public counters."""
    import re

    yt, _ = _services()
    ch = channel()
    ids: List[str] = []
    token: Optional[str] = None
    while len(ids) < limit:
        res = yt.playlistItems().list(playlistId=ch["uploads"], part="contentDetails", maxResults=50, pageToken=token).execute()
        ids += [i["contentDetails"]["videoId"] for i in res.get("items", [])]
        token = res.get("nextPageToken")
        if not token:
            break
    out = []
    for k in range(0, len(ids[:limit]), 50):
        for it in yt.videos().list(id=",".join(ids[k:k + 50]), part="snippet,contentDetails,statistics,status").execute().get("items", []):
            m = re.fullmatch(r"PT(?:(\d+)M)?(?:(\d+)S)?", it["contentDetails"]["duration"])
            secs = (int(m[1] or 0) * 60 + int(m[2] or 0)) if m else 0
            out.append({"video_id": it["id"], "title": it["snippet"]["title"], "published": it["snippet"]["publishedAt"], "seconds": secs, "privacy": it["status"]["privacyStatus"],
                        "views": int(it["statistics"].get("viewCount", 0)), "likes": int(it["statistics"].get("likeCount", 0)), "comments": int(it["statistics"].get("commentCount", 0))})
    return out


def video_report(days: int = 90) -> Dict[str, Dict[str, Any]]:
    """Per video over the last `days`: views, engaged views, average view percentage and duration, subscribers gained, likes, comments, shares."""
    _, an = _services()
    res = _query(an, days, metrics="views,engagedViews,averageViewPercentage,averageViewDuration,subscribersGained,likes,comments,shares", dimensions="video", sort="-views", maxResults=200)
    return {r["video"]: r for r in _rows(res)}


def retention_curve(video_id: str, days: int = 90) -> List[float]:
    """Audience watch ratio at 1 % steps of the video (the first point is above 1 when people replay a loop). Empty if YouTube has no curve yet."""
    _, an = _services()
    res = _query(an, days, metrics="audienceWatchRatio", dimensions="elapsedVideoTimeRatio", filters=f"video=={video_id}")
    return [r["audienceWatchRatio"] for r in _rows(res)]


def traffic_sources(days: int = 90) -> List[Dict[str, Any]]:
    _, an = _services()
    return _rows(_query(an, days, metrics="views,averageViewPercentage", dimensions="insightTrafficSourceType", sort="-views", maxResults=10))


def daily(days: int = 28) -> List[Dict[str, Any]]:
    _, an = _services()
    return _rows(_query(an, days, metrics="views,estimatedMinutesWatched,averageViewPercentage,subscribersGained", dimensions="day", sort="day"))


def retention_at(curve: List[float], ratio: float) -> Optional[float]:
    """The watch ratio near a point of the video (0.2 = a fifth of the way in), or None."""
    if not curve:
        return None
    return curve[min(len(curve) - 1, max(0, round(ratio * (len(curve) - 1))))]
