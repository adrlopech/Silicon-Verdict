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
    assert elapsed < 0.2 + 3 * 0.4 + 0.2 + 0.3  # sequential would take 3 * (0.2 + 0.4 + 0.2) = 2.4 s


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
