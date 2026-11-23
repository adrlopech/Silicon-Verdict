#!/usr/bin/env python3
"""Stores collected prices in data/prices/<date>.json (see guide/prices.md and scripts/pccomponentes_prices.js).

  echo '{"ryzen7:5700X": {"price": 194, "name": "AMD Ryzen 7 5700X"}, "ryzen7:5700X3D": null}' | python scripts/save_prices.py [--date YYYY-MM-DD]

Keys are <family>:<item id> of data/products/<family>.json; null means "no standalone listing today". Entries are merged into the file of that date.
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from services.prices import PRICES_DIR, families, load_family  # noqa: E402

SOURCE = "pccomponentes.com (cheapest listing of the standalone part, sorted by price)"


def merge(existing: dict, new: dict, day: str) -> dict:
    data = existing or {"date": day, "source": SOURCE, "currency": "EUR", "prices": {}}
    for key, value in new.items():
        family, _, item_id = key.partition(":")
        if family not in families() or item_id not in {i["id"] for i in load_family(family)["items"]} | {x for g in [load_family(family).get("gone", {})] for x in g.get("ids", [])}:
            raise ValueError(f"unknown product '{key}': it must be <family>:<item id> of data/products/")
        data["prices"][key] = {"price": float(value["price"]), "name": value.get("name", "")[:120]} if value and value.get("price") else {"price": None}
    return data


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", default=str(date.today()))
    args = ap.parse_args()
    new = json.load(sys.stdin)
    path = PRICES_DIR / f"{args.date}.json"
    PRICES_DIR.mkdir(parents=True, exist_ok=True)
    data = merge(json.loads(path.read_text()) if path.is_file() else {}, new, args.date)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(new)} prices stored in {path.relative_to(BASE_DIR)} ({sum(1 for v in data['prices'].values() if v['price'])} priced, {sum(1 for v in data['prices'].values() if not v['price'])} without listing)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
