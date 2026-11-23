"""Comments of the channel's videos: the ones nobody answered yet, a suggested reply for each, and (with approval) posting it.

Needs the scope youtube.force-ssl (scripts/authenticate_yt.py asks for it; an older token gets a clear error). A reply is only ever posted by `post_reply`, which the
command line calls one comment at a time after the operator says yes: nothing here answers on its own.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"


class CommentsUnavailable(RuntimeError):
    """The token lacks the comments scope."""


def _client():
    from services.youtube import YouTubeService

    svc = YouTubeService()
    client = svc.get_authenticated_client()
    from google.oauth2.credentials import Credentials
    if SCOPE not in (Credentials.from_authorized_user_file(str(svc.token_file)).scopes or []):
        raise CommentsUnavailable("the token lacks the comments scope: run `python scripts/authenticate_yt.py` and approve it (guide/publishing.md)")
    return client


def unanswered(days: int = 7, limit: int = 100) -> List[Dict[str, Any]]:
    """Top-level comments of the last `days` days on the channel's videos that have no reply from the channel yet, newest first."""
    yt = _client()
    me = yt.channels().list(mine=True, part="id").execute()["items"][0]["id"]
    since = datetime.now(timezone.utc) - timedelta(days=days)
    out: List[Dict[str, Any]] = []
    token = None
    while len(out) < limit:
        res = yt.commentThreads().list(allThreadsRelatedToChannelId=me, part="snippet,replies", maxResults=100, order="time", pageToken=token).execute()
        for t in res.get("items", []):
            top = t["snippet"]["topLevelComment"]["snippet"]
            when = datetime.fromisoformat(top["publishedAt"].replace("Z", "+00:00"))
            if when < since:
                return out
            if top.get("authorChannelId", {}).get("value") == me:
                continue
            if any(r["snippet"].get("authorChannelId", {}).get("value") == me for r in t.get("replies", {}).get("comments", [])):
                continue
            out.append({"thread_id": t["id"], "video_id": top["videoId"], "author": top["authorDisplayName"], "text": top["textOriginal"], "likes": top.get("likeCount", 0), "at": top["publishedAt"]})
        token = res.get("nextPageToken")
        if not token:
            break
    return out


class _Reply(BaseModel):
    reply: str = Field(description="the reply, 1-2 short sentences, in the language of the comment; empty string when it should not be answered (spam, insult, link)")


def suggest_reply(comment: str, video_title: str) -> str:
    """A short, friendly, honest reply in the channel's voice; "" when the comment is not worth answering."""
    from services.gemini_client import generate_structured

    system = ("You answer comments for a small tech Shorts channel (Silicon Verdict: PC hardware, prices, explainers). Warm, direct, one or two short sentences, no hashtags, no emojis spam, "
              "never invent specs or prices, never promise future videos you were not told about, never point to a pinned comment, link or description you cannot see. Answer a question only if the comment and the video title are enough to be sure of the answer; "
              "otherwise thank them and ask one short question to understand (for a vague 'how to fix this': which device and what happens). "
              "Return an empty reply for spam, insults and links.")
    obj, _tokens, _model = generate_structured(prompt=f"Video: {video_title}\nComment: {comment[:500]}", system_instruction=system, schema=_Reply, temperature=0.5, max_output_tokens=300, provider_first="cloudflare", provider_models=["@cf/meta/llama-3.3-70b-instruct-fp8-fast"])  # short answer: the quick model first, Gemini if it fails
    return obj.reply.strip()


def post_reply(thread_id: str, text: str) -> None:
    _client().comments().insert(part="snippet", body={"snippet": {"parentId": thread_id, "textOriginal": text}}).execute()
