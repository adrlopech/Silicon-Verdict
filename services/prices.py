"""Product price data for the "Every X at today's price" videos.

`data/products/<family>.json` holds the editorial side of a family (items, specs, one narration line per item, tier letters) and
`data/prices/<date>.json` the prices collected that day (see guide/prices.md). `scripts/build_every_script.py` joins both into a MotionProject.
"""
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional

from config.settings import settings

PRODUCTS_DIR = settings.BASE_DIR / "data" / "products"
PRICES_DIR = settings.BASE_DIR / "data" / "prices"

_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def num_to_words(n: int) -> str:
    """Spoken English for 0 to 999,999 ("one thousand four hundred sixty-four"): narration spells figures out so the voice reads them right."""
    n = int(round(n))
    if n < 0 or n > 999_999:
        raise ValueError(f"cannot spell {n}")
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + (f"-{_ONES[n % 10]}" if n % 10 else "")
    if n < 1000:
        return f"{_ONES[n // 100]} hundred" + (f" {num_to_words(n % 100)}" if n % 100 else "")
    return f"{num_to_words(n // 1000)} thousand" + (f" {num_to_words(n % 1000)}" if n % 1000 else "")


def load_family(name: str) -> Dict[str, Any]:
    path = PRODUCTS_DIR / f"{name}.json"
    if not path.is_file():
        raise FileNotFoundError(f"no product family '{name}' (data/products/{name}.json)")
    return json.loads(path.read_text(encoding="utf-8"))


def families() -> list:
    return sorted(p.stem for p in PRODUCTS_DIR.glob("*.json"))


def latest_prices_file() -> Optional[Path]:
    files = sorted(PRICES_DIR.glob("????-??-??.json"))
    return files[-1] if files else None


def load_prices(path: Optional[Path] = None) -> Dict[str, Any]:
    """{'date': 'YYYY-MM-DD', 'source': ..., 'currency': 'EUR', 'prices': {'<family>:<id>': {'price': 194.0, 'name': 'listing title'}}}"""
    path = path or latest_prices_file()
    if path is None or not Path(path).is_file():
        raise FileNotFoundError("no price file in data/prices/ (collect one: guide/prices.md)")
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data["_path"] = str(path)
    return data


def age_days(prices: Dict[str, Any], today: Optional[date] = None) -> int:
    return ((today or date.today()) - datetime.strptime(prices["date"], "%Y-%m-%d").date()).days


def price_of(prices: Dict[str, Any], family: str, item_id: str) -> Optional[float]:
    entry = prices.get("prices", {}).get(f"{family}:{item_id}")
    return float(entry["price"]) if entry and entry.get("price") else None


def spoken_euros(amount: float) -> str:
    """194.0 -> 'one hundred ninety-four euros' (the video says whole euros)."""
    return f"{num_to_words(round(amount))} euros"


def clean_listing(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def price_files() -> list:
    return sorted(PRICES_DIR.glob("????-??-??.json"))


def history(key: str) -> list:
    """[(date, price)] of '<family>:<item id>' over every stored price file, oldest first (days without a listing are left out)."""
    out = []
    for path in price_files():
        entry = json.loads(path.read_text(encoding="utf-8")).get("prices", {}).get(key)
        if entry and entry.get("price"):
            out.append((path.stem, float(entry["price"])))
    return out


def moves(min_pct: float = 5.0) -> list:
    """Price changes between the two newest price files: [{key, before, after, pct}] with |pct| >= min_pct, the biggest drops first.
    Items missing from either day are ignored. [] when fewer than two files exist."""
    files = price_files()
    if len(files) < 2:
        return []
    old, new = (json.loads(p.read_text(encoding="utf-8")).get("prices", {}) for p in files[-2:])
    out = []
    for key, entry in new.items():
        a, b = (old.get(key) or {}).get("price"), (entry or {}).get("price")
        if a and b and abs(b / a - 1) * 100 >= min_pct:
            out.append({"key": key, "before": float(a), "after": float(b), "pct": round((b / a - 1) * 100, 1)})
    return sorted(out, key=lambda m: m["pct"])
