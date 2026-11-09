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
    assert make_validator(None, None, "fix")(_project("fix", {2: "click", 4: "click", 7: "click"})) == []


def test_fix_format_needs_a_codeblock():
    types = [t if t != "codeBlock" else "textWithAccent" for t in _TYPES]
    types = ["bigText", "textWithAccent", "list", "textWithAccent", "list", "bigText", "textWithAccent", "list", "bigText", "textWithAccent", "list", "bigText", "outro"]
    problems = make_validator(None, None, "fix")(_project("fix", {2: "drag", 4: "drag"}, types))
    assert any("codeBlock" in p for p in problems)


def test_fix_format_needs_the_cursor_twice():
    problems = make_validator(None, None, "fix")(_project("fix", {2: "click"}))
    assert any("pointer" in p for p in problems)


def test_decode_format_needs_a_select_cursor():
    assert any("select" in p for p in make_validator(None, None, "decode")(_project("decode", {4: "drag"})))
    assert make_validator(None, None, "decode")(_project("decode", {0: "select", 4: "drag"})) == []


# ---- retention rules (content style study, Nov 2026) ----
from services.motion_generator import FORMAT_WEIGHTS, retention_problems  # noqa: E402

_COLD = "Your three nanometer chip has no three nanometer part inside."
_LOOP = "And the last step is the one most people skip."


def _retention_project(narrations, types=None, pinned="Team A or team B? Reply with one word."):
    types = types or ["bigText", "counter", "textWithAccent", "list", "bigText", "codeBlock", "outro"]
    scenes = []
    for t, narr in zip(types, narrations):
        extra = {"value": 5} if t == "counter" else {"items": ["A one", "B two"]} if t == "list" else {"code": ["a = 1", "b = 2"]} if t == "codeBlock" else {}
        scenes.append(MotionSceneModel(type=t, text="Short line", narration=narr, durationInFrames=90, **extra))
    return MotionProject(topic="t", screen_title="Test", title="A test title #siliconverdict #tech", description="One. Two.", tags=["a"] * 6, pinned_comment=pinned, scenes=scenes)


def _narrs(**override):
    base = [_COLD, "Five of them stack up, and that changes the picture quite a lot.", _LOOP, "Each step adds a little more to the pile of evidence here.",
            "Together they explain why the number on the box is misleading.", "Here is the label broken down into its parts for you.", "Is it team A or team B? Tell me below."]
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


def test_retention_needs_a_two_option_vote():
    open_question = _narrs(n6="What do you think about it? Tell me below.")
    assert any("two-option vote" in p for p in retention_problems(_retention_project(open_question)))
    assert any("pinned_comment" in p for p in retention_problems(_retention_project(_narrs(), pinned="What do you think?")))


# ---- numbered series, sound design, voice rotation ----
from types import SimpleNamespace  # noqa: E402

from services.motion_pipeline import RISER_TYPES, narrator_voice, sound_cues  # noqa: E402
from services.series import SERIES, apply_series, joined_hashtag, next_number  # noqa: E402


def _series_project(fmt="fix", title="Monitor Stuck at 60 Hz in Windows #siliconverdict #monitor #windows"):
    p = _retention_project(_narrs())
    p.format, p.title, p.tags = fmt, title, ["siliconverdict", "monitor"]
    return p


def test_series_prefixes_title_kicker_tags_and_description():
    p = _series_project()
    assert apply_series(p, number=7) == "Fix It Now #7"
    assert p.title == "Fix It Now #7: Monitor Stuck at 60 Hz in Windows #siliconverdict #monitor #windows"
    assert p.scenes[0].kicker == "fix it now #7" and "fixitnow" in p.tags and "Part of the Fix It Now series." in p.description


def test_series_is_idempotent_and_skips_formats_without_one():
    p = _series_project()
    apply_series(p, number=1)
    assert apply_series(p, number=2) is None and p.title.count("#1") == 1
    assert apply_series(_series_project(fmt="hardware2")) is None


