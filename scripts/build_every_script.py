#!/usr/bin/env python3
"""Builds the "Every X at today's price" tier-list script of a product family from its dataset and a price file.

  python scripts/build_every_script.py ryzen7                       # newest data/prices/<date>.json, written to data/scripts/every_ryzen7.json
  python scripts/build_every_script.py all --prices data/prices/2026-11-23.json
  python scripts/build_every_script.py rtx --max-age 2              # refuse prices older than 2 days (default 3)

The facts of the video come from two files, never from a model: data/products/<family>.json (items, specs, one narration line per item, the editorial tier letters) and
data/prices/<date>.json (the prices of that day: guide/prices.md says how to collect them). Items without a price today are left out; the families' "gone" scene says so.
The script goes through the same validator as every generated script. The tier letters are editorial: read the table this prints and change the dataset if a price
move makes one of them untrue (a "bargain" that is no longer one).
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from services.prices import age_days, families, load_family, load_prices, num_to_words, price_of, spoken_euros  # noqa: E402

MAX_ITEMS = 9


def _line(item: Dict[str, Any], price: float, prices: Dict[str, Any], family: str) -> str:
    """The item's narration line; its `alt` line replaces it when the item costs more than the one named in `pricier_than` (a price comparison that only holds on some days)."""
    text = item["line"]
    alt = item.get("alt")
    if alt:
        other = price_of(prices, family, alt["pricier_than"])
        if other is not None and price > other:
            text = alt["line"]
    return text.format(price=spoken_euros(price))


def hook_line(fam: Dict[str, Any], priced: list) -> str:
    """The first line: a conflict taken from today's data (the priciest item gets an F) when the board has an F, otherwise the family's own hook."""
    count = num_to_words(len(priced)).capitalize()
    noun = "cards" if priced and priced[0][1].get("kind") == "gpu" else "chips"
    fails = [p for p in priced if p[1]["tier"] == "F"]
    if fails and max(priced, key=lambda x: x[0]) in fails:
        return f"{count} {fam['cat']} {noun} ranked by value, and the most expensive one gets an F."
    if fails:
        return f"{count} {fam['cat']} {noun} ranked by value, and one of them gets an F."
    return fam["hook"].format(count=count)


def build(name: str, prices: Dict[str, Any]) -> Dict[str, Any]:
    """The MotionProject dict of one family (not yet validated)."""
    fam = load_family(name)
    priced = []
    for it in fam["items"]:
        p = price_of(prices, name, it["id"])
        if p is not None:
            priced.append((p, it))
    priced.sort(key=lambda x: (x[1]["tier"] == "S", x[0]))  # cheapest first, but the S-tier pick lands last: the reveal is the climax, not an F
    gone = fam.get("gone")
    if gone and all(price_of(prices, name, i) is None for i in gone["ids"]) and fam.get("now"):
        fam = {**fam, **fam["now"]}  # the older series is not on sale today: the video is named after what it really shows ("RTX 50", not "RTX 40 and 50")
    if not 6 <= len(priced) <= MAX_ITEMS:
        raise ValueError(f"{name}: {len(priced)} items have a price (a tier list needs 6-{MAX_ITEMS}): edit data/products/{name}.json or the price file")
    scenes: List[Dict[str, Any]] = [dict(type="bigText", text=f"Every {fam['short']}", accentText=fam["criterion"], kicker="tier list", narration=hook_line(fam, priced), durationInFrames=120)]
    board: List[str] = []
    for n, (price, it) in enumerate(priced):
        board.append(f"{it['tier']}|{it['label']}")
        narration = _line(it, price, prices, name)
        if n >= 1 and "more than" not in narration and len(narration.split()) <= 12 and price - priced[n - 1][0] >= 20:
            narration += f" That is {spoken_euros(price - priced[n - 1][0])} more than the {priced[n - 1][1]['label']}."  # a true comparison from the two prices, so the lines stop sounding the same
        narration += f" {fam['loop']}" if n == 0 else ""
        scenes.append(dict(type="tier", text=f"Ranking {fam['cat']}", accentText=fam["criterion"], kicker=f"{n + 1} of {len(priced)}", items=list(board), narration=narration, value=round(price), unit="€", durationInFrames=170))
    if gone and all(price_of(prices, name, i) is None for i in gone["ids"]):
        scenes.append(dict(type="textWithAccent", text=gone["text"], accentText=gone["accent"], narration=gone["narration"], durationInFrames=150))
    extra = fam.get("extra")
    if extra:
        scenes.append(dict(type="textWithAccent", text=extra["text"], accentText=extra["accent"], narration=extra["narration"], durationInFrames=150))
    tk = fam["takeaway"]
    scenes.append(dict(type="textWithAccent", text=tk["text"], accentText=tk["accent"], narration=tk["narration"], durationInFrames=150))
    a, b = fam["vote"]
    scenes.append(dict(type="outro", text="YOUR PICK?", accentText="Vote below", narration=f"Prices change every day. Which would you buy, {a} or {b}?", items=[a, b], durationInFrames=120))
    tags = " ".join(f"#{t}" for t in ["siliconverdict", *fam["hashtags"]])
    return dict(
        topic=f"Every {fam['short']} ranked by gaming value at the prices of {prices['date']}",
        screen_title=fam["screen_title"],
        title=f"Which {fam['short']} Is Actually Worth It Today? {tags}",  # a question the viewer wants answered, not a catalogue line
        description=f"{len(priced)} {fam['short']} products ranked by gaming value at today's lowest PcComponentes prices ({prices['date']}), from {priced[0][0]:.0f} to {priced[-1][0]:,.0f} euros. Prices change daily.",
        tags=fam["tags"], pinned_comment=f"{a} or {b}? Reply with one word.", accent="#00F0FF", kind="curiosity", format="tier", scenes=scenes,
    )


def validate(data: Dict[str, Any]) -> List[str]:
    from services.motion_generator import MotionProject, make_validator
    return make_validator(facts=None, fmt="tier", retention=True)(MotionProject.model_validate(data))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("family", help="a product family (data/products/<name>.json) or 'all'")
    ap.add_argument("--prices", default=None, help="price file (default: the newest in data/prices/)")
    ap.add_argument("--max-age", type=int, default=3, help="refuse prices older than this many days (default 3)")
    ap.add_argument("--out-dir", default=str(BASE_DIR / "data" / "scripts"))
    args = ap.parse_args()
    prices = load_prices(Path(args.prices) if args.prices else None)
    age = age_days(prices)
    print(f"Prices of {prices['date']} ({age} day(s) old) from {prices['source']}")
    if args.max_age is not None and age > args.max_age:
        print(f"Too old (--max-age {args.max_age}): collect new prices first (guide/prices.md).")
        return 2
    status = 0
    for name in (families() if args.family == "all" else [args.family]):
        data = build(name, prices)
        problems = validate(data)
        print(f"\n== {name}: {data['title']}")
        tiers = [s for s in data["scenes"] if s["type"] == "tier"]
        for entry in tiers[-1]["items"]:
            print("   ", entry)
        if problems:
            status = 1
            print("   PROBLEMS:", *problems, sep="\n     - ")
            continue
        out = Path(args.out_dir) / f"every_{name}.json"
        out.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"   written: {out.relative_to(BASE_DIR) if out.is_relative_to(BASE_DIR) else out}")
    return status


if __name__ == "__main__":
    sys.exit(main())
