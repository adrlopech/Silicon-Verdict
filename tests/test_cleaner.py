"""The `limpieza` cleaner: what it removes, what it keeps and that a dry run touches nothing."""
from pathlib import Path

import pytest

from services.cleaner import execute_comprehensive_cleanup


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    def make(rel: str, size: int = 10) -> None:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x" * size)

    make("output/youtube/Video A/a.mp4", 100)
    make("output/youtube/Video A/a.png", 5)
    make("output/tiktok/Video A/a.mp4", 100)
    make("output/tiktok/Video A/a.txt", 3)
    make("output/tiktok_small/Video_A.mp4", 50)
    make("temp/frame.png", 7)
    make("temp/voice.mp3", 9)
    make("temp/notes.txt", 1)
    make("temp/run_abc/raw.mp4", 200)
    make("data/history.db", 1)
    make("assets/audio/bed.mp3", 1)
    return tmp_path


def names(root: Path) -> set:
    return {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}


def test_dry_run_deletes_nothing(tree: Path):
    before = names(tree)
    res = execute_comprehensive_cleanup(base_dir=tree, dry_run=True)
    assert names(tree) == before
    assert res["dry_run"] and res["freed_bytes"] > 0


def test_full_cleanup_keeps_data_and_assets(tree: Path):
    res = execute_comprehensive_cleanup(base_dir=tree)
    assert names(tree) == {"data/history.db", "assets/audio/bed.mp3"}
    assert len(res["deleted_videos"]) == 4 and res["preserved_tiktok"] == []
    assert res["freed_bytes"] == 100 + 5 + 100 + 3 + 50 + 7 + 9 + 1 + 200


def test_keep_tiktok_preserves_both_copies(tree: Path):
    res = execute_comprehensive_cleanup(base_dir=tree, clean_tiktok=False, clean_metadata_txt=False)
    left = names(tree)
    assert "output/tiktok/Video A/a.mp4" in left and "output/tiktok_small/Video_A.mp4" in left
    assert not any(n.startswith("output/youtube") or n.startswith("temp/") for n in left)
    assert sorted(Path(p).name for p in res["preserved_tiktok"]) == ["Video_A.mp4", "a.mp4"]
