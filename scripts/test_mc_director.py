#!/usr/bin/env python3
"""Checks the Minecraft director with a synthetic script and a set of edge cases (no rendering, no Gemini).
   python scripts/test_mc_director.py
"""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.mc_director import compile_script  # noqa: E402

# Synthetic test script: exercises the director only (no topic; real videos always use a new Gemini script).
base = {
    "id": "director-test", "title": "DIRECTOR TEST", "cta": "TEST", "seconds": 64,
    "stations": [
        {"id": "mine", "type": "mine", "label": ["STATION A"], "gap": 6},
        {"id": "chest", "type": "chest", "label": ["STATION B"], "gap": 8},
        {"id": "pen", "type": "pen", "kinds": ["villager", "pig", "cow"], "gap": 8},
    ],
    "beats": [
        {"text": "Test beat one, a hook question?", "hl": "hook", "shot": "sign", "focus": "mine", "seconds": 3},
        {"text": "Waving at the camera", "actions": [{"act": "wave", "seconds": 2}]},
        {"text": "Mining the vein", "actions": [{"act": "mine", "target": "mine"}]},
        {"text": "Standing still for a while", "seconds": 3},
        {"text": "Walking to the chest", "shot": "pan", "actions": [{"act": "go", "target": "chest"}]},
        {"text": "Opening the chest", "actions": [{"act": "open_chest", "target": "chest"}]},
        {"text": "Back to the vein", "actions": [{"act": "go", "target": "mine"}]},
        {"text": "Mining again, faster", "actions": [{"act": "mine", "target": "mine", "fast": True}]},
        {"text": "Visiting the mobs", "actions": [{"act": "go", "target": "pen"}, {"act": "look", "target": "pen"}]},
        {"text": "Back to the chest", "actions": [{"act": "go", "target": "chest"}]},
        {"text": "And back to the vein", "actions": [{"act": "go", "target": "mine"}]},
        {"text": "Jump and wave", "actions": [{"act": "jump"}, {"act": "wave", "seconds": 2}]},
        {"text": "One more trip", "actions": [{"act": "go", "target": "chest"}]},
        {"text": "The end", "actions": [{"act": "go", "target": "mine"}]},
    ],
    "inventory": {"grow_at_beat": 11},
}
fails = 0


def check(name, script, expect_ok, needle=None):
    global fails
    r = compile_script(script)
    msgs = r["errors"] + r["warnings"]
    ok = r["ok"] == expect_ok and (needle is None or any(needle in m for m in msgs))
    fails += 0 if ok else 1
    print(("PASS " if ok else "FAIL ") + name + f" ({r['seconds']:.1f}s, {len(msgs)} msg)")
    if not ok:
        print("   ", msgs)


check("base script compiles", base, True)
assert compile_script(base)["seconds"] >= 61, "a 64 s script must be at least 61 s (TikTok monetisation)"

s = copy.deepcopy(base); s["beats"][2]["actions"][0]["target"] = "nope"
check("unknown station rejected", s, False, "unknown station")

s = copy.deepcopy(base); s["stations"].append({"id": "lago", "type": "pond"}); s["stations"].append({"id": "puerta", "type": "door"}); s["stations"].append({"id": "escalera", "type": "ladder"})
s["beats"] += [{"text": "Nadar", "actions": [{"act": "swim", "target": "lago"}]}, {"text": "Puerta", "actions": [{"act": "open_door", "target": "puerta"}]}, {"text": "Escalera", "actions": [{"act": "climb", "target": "escalera"}]}]
s["seconds"] = 70
check("swim + door + ladder compile", s, True)

s = copy.deepcopy(base); s["stations"].append({"id": "corral", "type": "pen", "kinds": ["pig", "cow", "villager"]})
s["beats"].append({"text": "Los mobs", "actions": [{"act": "attack", "target": "corral", "seconds": 1.5}]}); s["seconds"] = 70
check("pen + attack compile", s, True)

s = copy.deepcopy(base); s["stations"][0]["type"] = "dragon"
check("unknown station type rejected", s, False, "unknown type")

s = copy.deepcopy(base); s["stations"].append({"id": "corral", "type": "pen", "kinds": ["pig", "cow", "sheep", "chicken"]})
s["cast"] = [{"id": "alex", "kind": "villager", "at": "mine"}]
s["beats"].append({"text": "Busy pen", "actions": [{"act": "attack", "target": "corral", "seconds": 2}, {"actor": "alex", "act": "go", "target": "corral"}]}); s["seconds"] = 70
r = compile_script(s)
ok = r["ok"] and not r["quality"]
fails += 0 if ok else 1
print(("PASS " if ok else "FAIL ") + "hitboxes: no overlaps, nobody inside a block, camera clear" + ("" if ok else f" {r['quality']}"))

# the camera must keep up with the hero: he is never outside the safe part of the frame while walking, searching or carrying things
s = copy.deepcopy(base)
s["stations"] = [{"id": "lib", "type": "library"}, {"id": "shop", "type": "stall", "gap": 8}, {"id": "mine", "type": "mine", "gap": 9}]
s["beats"] = [{"text": "Walk to the library", "actions": [{"act": "go", "target": "lib"}]},
              {"text": "Search the catalog slowly", "actions": [{"act": "search", "target": "lib"}]},
              {"text": "Bring a book to the shop", "actions": [{"act": "fetch", "target": "lib", "to": "shop", "item": "item_book"}]},
              {"text": "Walk all the way to the mine", "actions": [{"act": "go", "target": "mine"}]},
              {"text": "Sprint back to the shop", "actions": [{"act": "sprint", "target": "shop"}]}]
s["seconds"] = 45
r = compile_script(s)
fr = r.get("framing", {})
ok = r["ok"] and fr.get("hidden", 99) == 0
fails += 0 if ok else 1
print(("PASS " if ok else "FAIL ") + f"camera keeps the hero in frame while he moves ({fr})")

print("OK" if not fails else f"{fails} FAILED")
sys.exit(1 if fails else 0)
