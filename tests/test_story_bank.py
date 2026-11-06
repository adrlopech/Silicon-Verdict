from types import SimpleNamespace

from services import story_bank


class FakeStory(SimpleNamespace):
    @classmethod
    def model_validate_json(cls, raw):
        import json

        return cls(**json.loads(raw))

    def model_dump_json(self):
        import json

        return json.dumps(self.__dict__)


def _use_fake(monkeypatch):
    monkeypatch.setitem(story_bank.MODELS, "fake", FakeStory)


def test_pop_marks_used_and_release_returns_it(tmp_db, monkeypatch):
    _use_fake(monkeypatch)
    story_bank.add_story("fake", FakeStory(topic="t1"))
    assert story_bank.count_ready("fake") == 1
    s = story_bank.pop_story("fake")
    assert s.topic == "t1" and story_bank.count_ready("fake") == 0
    assert story_bank.release_story(s) is True
    assert story_bank.count_ready("fake") == 1


def test_accept_filter_leaves_rejected_stories(tmp_db, monkeypatch):
    _use_fake(monkeypatch)
    story_bank.add_story("fake", FakeStory(topic="skip"))
    story_bank.add_story("fake", FakeStory(topic="take"))
    s = story_bank.pop_story("fake", accept=lambda x: x.topic == "take")
    assert s.topic == "take" and story_bank.count_ready("fake") == 1


def test_release_of_foreign_story_is_noop(tmp_db):
    assert story_bank.release_story(FakeStory(topic="x")) is False


def test_topics_in_bank(tmp_db, monkeypatch):
    _use_fake(monkeypatch)
    story_bank.add_story("fake", FakeStory(topic="a"))
    assert story_bank.topics_in_bank("fake") == ["a"]
