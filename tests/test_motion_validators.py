from services.motion_generator import _norm, looks_english, quote_supported

FACTS = _norm("The game's engine streams the open world from the SSD in small chunks, so the player never sees a loading screen while driving.")


def test_english_passes():
    assert looks_english("Your SSD is much faster than a hard drive because it has no moving parts.")


def test_spanish_is_rejected():
    assert not looks_english("Tu disco duro es mucho más lento que el SSD porque tiene partes móviles.")


def test_accents_rejected_even_when_short():
    assert not looks_english("¿Qué es esto?")


def test_exact_quote_supported():
    assert quote_supported("streams the open world from the SSD in small chunks", FACTS)


def test_small_difference_tolerated():
    assert quote_supported("streams the open world from the SSD in small chunk", FACTS)


def test_invented_quote_rejected():
    assert not quote_supported("the engine renders every frame on a quantum computer", FACTS)


def test_too_short_quote_rejected():
    assert not quote_supported("open world", FACTS)
