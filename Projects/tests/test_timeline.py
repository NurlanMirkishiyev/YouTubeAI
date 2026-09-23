import pytest

import timeline as tl

SCENES = [{"section": "Hook", "duration": 10}, {"section": "Hook", "duration": 5},
          {"section": "Section 1: A", "duration": 20}, {"section": "Recap", "duration": 8}]


def test_plan_timeline_without_cards():
    assert tl.plan_timeline([10, 20, 30], 0.5) == [10.5, 20.5, 30]


def test_plan_timeline_with_cards_total_matches():
    durs = tl.plan_timeline([10, 20], 0.5, 4.0, 6.0)
    assert durs == [4.5, 10.5, 20.5, 6.0]
    assert tl.montage_total(durs, 0.5) == pytest.approx(40.0)


def test_plan_timeline_empty_raises():
    with pytest.raises(ValueError):
        tl.plan_timeline([], 0.5)


def test_shift_srt():
    src = "1\n00:00:01,000 --> 00:00:02,500\nHi\n"
    assert tl.shift_srt(src, 4.0) == "1\n00:00:05,000 --> 00:00:06,500\nHi\n"


def test_shift_srt_crosses_minute():
    assert "00:01:03,200" in tl.shift_srt("00:00:59,200 --> 00:01:00,000", 4.0)


def test_display_title():
    assert tl.display_title("Section 2: Why Brands Matter") == "Why Brands Matter"
    assert tl.display_title("Recap") == "Recap"


def test_section_starts_with_offset():
    assert tl.section_starts(SCENES, 4.0) == [("Hook", 4.0), ("Section 1: A", 19.0), ("Recap", 39.0)]


def test_first_of_section():
    assert tl.first_of_section(SCENES) == [True, False, True, True]
