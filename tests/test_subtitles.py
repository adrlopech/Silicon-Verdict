from services.subtitles import format_ass_time, group_words_into_chunks


def test_ass_time_format():
    assert format_ass_time(0) == "0:00:00.00"
    assert format_ass_time(61.5) == "0:01:01.50"
    assert format_ass_time(3725.25) == "1:02:05.25"


def test_negative_time_clamps_to_zero():
    assert format_ass_time(-3) == "0:00:00.00"


def test_chunks_are_two_or_three_words_and_lossless():
    for n in range(1, 30):
        words = [{"word": str(i)} for i in range(n)]
        chunks = group_words_into_chunks(words)
        assert [w for c in chunks for w in c] == words
        if n >= 2:
            assert all(1 <= len(c) <= 3 for c in chunks)
            assert len(chunks[-1]) >= 2 or n == 1


def test_four_leftover_words_split_two_two():
    assert [len(c) for c in group_words_into_chunks([{}] * 4)] == [2, 2]
