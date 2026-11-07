#!/usr/bin/env python3
"""Builds + validates hand-written script banks.

Source files (compact JSON Lines, one script per line): docs/generated_scripts/bank/src/<type>.jsonl
  types: classic, myth, tier, whatif, evolution, versus, fix, decode  -> Motion Graphics (MotionProject, validated with services.motion_generator.make_validator)
         minecraft                                        -> McStory (validated with services.mc_story_generator._problems)
Output: docs/generated_scripts/bank/<type>/<type>_NNN.json  (exactly what scripts/render_motion_json.py takes for Motion types)

Usage: python scripts/build_script_bank.py [type ...]      (no args = every type found in src/)
Compact formats are documented at the top of each helper below.
"""
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
SRC = BASE / "docs/generated_scripts/bank/src"
OUT = BASE / "docs/generated_scripts/bank"

from services.motion_generator import MotionProject, estimated_seconds, make_validator  # noqa: E402

KICKER = {"tier": "tier list", "verdict": "myth or fact", "timeline": "evolution"}


def sc(type_, text, accent=None, narr="", **kw):
    d = {"type": type_, "text": text, "narration": narr, "durationInFrames": kw.pop("dur", 90)}
    if accent:
        d["accentText"] = accent
    d.update({k: v for k, v in kw.items() if v is not None})
    return d


def expand_scene(row):
    """row = [type, text, accent, narration, {extras}]  (extras: value, unit, items, code, icons, kicker, light, ...)"""
    t, text, acc, narr = row[0], row[1], row[2] or None, row[3]
    extra = row[4] if len(row) > 4 else {}
    return sc(t, text, acc, narr, **extra)


def build_general(s):
    return [expand_scene(r) for r in s["s"]]


def build_tier(s):
    """{"cat","crit","hook":[text,acc,narr],"items":[[L,label,narr],...],"take":[text,acc,narr],"out":[narr]}"""
    scenes = [sc("bigText", s["hook"][0], s["hook"][1], s["hook"][2], kicker="tier list")]
    board = []
    for letter, label, narr in s["items"]:
        board = board + [f"{letter}|{label}"]
        scenes.append(sc("tier", s["cat"], s["crit"], narr, kicker="tier list", items=list(board), dur=100))
    scenes.append(sc("textWithAccent", s["take"][0], s["take"][1], s["take"][2]))
    scenes.append(sc("outro", "STAY CURIOUS", "Follow for more", s["out"][0]))
    return scenes


def build_versus(s):
    """{"left","right","hook":[text,acc,narr],"rounds":[[metric,tag,unit,lv,rv,winner|None,narr],...],"take":[text,acc,narr],"out":[narr]}"""
    scenes = [sc("textWithAccent", s["hook"][0], s["hook"][1], s["hook"][2])]
    for i, (metric, tag, unit, lv, rv, win, narr) in enumerate(s["rounds"], 1):
        scenes.append(sc("versus", metric, tag, narr, kicker=f"round {i}", left=s["left"], right=s["right"], leftValue=lv, rightValue=rv, unit=unit, winner=win, dur=110))
        if i == 1 and s.get("mid") and len(s["rounds"]) > 3:
            pass
    for extra in s.get("between", []):  # optional extra scenes after the last round: rows
        scenes.append(expand_scene(extra))
    scenes.append(sc("textWithAccent", s["take"][0], s["take"][1], s["take"][2]))
    scenes.append(sc("outro", "STAY CURIOUS", "Follow for more", s["out"][0]))
    return scenes


def build_myth(s):
    """{"hook":[text,acc,narr],"claims":[[claim,verdict,truth,narr,support_row],...],"take":[text,acc,narr],"out":[narr]}  support_row = general scene row"""
    scenes = [sc("textWithAccent", s["hook"][0], s["hook"][1], s["hook"][2])]
    for claim, verdict, truth, narr, support in s["claims"]:
        scenes.append(sc("verdict", claim, truth, narr, kicker="myth or fact", verdict=verdict, dur=100))
        if support:
            scenes.append(expand_scene(support))
    scenes.append(sc("textWithAccent", s["take"][0], s["take"][1], s["take"][2]))
    scenes.append(sc("outro", "STAY CURIOUS", "Follow for more", s["out"][0]))
    return scenes