def test_series_title_stays_within_the_limit():
    p = _series_project(title="A very long title that keeps going and going about a monitor and its refresh rate in Windows and beyond #siliconverdict #monitor #windows")
    apply_series(p, number=123)
    assert len(p.title) <= 100 and p.title.endswith("#siliconverdict #monitor #windows")


def test_series_number_counts_different_topics_of_the_format(tmp_db):
    from services.history import record_short_history
    assert next_number("fix") == 1
    for topic in ("a", "a", "b"):  # a repeated topic (re-rendered) is one video of the series
        record_short_history(0, "motion_graphics", "t", "none", topic=topic, title=topic, video_id="x", category="MOTION GRAPHICS FIX")
    record_short_history(0, "motion_graphics", "t", "none", topic="c", title="c", video_id="x", category="MOTION GRAPHICS DECODE")
    assert next_number("fix") == 3 and next_number("decode") == 2


def test_every_series_has_a_one_word_hashtag():
    for name, tag in SERIES.values():
        assert tag.isalnum() and tag == tag.lower() and name


def test_hashtags_are_joined_words():
    assert joined_hashtag("tech explained") == "#techexplained" and joined_hashtag("#3D V-Cache") == "#3DVCache"


def test_sound_cues_hit_first_riser_before_reveals_hit_on_flash():
    kinds = ["bigText", "textWithAccent", "counter", "list", "flash", "versus", "outro"]
    starts = [0, 100, 200, 300, 400, 500, 600]
    cues = sound_cues(starts, kinds)
    assert ("sfx_hit.wav", 0.05, "first") in cues
    assert ("sfx_riser.wav", 200 / 30 - 0.95, "riser") in cues and ("sfx_hit.wav", 400 / 30, "flash") in cues
    assert sound_cues(starts, None) == []


def test_sound_cues_cap_the_risers():
    kinds = ["bigText"] + ["verdict"] * 9 + ["outro"]
    cues = sound_cues([i * 100 for i in range(len(kinds))], kinds)
    assert sum(1 for c in cues if c[2] == "riser") == 4 and "verdict" in RISER_TYPES


def test_narrator_rotates_by_format_and_can_be_turned_off(monkeypatch):
    from config.settings import settings
    daniel, adam, liam = settings.ELEVENLABS_VOICE_1, settings.ELEVENLABS_VOICE_2, settings.ELEVENLABS_VOICE_3
    voice = lambda fmt, kind="curiosity": narrator_voice(SimpleNamespace(format=fmt, kind=kind))  # noqa: E731
    monkeypatch.setattr(settings, "MOTION_VOICE_ROTATION", True)
    assert (voice("decode"), voice(None), voice("versus"), voice("myth"), voice("fix"), voice("whatif")) == (daniel, daniel, adam, adam, liam, liam)
    assert voice("decode", "game") == liam
    monkeypatch.setattr(settings, "MOTION_VOICE_ROTATION", False)
    assert voice("decode") == liam


# ---- the pointer only does things that mean something ----
from services.motion_generator import CURSOR_ACTIONS, assign_cursors, sanitize_cursors  # noqa: E402
from services.motion_pipeline import cursor_cues  # noqa: E402


def _scenes(types, cursors):
    out = []
    for i, t in enumerate(types):
        out.append(MotionSceneModel(type=t, text="Short line", accentText="Key word", narration=_NARR, durationInFrames=90, cursor=cursors.get(i),
                                    **({"items": ["A one", "B two"]} if t == "list" else {"code": ["a = 1", "b = 2"]} if t == "codeBlock" else {"value": 5} if t == "counter" else {})))
    return out


def test_old_actions_are_gone():
    assert set(CURSOR_ACTIONS) == {"click", "select", "drag", "toggle"}


def test_tab_hover_busy_and_idle_are_dropped():
    sc = _scenes(["bigText", "textWithAccent", "counter", "list", "bigText", "textWithAccent"], {0: "tab", 1: "hover", 2: "busy", 3: "idle"})
    sanitize_cursors(sc, None)
    assert [x.cursor for x in sc] == [None] * 6


