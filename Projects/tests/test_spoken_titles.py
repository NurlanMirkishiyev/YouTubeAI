from timeline import spoken_titles


def test_hook_section_gets_no_title_but_other_sections_do():
    # Istifadeci (2026-09-28): ilk saniyelerdeki "Hook" yazisi olmasin, diger basliqlar qalsin.
    # Regex-de \b evezine backspace (0x08) var idi -> "Hook" hem yazilir, hem seslendirilirdi.
    scenes = [{"section": "Hook"}, {"section": "Hook"}, {"section": "Section 1: The Power of Nine"},
              {"section": "Section 1: The Power of Nine"}, {"section": "Section 2: Left Digit"}]
    assert spoken_titles(scenes) == [None, None, "The Power of Nine", None, "Left Digit"]


def test_hook_variants_are_skipped_but_hooked_words_are_not():
    assert spoken_titles([{"section": "Hook: Carnival"}]) == [None]
    assert spoken_titles([{"section": "Hooked on Nines"}]) == ["Hooked on Nines"]
