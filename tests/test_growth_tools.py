"""Early stats cache, cover styles, price moves, comments and the whole batch main() with stubs."""
import json
import sys
from datetime import date, timedelta
from types import SimpleNamespace


from services import comments, prices, yt_analytics
from services.motion_pipeline import cover_style


def test_cover_style_is_stable_and_uses_both_styles():
    assert cover_style("Same title") == cover_style("Same title")
    assert {cover_style(f"Video {i}") for i in range(40)} == {"a", "b"}


def test_price_moves_and_history(tmp_path, monkeypatch):
    monkeypatch.setattr(prices, "PRICES_DIR", tmp_path)
    (tmp_path / "2026-11-22.json").write_text(json.dumps({"prices": {"rtx:5070": {"price": 600}, "rtx:5080": {"price": 1000}, "rtx:4060": {"price": None}}}))
    (tmp_path / "2026-11-23.json").write_text(json.dumps({"prices": {"rtx:5070": {"price": 540}, "rtx:5080": {"price": 1010}, "rtx:4060": {"price": 300}}}))
    assert [(m["key"], m["pct"]) for m in prices.moves(5)] == [("rtx:5070", -10.0)]  # 5080 moved 1 %, 4060 had no earlier price
    assert prices.history("rtx:5070") == [("2026-11-22", 600.0), ("2026-11-23", 540.0)]


def test_early_report_caches_finished_windows(tmp_path, monkeypatch):
    calls = []

    class Reports:
        def query(self, **kw):
            calls.append(kw["filters"])
            return SimpleNamespace(execute=lambda: {"columnHeaders": [{"name": "video"}, {"name": "views"}, {"name": "engagedViews"}, {"name": "averageViewPercentage"}], "rows": [["x", 50, 20, 41.0]]})

    monkeypatch.setattr(yt_analytics, "_services", lambda: (None, SimpleNamespace(reports=lambda: Reports())))
    old = str(date.today() - timedelta(days=10))
    vids = [{"video_id": "old1", "published": old + "T10:00:00Z", "privacy": "public"},
            {"video_id": "new1", "published": str(date.today()) + "T10:00:00Z", "privacy": "public"},
            {"video_id": "sched", "published": old + "T10:00:00Z", "privacy": "private"}]
    cache = tmp_path / "early.json"
    assert yt_analytics.early_report(vids, cache)["old1"]["views"] == 50
    yt_analytics.early_report(vids, cache)
    assert calls == ["video==old1"]  # the new and the scheduled videos are skipped; the second run reads the cache


def _thread(cid, author, text, at, replies=()):
    return {"id": cid, "snippet": {"topLevelComment": {"snippet": {"videoId": "v", "authorDisplayName": author, "textOriginal": text, "publishedAt": at, "authorChannelId": {"value": author}}}},
            "replies": {"comments": [{"snippet": {"authorChannelId": {"value": r}}} for r in replies]}}


def test_unanswered_skips_own_answered_and_old_comments(monkeypatch):
    now = date.today().isoformat() + "T08:00:00Z"
    old = (date.today() - timedelta(days=30)).isoformat() + "T08:00:00Z"
    items = [_thread("1", "fan", "Great video", now), _thread("2", "ME", "pinned by me", now), _thread("3", "fan2", "answered", now, replies=["ME"]), _thread("4", "fan3", "too old", old)]
    yt = SimpleNamespace(channels=lambda: SimpleNamespace(list=lambda **k: SimpleNamespace(execute=lambda: {"items": [{"id": "ME"}]})),
                         commentThreads=lambda: SimpleNamespace(list=lambda **k: SimpleNamespace(execute=lambda: {"items": items})))
    monkeypatch.setattr(comments, "_client", lambda: yt)
    assert [c["thread_id"] for c in comments.unanswered(7)] == ["1"]


def test_whole_batch_with_stubs(tmp_path, monkeypatch):
    from scripts import genera_batch as gb
    import services.motion_pipeline as mp
    monkeypatch.setattr(gb, "LATEST", tmp_path / "latest.json")
    monkeypatch.setattr(gb, "LOG", tmp_path / "log.json")
    monkeypatch.setattr(gb, "format_stats", lambda: {})
    monkeypatch.setattr(gb, "ranked_slots", lambda: gb.DEFAULT_SLOTS_UTC)
    monkeypatch.setattr(gb, "every_pick", lambda picks: (None, "test"))
    monkeypatch.setattr(gb, "prepare_with_fallback", lambda p, plan: f"prep-{p['format']}")
    monkeypatch.setattr(gb, "small_copy", lambda src, dst: dst)
    monkeypatch.setattr(mp, "finish_motion_video", lambda prep, export_only=True: {"youtube_video": str(tmp_path / f"{prep}.mp4"), "tiktok_video": "t.mp4", "title": f"Title {prep}", "cover_style": "b", "tiktok_cover": ""})
    monkeypatch.setattr(gb.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout="https://youtu.be/ABC123", stderr="", returncode=0))
    import scripts.health_check as hc
    monkeypatch.setattr(hc, "run", lambda: [])
    import services.notify as nt
    sent = []
    monkeypatch.setattr(nt, "notify", lambda t, m, webhook=None: sent.append(t))
    monkeypatch.setattr(sys, "argv", ["genera_batch", "--count", "2", "--date", "2026-12-01", "--seed", "1", "--no-every"])
    assert gb.main() == 0
    manifest = json.loads((tmp_path / "latest.json").read_text())
    assert len(manifest) == 2 and all(e["video_id"] == "ABC123" and e["cover_style"] == "b" for e in manifest)
    assert [e["cover_style"] for e in json.loads((tmp_path / "log.json").read_text())] == ["b", "b"]
    assert sent == ["Silicon Verdict: batch finished"]


def test_batch_does_not_start_when_the_health_check_fails(monkeypatch):
    from scripts import genera_batch as gb
    import scripts.health_check as hc
    import services.notify as nt
    sent = []
    monkeypatch.setattr(gb, "format_stats", lambda: {})
    monkeypatch.setattr(gb, "ranked_slots", lambda: gb.DEFAULT_SLOTS_UTC)
    monkeypatch.setattr(hc, "run", lambda: [("FAIL", "YouTube token", "dead")])
    monkeypatch.setattr(nt, "notify", lambda t, m, webhook=None: sent.append(t))
    monkeypatch.setattr(sys, "argv", ["genera_batch", "--count", "1", "--no-every"])
    assert gb.main() == 1 and sent == ["Silicon Verdict: batch not started"]


def test_count_limits_the_plan():
    from scripts.genera_batch import pick_formats
    import random
    assert len(pick_formats({}, random.Random(0), n=2)) == 2