def test_actions_only_stay_where_they_mean_something():
    sc = _scenes(["bigText", "list", "counter", "progressBar", "textWithAccent", "codeBlock", "tier"], {0: "select", 1: "drag", 2: "click", 3: "drag", 4: "click", 5: "click"})
    sanitize_cursors(sc, None)
    assert sc[0].cursor == "select"  # a headline's phrase can be selected
    assert sc[1].cursor is None  # nothing to pull in a list
    assert sc[2].cursor is None  # clicking a number means nothing
    assert sc[3].cursor == "drag"  # the bar's knob
    assert sc[4].cursor is None or sc[4].cursor == "select"  # a click on a headline becomes a selection (when the spacing allows it)
    assert sc[5].cursor == "click"  # the setting in a code panel


def test_pointer_scenes_keep_their_distance_and_budget():
    sc = _scenes(["bigText"] * 1 + ["progressBar", "textWithAccent", "progressBar", "textWithAccent", "progressBar", "textWithAccent", "progressBar"], {i: "drag" if i % 2 else "select" for i in range(8)})
    sanitize_cursors(sc, None)
    idx = [i for i, x in enumerate(sc) if x.cursor]
    assert len(idx) <= 3 and all(b - a >= 2 for a, b in zip(idx, idx[1:]))


def test_a_toggle_is_only_for_the_first_scene():
    sc = _scenes(["bigText", "textWithAccent"], {0: "toggle", 1: "toggle"})
    sanitize_cursors(sc, None)
    assert sc[0].cursor == "toggle" and sc[0].toggle == "airplane" and sc[1].cursor is None


def test_assign_gives_decode_its_select_and_fix_its_clicks():
    types = ["bigText", "textWithAccent", "codeBlock", "textWithAccent", "list", "bigText", "outro"]
    sc = _scenes(types, {})
    assign_cursors(sc, "decode")
    assert sc[0].cursor == "select" and "click" in [x.cursor for x in sc]
    sc = _scenes(types, {})
    assign_cursors(sc, "fix")
    assert [x.cursor for x in sc].count("click") == 2


def test_assign_carries_tier_chips_and_pulls_bars():
    sc = _scenes(["bigText", "tier", "tier", "tier", "tier", "textWithAccent", "outro"], {})
    assign_cursors(sc, "tier")
    assert {x.cursor for x in sc if x.cursor} == {"drag"}
    sc = _scenes(["bigText", "textWithAccent", "progressBar", "list", "outro"], {})
    assign_cursors(sc, None)
    assert sc[2].cursor == "drag"


def test_select_cue_is_the_moment_the_key_word_is_spoken():
    sc = _scenes(["bigText", "textWithAccent"], {1: "select"})
    sc[1].accentText = "Key word"
    project = SimpleNamespace(scenes=sc)
    words = [{"word": w, "start": 1.0 + i * 0.4, "end": 1.3 + i * 0.4} for i, w in enumerate("Your first line".split())] \
        + [{"word": w, "start": 3.0 + i * 0.4, "end": 3.3 + i * 0.4} for i, w in enumerate("This is the key word here".split())]
    cursor_cues(project, words, [3, 6], [0.0, 2.8])
    assert sc[1].cursorCue == round(3.0 + 3 * 0.4 - 2.8, 2)  # "key" is the 4th word of the second scene
    assert sc[0].cursorCue is None


# ---- ui presets: 20 drawn interfaces the pointer uses ----
import json  # noqa: E402
from pathlib import Path  # noqa: E402

from services.motion_generator import MAX_UI_SCENES, UI_FORMATS_OFF, UI_PRESETS, _ui_problems, ui_rules  # noqa: E402

SAMPLE_UI = Path(__file__).resolve().parent.parent / "remotion_studio" / "src" / "motion" / "sample_ui.json"


def _ui(preset, **kw):
    base = dict(type="ui", preset=preset, text="Short headline", narration=_NARR, durationInFrames=150)
    base.update(kw)
    return MotionSceneModel(**base)


def _bare(*scenes):
    return SimpleNamespace(scenes=list(scenes))


