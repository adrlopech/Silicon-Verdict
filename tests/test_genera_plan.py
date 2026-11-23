"""run_plan overlaps the three stages of a batch (prepare N+1, render N, upload N-1) and survives failures."""
import threading
import time

from scripts.genera_batch import run_plan


def make_plan(n: int, fmt: str = "myth"):
    return [{"format": fmt, "slot": f"{13 + 3 * i:02d}:00", "name": f"v{i}"} for i in range(n)]


def test_stages_overlap_and_order_is_kept():
    events, lock = [], threading.Lock()

    def log(kind, name):
        with lock:
            events.append((kind, name, time.time()))

    def prepare(p):
        log("prepare_start", p["name"]); time.sleep(0.2); log("prepare_end", p["name"]); return p["name"]

    def finish(prep):
        log("render_start", prep); time.sleep(0.4); log("render_end", prep); return {"res": prep}

    published = []

    def publish(p, res, now):
        time.sleep(0.2); published.append((p["name"], res["res"], now))

    start = time.time()
    run_plan(make_plan(3), prepare, finish, publish, public_first=True)
    elapsed = time.time() - start
    assert published == [("v0", "v0", True), ("v1", "v1", False), ("v2", "v2", False)]  # upload order = plan order, only the first is "now"
    by = {(k, n): t for k, n, t in events}
    assert by[("prepare_start", "v1")] < by[("render_end", "v0")]  # video 1 is prepared while video 0 renders
    assert by[("prepare_start", "v2")] < by[("render_end", "v1")]
    assert elapsed < 2.3  # sequential would take 3 * (0.2 + 0.4 + 0.2) = 2.4 s, the overlap about 1.8 s (the ordering asserts above are the real test; this only guards against fully serial code)


def test_a_failed_prepare_or_render_skips_only_that_video(capsys):
    def prepare(p):
        if p["name"] == "v1":
            raise ValueError("script rejected")
        return p["name"]

    def finish(prep):
        if prep == "v2":
            raise RuntimeError("render crashed")
        return {"res": prep}

    published = []
    run_plan(make_plan(4), prepare, finish, lambda p, res, now: published.append(p["name"]))
    assert published == ["v0", "v3"]
    assert capsys.readouterr().out.count("FAILED") == 2


def test_game_capable_formats_are_not_prefetched():
    order, lock = [], threading.Lock()

    def prepare(p):
        with lock:
            order.append(("prepare", p["name"]))
        return p["name"]

    def finish(prep):
        time.sleep(0.2)
        with lock:
            order.append(("finish", prep))
        return {"res": prep}

    plan = make_plan(2, fmt="classic")
    run_plan(plan, prepare, finish, lambda p, res, now: None)
    assert order == [("prepare", "v0"), ("finish", "v0"), ("prepare", "v1"), ("finish", "v1")]  # classic may pick game footage: strictly one after the other


def test_fallback_picks_banked_formats_not_already_in_the_plan():
    from scripts.genera_batch import choose_fallback
    plan = [{"format": "top5"}, {"format": "versus"}, {"format": "whatif"}, {"format": "numbers"}]
    stock = {"versus": 5, "myth": 3, "whatif": 4, "evolution": 0, "decode": 2, "tier": 1}
    assert choose_fallback(plan, "top5", stock) == ["myth", "decode", "tier"]  # versus and whatif are taken, evolution has no stock
    assert choose_fallback(plan, "numbers", {}) == []  # nothing banked: nothing to fall back to


def test_prepare_with_fallback_swaps_the_format_and_keeps_hand_written_scripts(monkeypatch, capsys):
    import scripts.genera_batch as gb
    import services.motion_pipeline as mp
    import services.story_bank as sb

    def failing_prepare(p):
        raise RuntimeError("503 UNAVAILABLE")

    monkeypatch.setattr(gb, "prepare", failing_prepare)
    monkeypatch.setattr(sb, "ready_by_format", lambda series="motion": {"myth": 2})
    monkeypatch.setattr(mp, "prepare_motion_video", lambda **kw: ("prepared", kw))
    plan = [{"format": "top5", "why": "weighted draw"}, {"format": "versus", "why": "proven"}]
    prep = gb.prepare_with_fallback(plan[0], plan)
    assert prep == ("prepared", {"fmt": "myth", "bank_only": True})
    assert plan[0]["format"] == "myth" and "fallback for top5" in plan[0]["why"]

    hand = {"format": "tier", "script": "data/scripts/x.json", "why": "mine"}
    try:
        gb.prepare_with_fallback(hand, [hand])
        raise AssertionError("a hand-written script must not be replaced")
    except RuntimeError:
        assert hand["format"] == "tier"
