from services.motion_generator import _norm, looks_english, quote_supported

FACTS = _norm("The game's engine streams the open world from the SSD in small chunks, so the player never sees a loading screen while driving.")


def test_english_passes():
    assert looks_english("Your SSD is much faster than a hard drive because it has no moving parts.")


def test_spanish_is_rejected():
    assert not looks_english("Tu disco duro es mucho más lento que el SSD porque tiene partes móviles.")


def test_accents_rejected_even_when_short():
    assert not looks_english("¿Qué es esto?")


def test_exact_quote_supported():
    assert quote_supported("streams the open world from the SSD in small chunks", FACTS)


def test_small_difference_tolerated():
    assert quote_supported("streams the open world from the SSD in small chunk", FACTS)


def test_invented_quote_rejected():
    assert not quote_supported("the engine renders every frame on a quantum computer", FACTS)


def test_too_short_quote_rejected():
    assert not quote_supported("open world", FACTS)


# ---- fix / decode formats (niche research, Nov 2026) ----
from services.motion_generator import FORMAT_RULES, FORMATS, MotionProject, MotionSceneModel, make_validator  # noqa: E402

_NARR = "So your computer behaves differently once this one setting is changed, and you will notice it quickly."
_TYPES = ["bigText", "textWithAccent", "codeBlock", "textWithAccent", "list", "bigText", "textWithAccent", "codeBlock", "bigText", "textWithAccent", "list", "bigText", "outro"]


def _project(fmt, cursors, types=_TYPES):
    scenes = []
    for i, t in enumerate(types):
        extra = {}
        if t == "codeBlock":
            extra["code"] = ["Settings > System", "Display"]
        if t == "list":
            extra["items"] = ["First step", "Second step"]
        scenes.append(MotionSceneModel(type=t, text="Short line", accentText="Key word" if t in ("textWithAccent", "outro") else None,
                                       narration=_NARR, durationInFrames=90, cursor=cursors.get(i), **extra))
    return MotionProject(topic="t", screen_title="Test", title="A test title #siliconverdict #tech", description="One. Two.", tags=["a"] * 6,
                         pinned_comment="Why?", scenes=scenes, format=fmt)


def test_new_formats_are_registered():
    for name in ("fix", "decode"):
        assert name in FORMATS and name in FORMAT_RULES


def test_fix_format_passes_with_steps_and_cursor():
    assert make_validator(None, None, "fix")(_project("fix", {2: "select", 4: "drag", 7: "click"})) == []


def test_fix_format_needs_a_codeblock():
    types = [t if t != "codeBlock" else "textWithAccent" for t in _TYPES]
    types = ["bigText", "textWithAccent", "list", "textWithAccent", "list", "bigText", "textWithAccent", "list", "bigText", "textWithAccent", "list", "bigText", "outro"]
    problems = make_validator(None, None, "fix")(_project("fix", {2: "drag", 4: "drag"}, types))
    assert any("codeBlock" in p for p in problems)


def test_fix_format_needs_the_cursor_twice():
    problems = make_validator(None, None, "fix")(_project("fix", {2: "select"}))
    assert any("cursor" in p for p in problems)


def test_decode_format_needs_a_select_cursor():
    assert any("select" in p for p in make_validator(None, None, "decode")(_project("decode", {4: "drag"})))
    assert make_validator(None, None, "decode")(_project("decode", {0: "select", 4: "drag"})) == []