def test_there_are_twenty_presets_and_the_prompt_lists_them_all():
    assert len(UI_PRESETS) == 20
    rules = ui_rules()
    assert all(name in rules for name in UI_PRESETS) and all(spec["action"] in ("select", "drag", "click") for spec in UI_PRESETS.values())


def test_the_sample_has_one_valid_scene_per_preset():
    scenes = [MotionSceneModel(**x) for x in json.loads(SAMPLE_UI.read_text(encoding="utf-8"))["scenes"]]
    assert {s.preset for s in scenes} == set(UI_PRESETS)
    for s in scenes:
        problems = [p for p in _ui_problems(_bare(s), None) if "mentioned in that scene" not in p]  # the sample's narration is a placeholder
        assert problems == [], (s.preset, problems)


def test_ui_scene_checks():
    ok = _ui("display", items=["60 Hz", "144 Hz"], value=2)
    assert _ui_problems(_bare(ok), None) == []
    assert any("preset" in p for p in _ui_problems(_bare(_ui("nope")), None))
    assert any("value" in p for p in _ui_problems(_bare(_ui("display", items=["60 Hz", "144 Hz"], value=5)), None))
    assert any("accentText" in p for p in _ui_problems(_bare(_ui("bios", items=["A|1", "B|2", "C|3"], value=1)), None))
    assert any("two different slots" in p for p in _ui_problems(_bare(_ui("dimm", items=["A1", "A2", "B1", "B2"], leftValue=2, rightValue=2)), None))
    assert any("add up to 100" in p for p in _ui_problems(_bare(_ui("diskbar", items=["Games|50", "Apps|20", "Free|10"], value=30, leftValue=1, rightValue=2)), None))
    assert any("unit" in p for p in _ui_problems(_bare(_ui("partpicker", items=["Board|B650", "CPU|empty"], value=2, accentText="Chip", leftValue=0)), None))


def test_ui_scenes_are_limited_and_spaced():
    d = _ui("display", items=["60 Hz", "144 Hz"], value=2)
    assert any("at most" in p for p in _ui_problems(_bare(d, d, d), None))
    assert any("between them" in p for p in _ui_problems(_bare(d, d), None))
    assert any("no ui scenes" in p for p in _ui_problems(_bare(d), "tier")) and "tier" in UI_FORMATS_OFF and MAX_UI_SCENES == 2


def test_the_preset_decides_the_pointer_action():
    sc = [_ui("display", items=["60 Hz", "144 Hz"], value=2, cursor="hover"), _ui("nope", cursor="click")]
    sanitize_cursors(sc, None)
    assert sc[0].cursor == "click" and sc[1].cursor is None
    sc = [_ui("gamemenu", items=["Shadows|90>40", "Textures|80>80"], value=1, leftValue=60, rightValue=90, cursor="click")]
    sanitize_cursors(sc, None)
    assert sc[0].cursor == "drag"


# ---- more music and effects ----
from services.motion_pipeline import MUSIC_BY_FORMAT, WHOOSHES, music_bed, pointer_moment, scene_audio_info  # noqa: E402

AUDIO = Path(__file__).resolve().parent.parent / "assets" / "audio"


def test_every_music_bed_and_effect_exists():
    beds = {f for opts in MUSIC_BY_FORMAT.values() for f in opts}
    assert len(beds) >= 7 and all((AUDIO / f).is_file() for f in beds)
    assert all((AUDIO / f).is_file() for f in WHOOSHES)
    for cue in ("sfx_click", "sfx_pop", "sfx_tick", "sfx_swish", "sfx_chime", "sfx_error", "sfx_ding", "sfx_boom", "sfx_glitch", "sfx_type", "sfx_sparkle"):
        assert (AUDIO / f"{cue}.wav").is_file(), cue


