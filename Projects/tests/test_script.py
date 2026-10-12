import os
import re

import pytest

import script

REAL = r"C:\YouTubeAI\Ssenariler\eli5_business_how_free_apps_make_billions_script.md"

PROD = """# How Free Apps Make Billions Without Charging You
## ELI5 Business — 12-Minute YouTube Video Script

**Format:** Educational explainer
**Target runtime:** Approximately 12 minutes

---

## 00:00–00:45 — Hook: If It’s Free, Who Pays?

**VISUAL:** A phone screen fills with app icons.

**NARRATION:**

Imagine an app you use every single day.

So here’s the big question: **if you’re not paying for the app, who is?**

---

## 00:45–02:00 — Secret #1: Users Are an Opportunity

**VISUAL:** A small app starts with ten users.

**NARRATION:**

Should you immediately charge everyone five dollars a month? Or should you first give people a reason to join?

---

## Editing and Visual Plan

- Use the owl in every scene.

## Production Notes

Keep it simple.
"""

PLAIN = """# Why Coffee Costs $5

People pay $5 for coffee. That is a lot.

## The Beans

Beans are cheap.
"""


def test_production_format_reads_only_narration_word_for_word():
    got = script.parse(PROD, "x")
    assert got["title"] == "How Free Apps Make Billions Without Charging You"
    assert [s["name"] for s in got["sections"]] == ["Hook: If It’s Free, Who Pays?",
                                                    "Secret #1: Users Are an Opportunity"]
    assert got["sections"][0]["visual"] == "A phone screen fills with app icons."
    assert got["sections"][0]["paragraphs"] == [
        "Imagine an app you use every single day.",
        "So here’s the big question: if you’re not paying for the app, who is?"]


def test_plain_script_without_markers_is_accepted():
    got = script.parse(PLAIN, "x")
    assert got["title"] == "Why Coffee Costs $5"
    assert got["sections"][0] == {"name": "", "visual": "", "paragraphs": ["People pay $5 for coffee. That is a lot."]}
    assert got["sections"][1]["name"] == "The Beans"


def test_missing_title_uses_file_name():
    assert script.parse("Just one line of narration.", "my-video")["title"] == "my-video"


def test_scenes_keep_every_word_in_order():
    sections = script.parse(PROD, "x")["sections"]
    scenes = script.split_scenes(sections, max_words=12)
    joined = " ".join(s["text"] for s in scenes)
    original = " ".join(p for s in sections for p in s["paragraphs"])
    assert joined.split() == original.split()
    assert [s["n"] for s in scenes] == list(range(1, len(scenes) + 1))
    assert scenes[0]["section_start"] and scenes[0]["section"] == "Hook: If It’s Free, Who Pays?"
    assert sum(s["section_start"] for s in scenes) == 2
    assert all(len(s["text"].split()) <= 20 for s in scenes)


def test_slug():
    assert script.slugify("How Free Apps Make Billions — Without You?") == "how-free-apps-make-billions-without-you"


MID_VISUAL = """# Mid Visual Test
## Section A

**VISUAL:** First visual.

**NARRATION:**

First narration paragraph.

**VISUAL:** Second visual.

Second narration paragraph after the mid visual.
"""

LIST_AND_LABELS = """# Rules Video
## Rules

**NARRATION:**

- First bullet point here.
- **Rule one:** keep the text.

**Rule two:** standalone label line.

| Col A | Col B |
|---|---|
| x | y |

Plain closing line.
"""


def test_visual_between_narration_paragraphs_does_not_end_narration():
    secs = script.parse(MID_VISUAL, "x")["sections"]
    assert [s["paragraphs"] for s in secs] == [["First narration paragraph."],
                                               ["Second narration paragraph after the mid visual."]]
    assert secs[0]["visual"] == "First visual."
    assert secs[1]["visual"] == "Second visual." and secs[1]["cont"] is True and secs[1]["name"] == "Section A"
    scenes = script.split_scenes(secs)
    assert scenes[0]["visual"] == "First visual." and scenes[0]["section_start"] is True
    assert scenes[-1]["visual"] == "Second visual." and scenes[-1]["section_start"] is False
    assert " ".join(s["text"] for s in scenes) == ("First narration paragraph. "
                                                   "Second narration paragraph after the mid visual.")


def test_bullets_and_inline_labels_inside_narration_are_kept_as_text():
    paras = script.parse(LIST_AND_LABELS, "x")["sections"][0]["paragraphs"]
    assert paras == ["First bullet point here.", "Rule one: keep the text.",
                     "Rule two: standalone label line.", "Col A, Col B", "x, y", "Plain closing line."]


def _independent_narration_words(path: str) -> list[str]:
    """Own extraction, not via script.parse: lines between **NARRATION:** and the next ## heading."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().replace("\r\n", "\n").split("\n")
    words, on = [], False
    for ln in lines:
        s = ln.strip()
        if s.startswith("## "):
            on = False
            continue
        if re.match(r"^\*\*\s*NARRATION\s*:\s*\*\*", s, re.I):
            on = True
            continue
        if not on or not s or s == "---" or s.startswith("**VISUAL:**"):
            continue
        s = re.sub(r"^(?:[-*+]|\d+\.)\s+", "", s).replace("**", "").replace("*", "")
        words.extend(s.split())
    return words


@pytest.mark.skipif(not os.path.exists(REAL), reason="real script file not present")
def test_real_file_keeps_every_narration_word_in_order():
    scenes = script.build(REAL)["scenes"]
    got = " ".join(s["text"] for s in scenes).split()
    assert got == _independent_narration_words(REAL)
    assert "So how do companies encourage users to come back?" in " ".join(s["text"] for s in scenes)


def test_title_without_letters_uses_the_file_name_for_the_slug(tmp_path):
    p = tmp_path / "my_script.md"
    p.write_text("# ???\n\nHello there, this is the story.\n", encoding="utf-8")
    assert script.build(str(p))["slug"] == "my-script"
