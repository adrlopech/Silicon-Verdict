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


# ---- retention rules (content style study, Nov 2026) ----
from services.motion_generator import FORMAT_WEIGHTS, retention_problems  # noqa: E402

_COLD = "Your three nanometer chip has no three nanometer part inside."
_LOOP = "And the last step is the one most people skip."


def _retention_project(narrations, types=None):
    types = types or ["bigText", "counter", "textWithAccent", "list", "bigText", "codeBlock", "outro"]
    scenes = []
    for t, narr in zip(types, narrations):
        extra = {"value": 5} if t == "counter" else {"items": ["A one", "B two"]} if t == "list" else {"code": ["a = 1", "b = 2"]} if t == "codeBlock" else {}
        scenes.append(MotionSceneModel(type=t, text="Short line", narration=narr, durationInFrames=90, **extra))
    return MotionProject(topic="t", screen_title="Test", title="A test title #siliconverdict #tech", description="One. Two.", tags=["a"] * 6, pinned_comment="Why?", scenes=scenes)


def _narrs(**override):
    base = [_COLD, "Five of them stack up, and that changes the picture quite a lot.", _LOOP, "Each step adds a little more to the pile of evidence here.",
            "Together they explain why the number on the box is misleading.", "Here is the label broken down into its parts for you.", "Follow for more."]
    for k, v in override.items():
        base[int(k[1:])] = v
    return base


def test_retention_passes_a_cold_open_with_a_loop_and_breaks():
    assert retention_problems(_retention_project(_narrs())) == []


def test_retention_rejects_a_greeting_hook():
    assert any("cold open" in p for p in retention_problems(_retention_project(_narrs(n0="So today we look at why your chip name is misleading."))))


def test_retention_rejects_a_long_hook():
    long_hook = "Your chip is called three nanometer but nothing inside it measures three nanometers and that surprises almost every single person."
    assert any("words" in p for p in retention_problems(_retention_project(_narrs(n0=long_hook))))


def test_retention_needs_an_open_loop():
    assert any("open loop" in p for p in retention_problems(_retention_project(_narrs(n2="Each step adds a little more to the pile of evidence here."))))


def test_retention_rejects_three_headlines_in_a_row():
    types = ["bigText", "textWithAccent", "bigText", "list", "counter", "codeBlock", "outro"]
    assert any("headline" in p for p in retention_problems(_retention_project(_narrs(), types)))


def test_retention_is_off_by_default_and_on_when_asked():
    greeting = _retention_project(_narrs(n0="So today we look at why your chip name is misleading."))
    assert not any("cold open" in p for p in make_validator(None, None, None)(greeting))
    assert any("cold open" in p for p in make_validator(None, None, None, retention=True)(greeting))


def test_number_formats_are_weighted_above_the_stalled_ones():
    assert min(FORMAT_WEIGHTS[f] for f in ("whatif", "versus", "evolution", "fix", "decode")) > max(FORMAT_WEIGHTS[f] for f in ("myth", "tier"))