def test_music_depends_on_the_format_and_is_stable_per_topic():
    assert music_bed("fix", "A topic") == music_bed("fix", "A topic")
    assert music_bed("fix", "x") in MUSIC_BY_FORMAT["fix"] and music_bed("whatif", "x") in MUSIC_BY_FORMAT["whatif"]
    assert {music_bed("fix", f"topic {i}") for i in range(12)} == set(MUSIC_BY_FORMAT["fix"])  # both beds get used
    assert music_bed("unknown", "x") in MUSIC_BY_FORMAT[None]


def test_the_pointer_sounds_follow_what_it_does():
    kinds = ["bigText", "textWithAccent", "ui", "verdict", "counter", "outro"]
    starts = [0, 100, 200, 400, 500, 700]
    info = [{"cursor": None, "dur": 100}, {"cursor": "select", "dur": 100, "cue": None}, {"cursor": "click", "dur": 200, "cue": 2.0}, {"cursor": None, "dur": 100, "verdict": "myth"},
            {"cursor": None, "dur": 200}, {"cursor": None, "dur": 100}]
    cues = sound_cues(starts, kinds, info)
    names = [c[0] for c in cues]
    assert "sfx_swish.wav" in names and "sfx_click.wav" in names and "sfx_error.wav" in names and names.count("sfx_tick.wav") == 5 and "sfx_chime.wav" in names
    click = next(c for c in cues if c[0] == "sfx_click.wav")
    assert click[1] == 200 / 30 + pointer_moment("ui", "click", 200, 2.0) and pointer_moment("ui", "click", 200, 2.0) == (60 - 2) / 30
    assert sound_cues(starts, kinds)[0] == ("sfx_hit.wav", 0.05, "first") and len(sound_cues(starts, kinds)) < len(cues)


