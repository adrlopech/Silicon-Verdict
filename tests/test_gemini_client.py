import json

import pytest
import requests

from services import gemini_client as gc

PROV = ("cf", "http://llm.test/v1", "CF_KEY", "m")


class Resp:
    def __init__(self, status=200, content=None, headers=None, text=None):
        self.status_code, self.headers = status, headers or {}
        self._body = {"choices": [{"message": {"content": content}}], "usage": {"prompt_tokens": 1, "completion_tokens": 2}}
        self.text = text if text is not None else json.dumps(self._body)

    def json(self):
        return self._body


@pytest.fixture
def api(monkeypatch):
    calls = []
    queue = []

    def post(url, headers, json, timeout):
        calls.append(json)
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item
    monkeypatch.setattr(requests, "post", post)
    monkeypatch.setattr(gc, "_provider_key", lambda attr: "k")
    monkeypatch.setattr(gc.time, "sleep", lambda s: None)
    return calls, queue


def run(validate=None, attempts=3):
    return gc._compatible_one_model(PROV, "m", "prompt", "system", None, 0.5, validate, 500, attempts=attempts)


def test_rejected_draft_is_repaired_in_a_multi_turn_conversation(api):
    calls, queue = api
    queue += [Resp(content='{"n": 1}'), Resp(content='{"n": 2}')]
    obj, _, who = run(validate=lambda o: [] if o["n"] == 2 else ["n must be 2"])
    assert obj == {"n": 2} and who == "cf:m"
    second = calls[1]["messages"]
    assert second[-2] == {"role": "assistant", "content": '{"n": 1}'} and "n must be 2" in second[-1]["content"]


def test_gives_up_after_the_attempts_with_the_last_reason(api):
    _, queue = api
    queue += [Resp(content='{"n": 1}')] * 2
    with pytest.raises(ValueError, match="rejected by validator"):
        run(validate=lambda o: ["no"], attempts=2)


def test_rate_limit_is_busy_and_bad_key_is_fatal(api):
    _, queue = api
    queue.append(Resp(status=429, headers={"retry-after": "7"}, text="slow down"))
    with pytest.raises(gc._ProviderBusy) as busy:
        run()
    assert busy.value.wait == 7.0
    queue.append(Resp(status=401, text="bad key"))
    with pytest.raises(gc.GeminiUnavailable):
        run()


def test_server_errors_and_network_errors_are_retried(api):
    _, queue = api
    queue += [Resp(status=503, text="down"), requests.ConnectionError("reset"), Resp(content='{"ok": true}')]
    assert run()[0] == {"ok": True}


def test_classify_error_kinds():
    assert gc._classify(RuntimeError("429 RESOURCE_EXHAUSTED per day"))[0] == "daily"
    assert gc._classify(RuntimeError("503 UNAVAILABLE"))[0] == "transient"
    assert gc._classify(RuntimeError("404 NOT_FOUND"))[0] == "unusable"
