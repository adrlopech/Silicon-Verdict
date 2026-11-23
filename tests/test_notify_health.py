from scripts import health_check
from services import notify as notify_mod


def test_notify_never_raises_and_posts_webhook(monkeypatch):
    sent = {}
    monkeypatch.setattr(notify_mod.sys, "platform", "linux")
    import requests
    monkeypatch.setattr(requests, "post", lambda url, json, timeout: sent.update(url=url, json=json))
    notify_mod.notify("t", 'say "hi"', webhook="http://x.test/hook")
    assert sent["url"] == "http://x.test/hook" and "hi" in sent["json"]["text"]
    monkeypatch.setattr(requests, "post", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
    notify_mod.notify("t", "m", webhook="http://x.test/hook")  # swallowed


def test_health_run_survives_a_crashing_check(monkeypatch):
    def boom():
        raise RuntimeError("x")
    monkeypatch.setattr(health_check, "CHECKS", [boom, lambda: (health_check.OK, "fine", "ok")])
    res = health_check.run()
    assert res[0][0] == health_check.WARN and res[1][0] == health_check.OK
