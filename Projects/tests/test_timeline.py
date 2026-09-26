
import timeline as tl

SCENES = [{"section": "Hook", "duration": 10}, {"section": "Hook", "duration": 5},
          {"section": "Section 1: A", "duration": 20}, {"section": "Recap", "duration": 8}]


def test_display_title():
    assert tl.display_title("Section 2: Why Brands Matter") == "Why Brands Matter"
    assert tl.display_title("Recap") == "Recap"


def test_section_starts_with_offset():
    assert tl.section_starts(SCENES, 4.0) == [("Hook", 4.0), ("Section 1: A", 19.0), ("Recap", 39.0)]

