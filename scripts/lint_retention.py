#!/usr/bin/env python3
"""Measures the hand-written Motion banks against the retention rules (cold open, open loop, pattern breaks).

The generator holds NEW scripts to these rules (`make_validator(..., retention=True)`); the banks were written before and are only reported here.

Usage:
  python scripts/lint_retention.py            # every bank type, one summary line each
  python scripts/lint_retention.py fix -v     # one type, list the scripts that fail
"""
import json
import sys
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from services.motion_generator import MotionProject, retention_problems  # noqa: E402

BANK = BASE_DIR / "docs" / "generated_scripts" / "bank"


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    verbose = "-v" in sys.argv
    kinds = args or sorted(p.name for p in BANK.iterdir() if p.is_dir() and p.name != "src")
    for kind in kinds:
        total, failing, reasons = 0, 0, Counter()
        for f in sorted((BANK / kind).glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            data.pop("name", None)
            data.pop("estimated_seconds", None)
            problems = retention_problems(MotionProject.model_validate(data))
            total += 1
            if problems:
                failing += 1
                for p in problems:
                    reasons[p.split(":")[0].split(" (")[0][:60]] += 1
                if verbose:
                    print(f"  {f.name}: {' | '.join(problems)}")
        print(f"{kind:10s} {total - failing:3d}/{total:3d} pass  " + "; ".join(f"{n}x {r}" for r, n in reasons.most_common(3)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