BUILDERS = {"classic": build_general, "whatif": build_general, "evolution": build_general, "tier": build_tier, "versus": build_versus, "myth": build_myth, "fix": build_general, "decode": build_general}
FORMAT_OF = {"classic": None, "whatif": "whatif", "evolution": "evolution", "tier": "tier", "versus": "versus", "myth": "myth", "fix": "fix", "decode": "decode"}


def build_motion(kind, s):
    scenes = BUILDERS[kind](s)
    if kind == "whatif":
        scenes[0].setdefault("kicker", "what if")
    if kind in ("fix", "decode"):
        scenes[0].setdefault("kicker", "fix it now" if kind == "fix" else "decoded")
    for x in scenes:
        if x["type"] == "timeline":
            x.setdefault("kicker", "evolution")
    proj = MotionProject(topic=s["topic"], screen_title=s["st"], title=s["title"], description=s["desc"], tags=s["tags"], pinned_comment=s["pc"],
                         scenes=[__import__("services.motion_generator", fromlist=["MotionSceneModel"]).MotionSceneModel(**x) for x in scenes],
                         format=FORMAT_OF[kind], kind="curiosity", fact_checked=False)
    problems = make_validator(None, None, FORMAT_OF[kind])(proj)
    cap = 26 if kind in ('tier', 'versus') else 20
    problems += [f'scene {i}: narration has {len(x.narration.split())} words (max {cap})' for i, x in enumerate(proj.scenes, 1) if len(x.narration.split()) > cap]
    if not 1 <= len(re.findall(r"#\w+", proj.title)) <= 4 or "#siliconverdict" not in proj.title.lower():
        problems.append("title needs #siliconverdict plus 1-3 hashtags")
    if len(proj.screen_title) > 24:
        problems.append("screen_title over 24 characters")
    return proj, problems


def expand_mc(s):
    """Compact Minecraft source -> McStory dict.
    {"topic","id","screen","cta","title","desc","tags","pc","time","stations":[...],"cast":[...],"inv":{...},
     "beats":[[text, hl|null, [[act, target|null, {extra}], ...], {beat extras: shot, focus, stock, tag, stall, seconds}], ...]}"""
    beats = []
    for b in s["beats"]:
        text, hl, acts = b[0], b[1], b[2]
        extra = b[3] if len(b) > 3 else {}
        actions = []
        for a in acts:
            d = {"act": a[0]}
            if len(a) > 1 and a[1]:
                d["target"] = a[1]
            if len(a) > 2:
                d.update(a[2])
            actions.append(d)
        beat = {"text": text, "actions": actions}
        if hl:
            beat["hl"] = hl
        beat.update(extra)
        beats.append(beat)
    out = {"topic": s["topic"], "category_name": "MINECRAFT EXPLAINER", "header_banner": s["screen"], "title": s["title"], "description": s["desc"],
           "tags": s["tags"], "pinned_comment": s["pc"], "script_id": s["id"], "screen_title": s["screen"], "cta": s["cta"], "seconds": 64.0,
           "time": s.get("time", "day"), "stations": s["stations"], "cast": s.get("cast", []), "beats": beats}
    if s.get("inv"):
        out["inventory"] = s["inv"]
    return out


