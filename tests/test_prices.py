"""Product datasets, price files and the builder of the "Every X at today's price" scripts."""
import copy
from datetime import date

import pytest

from scripts.build_every_script import build, validate
from scripts.genera_batch import every_pick
from scripts.save_prices import merge
from services.prices import age_days, families, load_prices, num_to_words, spoken_euros


@pytest.mark.parametrize("n,words", [(0, "zero"), (7, "seven"), (19, "nineteen"), (20, "twenty"), (194, "one hundred ninety-four"), (1000, "one thousand"),
                                      (1464, "one thousand four hundred sixty-four"), (8717, "eight thousand seven hundred seventeen"), (12000, "twelve thousand")])
def test_num_to_words(n, words):
    assert num_to_words(n) == words


def test_spoken_euros_rounds_to_whole_euros():
    assert spoken_euros(1849.99) == "one thousand eight hundred fifty euros"
    assert spoken_euros(194.0) == "one hundred ninety-four euros"


@pytest.fixture(scope="module")
def prices():
    return load_prices()


@pytest.mark.parametrize("family", families())
def test_every_family_builds_a_script_that_passes_the_validator(family, prices):
    data = build(family, prices)
    assert validate(data) == []
    assert data["format"] == "tier" and data["title"].startswith("Which ") and "#siliconverdict" in data["title"]
    tiers = [s for s in data["scenes"] if s["type"] == "tier"]
    assert 6 <= len(tiers) <= 9
    assert len(tiers[-1]["items"]) == len(tiers)  # the last board holds every item once
    assert "euros" in " ".join(s["narration"] for s in tiers)


def test_items_are_placed_by_price_and_unpriced_ones_are_left_out(prices):
    data = build("ryzen7", prices)
    board = [s for s in data["scenes"] if s["type"] == "tier"][-1]["items"]
    assert "S|5700X3D" not in board  # no standalone listing on that day
    spoken = [s["narration"] for s in data["scenes"] if s["type"] == "tier"]
    assert "one hundred ninety-four euros" in spoken[0]  # the cheapest first


def test_alt_line_applies_only_when_the_condition_holds(prices):
    cheap = copy.deepcopy(prices)
    cheap["prices"]["ryzen7:5800X3D"]["price"] = 300.0  # cheaper than the 7800X3D (335.99): the comparison line must go
    assert "more than the 7800X3D" not in " ".join(s["narration"] for s in build("ryzen7", cheap)["scenes"])
    assert "more than the 7800X3D" in " ".join(s["narration"] for s in build("ryzen7", prices)["scenes"])


def test_gone_scene_only_when_every_listed_item_is_missing(prices):
    assert any(s["text"] == "40 series gone" for s in build("rtx", prices)["scenes"])
    back = copy.deepcopy(prices)
    back["prices"]["rtx:4070S"] = {"price": 650.0, "name": "RTX 4070 Super"}
    assert not any(s["text"] == "40 series gone" for s in build("rtx", back)["scenes"])


def test_too_few_priced_items_is_an_error(prices):
    bare = copy.deepcopy(prices)
    for key in list(bare["prices"]):
        if key.startswith("radeon:"):
            bare["prices"][key] = {"price": None}
    with pytest.raises(ValueError):
        build("radeon", bare)


def test_save_prices_merge_rejects_unknown_products():
    day = "2026-11-24"
    merged = merge({}, {"ryzen7:5700X": {"price": 190, "name": "x"}, "ryzen7:5700X3D": None}, day)
    assert merged["prices"]["ryzen7:5700X"]["price"] == 190.0 and merged["prices"]["ryzen7:5700X3D"]["price"] is None
    with pytest.raises(ValueError):
        merge({}, {"ryzen7:nope": {"price": 1}}, day)
    with pytest.raises(ValueError):
        merge({}, {"cpus:5700X": {"price": 1}}, day)


def test_every_pick_needs_fresh_prices(prices):
    assert age_days(prices, date(2026, 11, 25)) == 2
    pick, note = every_pick([{"format": "tier"}, {"format": "versus"}], today=date(2026, 12, 20))
    assert pick is None and "days old" in note
    pick, note = every_pick([{"format": "tier"}], today=date(2026, 11, 24))
    assert pick and pick["format"] == "tier" and pick["script"].startswith("data/scripts/every_") and pick["family"] in families()
