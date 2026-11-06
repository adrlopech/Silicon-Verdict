from datetime import datetime

from services.output_layout import sanitize_title, timestamp_stem


def test_hashtags_and_emojis_removed():
    assert sanitize_title("Why SSDs forget 🔥 #shorts #tech") == "Why SSDs forget"


def test_filesystem_unsafe_characters_removed():
    assert "/" not in sanitize_title("a/b\\c:d*e?f")


def test_empty_title_has_fallback():
    assert sanitize_title("") == "Untitled video"
    assert sanitize_title("#only #tags") == "Untitled video"


def test_long_title_is_cut_at_a_word_boundary():
    t = sanitize_title("word " * 60, max_len=30)
    assert len(t) <= 30 and not t.endswith(" ")


def test_timestamp_stem_format():
    assert timestamp_stem(datetime(2026, 3, 4, 5, 6, 7)) == "2026-03-04_05-06-07"
