#!/usr/bin/env python3
"""Price moves between the two newest files of data/prices/ (a drop is a reason for an "Every X" video today) and the history of one product.

  python scripts/price_drops.py                    # every move of 5 % or more
  python scripts/price_drops.py --min 10
  python scripts/price_drops.py --history rtx:5070 # its price on every collected day
"""
import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from services.prices import history, moves, price_files  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min", type=float, default=5.0, help="smallest move in percent (default 5)")
    ap.add_argument("--history", default=None, help="<family>:<item id>")
    args = ap.parse_args()
    if args.history:
        for day, price in history(args.history):
            print(f"{day}  {price:>9,.2f} EUR")
        return 0
    files = price_files()
    if len(files) < 2:
        print("Only one price file so far: moves need two days (guide/prices.md).")
        return 0
    print(f"{files[-2].stem} -> {files[-1].stem}")
    found = moves(args.min)
    for m in found:
        print(f"  {m['pct']:+6.1f}%  {m['key']:<22} {m['before']:>8,.2f} -> {m['after']:>8,.2f} EUR")
    if not found:
        print(f"  no move of {args.min:g}% or more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