def build_minecraft(s):
    from core.schemas import McStory
    import services.mc_story_generator as g
    story = McStory.model_validate(expand_mc(s) if isinstance(s["beats"][0], list) else s)
    from services.mc_director import compile_script
    for attempt in range(1, 6):  # beats whose walk is too long for their subtitle get a minimum on-screen time until the director stops warning
        rep = compile_script(story.to_script())
        if not any("top speed" in w for w in rep["warnings"]):
            break
        for st_ in story.stations:  # bring the stations closer first: long walks squeezed into one subtitle look like x2 playback
            if st_.type != "sign":
                st_.gap = max(3.0, (st_.gap if st_.gap is not None else 8.0) - 2.0)
        for b in story.beats:
            if any(a.act in ("go", "fetch", "sprint", "search") for a in b.actions):
                b.seconds = max(b.seconds or 0, 2.8 + 0.6 * attempt)
    problems = g._problems(story)
    return story, problems


def import_bank():
    """Adds every built script in bank/<type>/ to the story bank in data/history.db (skips topics already there)."""
    import glob
    from services.motion_generator import MotionProject
    from core.schemas import McStory
    from services.story_bank import add_story, count_ready, topics_in_bank
    added = 0
    for kind in ("classic", "myth", "tier", "versus", "whatif", "evolution", "fix", "decode", "minecraft"):
        series = "minecraft" if kind == "minecraft" else "motion"
        have = {t.strip().lower() for t in topics_in_bank(series)}
        n = 0
        for f in sorted(glob.glob(str(OUT / kind / "*.json"))):
            data = json.loads(Path(f).read_text(encoding="utf-8"))
            data.pop("name", None)
            data.pop("estimated_seconds", None)
            obj = (McStory if series == "minecraft" else MotionProject).model_validate(data)
            if obj.topic.strip().lower() in have:
                continue
            add_story(series, obj, model="handwritten")
            have.add(obj.topic.strip().lower())
            n += 1
        print(f"{kind}: {n} added to the '{series}' bank")
        added += n
    print(f"added {added}; ready now: minecraft={count_ready('minecraft')} motion={count_ready('motion')}")


def main():
    if "--import-bank" in sys.argv:
        return import_bank()
    kinds = sys.argv[1:] or sorted({p.stem.split("_")[0] for p in SRC.glob("*.jsonl")})
    total_bad = 0
    topics = {}
    for kind in kinds:
        parts = sorted(SRC.glob(f"{kind}_*.jsonl")) + sorted(SRC.glob(f"{kind}.jsonl"))
        if not parts:
            continue
        outdir = OUT / kind
        outdir.mkdir(parents=True, exist_ok=True)
        for old in outdir.glob("*.json"):
            old.unlink()
        ok = 0
        for n, line in enumerate([ln for f in parts for ln in f.read_text(encoding="utf-8").splitlines()], 1):
            if not line.strip() or line.startswith("#"):
                continue
            try:
                s = json.loads(line)
            except Exception as exc:
                print(f"[{kind} line {n}] BAD JSON: {exc}")
                total_bad += 1
                continue
            try:
                obj, problems = build_minecraft(s) if kind == "minecraft" else build_motion(kind, s)
            except Exception as exc:
                print(f"[{kind} #{n}] {s.get('topic')}: BUILD ERROR {str(exc)[:300]}")
                total_bad += 1
                continue
            key = s["topic"].strip().lower()
            if key in topics:
                problems.append(f"duplicate topic of {topics[key]}")
            topics[key] = f"{kind} #{n}"
            if problems:
                print(f"[{kind} #{n}] {s['topic']}:")
                for p in problems:
                    print("    -", p)
                total_bad += 1
                continue
            name = f"{kind}_{ok + 1:03d}"
            data = obj.model_dump(exclude_none=True) if kind != "minecraft" else obj.model_dump()
            data["name"] = name
            if kind != "minecraft":
                data["estimated_seconds"] = round(estimated_seconds(obj))
            (outdir / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            ok += 1
        print(f"{kind}: {ok} valid scripts written to {outdir.relative_to(BASE)}")
    print("TOTAL INVALID:", total_bad)


if __name__ == "__main__":
    main()
