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


def test_words_to_add():
    assert sg.words_to_add(1500, 600) == 590     # ceil(600/60*199*1.05)=2090
    assert sg.words_to_add(2500, 600) == 0


def test_words_for_seconds():
    assert sg.words_for_seconds(30) == 110       # ceil(0.5*199*1.10)


def test_teaching_headings():
    assert sg.teaching_headings(MD) == ["Section 1: One", "Section 2: Two"]


def test_insert_before_common_mistakes():
    out = sg.insert_before(MD, "## Common Mistakes", "## Section 3: Three\n\nnew text")
    assert out.index("## Section 3: Three") < out.index("## Common Mistakes")
    assert "d e\n\n## Section 3: Three\n\nnew text\n\n## Common Mistakes" in out


def test_insert_before_missing_anchor():
    with pytest.raises(ValueError):
        sg.insert_before("# x", "## Common Mistakes", "b")