def test_the_mix_has_music_effects_and_voice_without_clipping(tmp_path):
    import subprocess

    from services.motion_pipeline import add_sound
    from services.voice import get_ffmpeg_bin

    ff = get_ffmpeg_bin()
    raw = tmp_path / "raw.mp4"
    subprocess.run([ff, "-y", "-f", "lavfi", "-i", "color=c=black:s=320x568:d=6:r=30", "-pix_fmt", "yuv420p", str(raw)], check=True, capture_output=True)
    voice = tmp_path / "v.mp3"
    subprocess.run([ff, "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=2", str(voice)], check=True, capture_output=True)
    sc = [SimpleNamespace(cursor=c, durationInFrames=90, cursorCue=None, verdict=v) for c, v in ((None, None), ("select", None))]
    out = add_sound(raw, tmp_path / "out.mp4", [0, 90], [(0, voice, 2.0)], lead=0.0, kinds=["bigText", "textWithAccent"], music_file="bed_chill.mp3", info=scene_audio_info(sc))
    log = subprocess.run([ff, "-hide_banner", "-i", str(out), "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    assert "Audio:" in log and float(log.split("max_volume:")[1].split("dB")[0]) < -0.5


# ---- looks, captions and cues (video audit, Nov 2026) ----
import re  # noqa: E402

from services.looks import AFFINITY, AVOID_LAST, LOOKS, choose_look  # noqa: E402
from services.motion_pipeline import build_captions, synthetic_captions  # noqa: E402

LOOKS_TS = Path(__file__).resolve().parent.parent / "remotion_studio" / "src" / "motion" / "looks.ts"


def test_python_and_remotion_agree_on_the_looks():
    ts_names = re.findall(r"^  (\w+): \{ name: '(\w+)'", LOOKS_TS.read_text(encoding="utf-8"), re.M)
    assert {k for k, _ in ts_names} == set(LOOKS) and all(k == n for k, n in ts_names)


def test_every_format_has_valid_affinities():
    assert all(set(v) <= set(LOOKS) for v in AFFINITY.values()) and len(LOOKS) == 8


def test_a_look_is_not_reused_within_the_last_videos():
    seen = []
    for i in range(24):
        look = choose_look("fix", f"topic {i}", recent=seen)
        assert look not in seen[:AVOID_LAST]
        seen.insert(0, look)
    assert len(set(seen)) >= 4  # real variety across many videos of the same format


def test_the_same_topic_gets_the_same_look_and_formats_follow_their_affinity():
    assert choose_look("decode", "RTX", recent=[]) == choose_look("decode", "RTX", recent=[])
    assert all(choose_look("decode", f"t{i}", recent=[]) in AFFINITY["decode"] for i in range(10))


def _voiced(texts):
    sc = [MotionSceneModel(type="textWithAccent", text="Short line", accentText="key phrase", narration=t, durationInFrames=90) for t in texts]
    return sc


def test_captions_follow_the_voice_timing_and_the_accent_cue_is_set():
    sc = _voiced(["The key phrase matters here.", "Then it ends."])
    project = SimpleNamespace(scenes=sc, captions=None)
    words, t = [], 0.0
    for s_ in sc:
        for _ in s_.narration.split():
            words.append({"word": "x", "start": t, "end": t + 0.3})
            t += 0.35
    counts = [len(s_.narration.split()) for s_ in sc]
    cuts = [0.0, counts[0] * 0.35 + 0.2, t + 0.2]
    build_captions(project, words, [s_.narration for s_ in sc], counts, cuts)
    caps = project.captions
    assert [c.w for c in caps[:3]] == ["The", "key", "phrase"] and all(b.s >= a.s for a, b in zip(caps, caps[1:]))
    assert caps[len(caps) - 1].s >= 90  # the second scene starts at frame 90
    assert sc[0].accentCue == round(0.35 - 0.0, 2)  # "key" is the second word, said 0.35 s in


def test_synthetic_captions_for_previews_cover_every_word():
    sc = _voiced(["One two three four five.", "Six seven."])
    project = SimpleNamespace(scenes=sc, captions=None)
    synthetic_captions(project)
    assert len(project.captions) == 7 and sc[0].accentCue is None  # "key" is not in the line, so no cue


def test_to_props_carries_the_look_and_captions():
    p = _retention_project(_narrs())
    p.look = "cobalt"
    synthetic_captions(p)
    props = p.to_props()
    assert props["look"] == "cobalt" and props["captions"] and {"w", "s", "e"} <= set(props["captions"][0])
    p.look, p.captions = None, None
    assert "look" not in p.to_props() and "captions" not in p.to_props()


def test_scenes_must_stay_short_enough_to_keep_the_screen_moving():
    long_line = "This is a very long line that keeps going and going so the screen would sit still for far too long indeed."
    assert any("split it across two scenes" in x for x in retention_problems(_retention_project(_narrs(n1=long_line))))


def test_every_look_is_blue():
    import colorsys

    ts = LOOKS_TS.read_text(encoding="utf-8")
    for name in LOOKS:
        row = re.search(rf"^  {name}: \{{ name: '{name}', accent: '(#\w+)', accent2: '(#\w+)', background: '(#\w+)'", ts, re.M)
        assert row, name
        for hex_ in row.groups():
            r, g, b = (int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5))
            h, sat, val = colorsys.rgb_to_hsv(r, g, b)
            # the blue family: hue between cyan (170 deg) and indigo (255 deg), or a near-neutral blue-tinted white / black
            assert (170 / 360 <= h <= 255 / 360) or sat < 0.2 or val < 0.1, (name, hex_, round(h * 360), round(sat, 2), round(val, 2))


# ---- callouts, the re-hook and the 60-second floor (audit follow-up) ----
from services.motion_pipeline import MIN_VIDEO_SECONDS, pick_callout, rehook_index  # noqa: E402


def test_callouts_pick_figures_acronyms_and_skip_plain_words():
    assert pick_callout("And the first two digits name the generation, so fifty is newer than forty on 144 Hz panels".split())[0] == "144 Hz"
    assert pick_callout("Inside it a small circuit talks to the RTX card over the bus every single time".split())[0] == "RTX"
    assert pick_callout("it simply keeps going and going without ever stopping for anyone at all today".split()) is None


def test_the_rehook_scene_is_near_the_middle_and_short_videos_have_none():
    starts = [i * 100 for i in range(12)]
    assert rehook_index(starts, [100] * 12) == 6
    assert rehook_index([0, 100, 200, 300], [100] * 4) == -1
    assert 2 <= rehook_index(starts, [100] * 12) <= 9


def test_sound_gets_a_boom_at_the_rehook_scene():
    kinds = ["bigText"] * 12
    starts = [i * 100 for i in range(12)]
    info = [{"cursor": None, "dur": 100} for _ in range(12)]
    cues = sound_cues(starts, kinds, info)
    assert ("sfx_boom.wav", 600 / 30, "rehook") in cues


def test_scenes_of_17_words_still_reach_the_monetisation_floor():
    # 13 scenes x 12-17 words keeps the narration between 150 and 190 words: more than 60 seconds at the natural pace
    words = 13 * 14
    assert 150 <= words <= 190 and words / 2.5 + 13 * 0.3 > MIN_VIDEO_SECONDS - 1


def test_the_functional_colours_are_blue_too():
    ts = (Path(__file__).resolve().parent.parent / "remotion_studio" / "src" / "motion")
    tier = re.search(r"TIER_COLORS[^=]*= (\{[^}]*\})", (ts / "formats.tsx").read_text(encoding="utf-8")).group(1)
    for hex_ in re.findall(r"#[0-9A-Fa-f]{6}", tier) + re.findall(r"(?:myth|fact|partly): \{ label: '[A-Z ]+', color: '(#\w+)'", (ts / "formats.tsx").read_text(encoding="utf-8")):
        r, g, b = (int(hex_[i:i + 2], 16) for i in (1, 3, 5))
        assert b >= max(r, g) - 8 or (g >= r and b >= r), hex_  # blue-dominant: no red, yellow, orange or green


def test_a_busy_mix_is_brought_under_the_peak_limit(tmp_path):
    import subprocess

    from services.motion_pipeline import PEAK_CEILING_DB, _peak_db, add_sound
    from services.voice import get_ffmpeg_bin

    ff = get_ffmpeg_bin()
    raw = tmp_path / "raw.mp4"
    subprocess.run([ff, "-y", "-f", "lavfi", "-i", "color=c=black:s=320x568:d=14:r=30", "-pix_fmt", "yuv420p", str(raw)], check=True, capture_output=True)
    n = 12
    starts = [i * 35 for i in range(n)]  # a cue on almost every beat: the loudest case
    kinds = ["verdict", "counter", "flash", "versus", "counter", "verdict", "ui", "counter", "flash", "versus", "verdict", "outro"]
    info = [{"cursor": "click" if k == "ui" else None, "dur": 35, "cue": None, "verdict": "myth", "callout_at": 0.2} for k in kinds]
    out = add_sound(raw, tmp_path / "out.mp4", starts, None, kinds=kinds, music_file="bed_drive.mp3", info=info)  # unvoiced: effects at their loudest
    assert _peak_db(out) <= PEAK_CEILING_DB + 0.3


# ---- YouTube Analytics client ----
def test_analytics_refuses_a_token_without_the_scopes_and_says_how_to_get_them(tmp_path, monkeypatch):
    import json

    from config.settings import settings
    from services import yt_analytics as ya

    token = tmp_path / "token.json"
    token.write_text(json.dumps({"token": "x", "refresh_token": "y", "client_id": "c", "client_secret": "s", "token_uri": "https://oauth2.googleapis.com/token", "scopes": ["https://www.googleapis.com/auth/youtube.upload"]}))
    monkeypatch.setattr(settings, "YOUTUBE_TOKEN_PATH", str(token))
    try:
        ya._creds()
        raise AssertionError("a token with only the upload scope must be refused")
    except ya.AnalyticsUnavailable as exc:
        assert "yt-analytics.readonly" in str(exc) and "authenticate_yt.py" in str(exc)


def test_retention_reads_the_curve_at_a_point_of_the_video():
    from services.yt_analytics import retention_at

    curve = [1.0 - i / 100 for i in range(101)]
    assert retention_at(curve, 0.2) == curve[20] and retention_at(curve, 0.8) == curve[80] and retention_at([], 0.5) is None
