import pytest

import script_gen as sg

MD = """# T

## Hook

Hi.

## Section 1: One

a b c

## Section 2: Two

d e

## Common Mistakes

x

## Recap

y
"""


# Uzunluq effektiv suretle (intro/basliq/outro + pauzalar daxil) hesablanir: 2402 soz -> 935 s,
# 2364 soz -> 967 s (~150 soz/deq). Xalis 199 wpm ile 16 deq-lik video cixirdi.
def test_words_to_add():
    assert sg.words_to_add(1000, 480) == 260     # ceil(480/60*150*1.05)=1260
    assert sg.words_to_add(1400, 480) == 0


def test_words_to_cut_for_max_length():
    assert sg.words_to_cut(1600, 600) == 145     # 1600 - floor(600/60*150*0.97)=1455
    assert sg.words_to_cut(1300, 600) == 0


def test_words_for_seconds():
    assert sg.words_for_seconds(30) == 83        # ceil(0.5*150*1.10)


def test_shorten_rewrites_the_longest_teaching_sections_until_enough_is_cut():
    md = ("# T\n\n## Hook\n\n" + "h " * 50 + "\n\n## Section 1: A\n\n" + "a " * 300
          + "\n\n## Section 2: B\n\n" + "b " * 200 + "\n\n## Common Mistakes\n\n" + "m " * 100)
    asked = []

    def rewrite(heading, body, target):
        asked.append((heading, target))
        return "x " * target

    out = sg.shorten(md, 150, rewrite)
    assert asked == [("Section 1: A", 150)]
    assert sg.word_count(out) == sg.word_count(md) - 150
    assert "## Section 2: B" in out and "## Common Mistakes" in out and "h h" in out


def test_teaching_headings():
    assert sg.teaching_headings(MD) == ["Section 1: One", "Section 2: Two"]


def test_insert_before_common_mistakes():
    out = sg.insert_before(MD, "## Common Mistakes", "## Section 3: Three\n\nnew text")
    assert out.index("## Section 3: Three") < out.index("## Common Mistakes")
    assert "d e\n\n## Section 3: Three\n\nnew text\n\n## Common Mistakes" in out


def test_insert_before_missing_anchor():
    with pytest.raises(ValueError):
        sg.insert_before("# x", "## Common Mistakes", "b")
