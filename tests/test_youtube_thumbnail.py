from PIL import Image

from services.youtube import YouTubeService


def test_thumbnail_stays_vertical_jpeg_under_2mb(tmp_path):
    src = tmp_path / "cover.png"
    Image.effect_noise((1080, 1920), 80).convert("RGB").save(src)
    out = YouTubeService.make_thumbnail(str(src))
    assert out.suffix == ".jpg" and out.stat().st_size < 2_000_000
    assert Image.open(out).size == (1080, 1920)
