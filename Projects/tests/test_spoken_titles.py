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


def test_no_backspace_characters_in_source():
    # Reyestr #28 ve 2026-10-04 (visuals.py): regex-de `\b` evezine 0x08 yazilmisdi - sessizce isleyirdi
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[2]
    # 2026-10-04: progress.md-de `Projects\forget` -> form feed (0x0C) da tapildi - butun idare simvollari + sened
    import re
    control = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f]")
    files = [*root.glob("Projects/*.py"), *root.glob("Projects/tests/*.py"), *root.glob("Remotion/src/**/*.ts*"),
             *root.glob("*.md"), *root.glob("docs/**/*.md")]
    bad = [str(f) for f in files if control.search(f.read_text(encoding="utf-8"))]
    assert bad == []
