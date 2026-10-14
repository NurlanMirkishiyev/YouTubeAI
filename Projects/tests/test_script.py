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


# --- Umumi format: etiket varianti ne olursa olsun rejissor qeydi oxunmur ---------------------------------

VOICEOVER = """# ELI5 Business: Why Expensive Brands Win

**Format:** 12-minute faceless business explainer | **Language:** English
**Visual identity:** Use the same owl mascot.

## Video title
**Why Expensive Brands Make People Want Them**

## Thumbnail idea
Show two handbags. The owl looks surprised. Use only a few words: **“WHY PAY MORE?”**

---

## Scene 1 — The Strange Power of a High Price (00:00–00:55)

**Voiceover**

Imagine two plain white T-shirts.

Which one feels more valuable?

**Visuals:** Compare two T-shirts. Cut to a handbag. On-screen text: “WHY?”

---

## Scene 2 — Price Becomes a Shortcut (00:55–02:00)

**Voiceover**

Let’s start with the simplest reason.

**Visuals:** Two olive oil bottles.

---

## Editing and Production Notes

- **Pacing:** Aim for 125 words per minute.

## Core Takeaway

**Expensive brands can sell more than products.**
"""


def _spoken(md: str) -> str:
    return " ".join(p for s in script.parse(md, "x")["sections"] for p in s["paragraphs"])


def test_voiceover_heading_and_visuals_label_are_not_spoken():
    got = script.parse(VOICEOVER, "x")
    assert [s["paragraphs"] for s in got["sections"]] == [
        ["Imagine two plain white T-shirts.", "Which one feels more valuable?"],
        ["Let’s start with the simplest reason."]]
    assert got["sections"][0]["visual"].startswith("Compare two T-shirts.")


def test_scene_number_and_timecode_are_removed_from_section_name():
    got = script.parse(VOICEOVER, "x")
    assert [s["name"] for s in got["sections"]] == ["The Strange Power of a High Price", "Price Becomes a Shortcut"]


def test_video_title_section_is_the_title_and_thumbnail_idea_is_kept():
    got = script.parse(VOICEOVER, "x")
    assert got["title"] == "Why Expensive Brands Make People Want Them"
    assert "two handbags" in got["thumbnail_idea"]
    assert got["thumbnail_text"] == "WHY PAY MORE?"


def test_meta_sections_are_never_spoken_even_without_narration_labels():
    md = VOICEOVER.replace("**Voiceover**\n", "")          # plain mode
    spoken = _spoken(md)
    for bad in ("Format", "Visual identity", "Video title", "two handbags", "Pacing", "Expensive brands can sell",
                "Visuals", "Cut to"):
        assert bad not in spoken
    assert "Imagine two plain white T-shirts." in spoken


@pytest.mark.parametrize("speech,direction", [
    ("**NARRATION:**", "**VISUAL:** A phone."),
    ("**Voice-over:**", "**On-screen text:** WHY"),
    ("**VO**", "**B-roll:** a street"),
    ("**Narrator**:", "**SFX:** ding"),
    ("### Voiceover", "**Camera:** zoom in"),
    ("VOICEOVER:", "VISUALS: a phone"),
    ("**Script:**", "[Cut to a phone screen]"),
    ("**Host:**", "(Music fades in)"),
    ("**Voiceover:**", "**Text on screen:** “WHY?”"),
])
def test_any_speech_and_direction_label_variant(speech, direction):
    md = f"# T\n\n## Part\n\n{speech}\n\nHello there friend.\n\n{direction}\n\n{speech}\n\nSecond line here.\n"
    assert _spoken(md) == "Hello there friend. Second line here."


def test_label_only_direction_line_covers_following_paragraphs_until_speech():
    md = "# T\n\n## A\n\n**Narration**\n\nSpoken one.\n\n**Visuals**\n\nA phone.\n\nCut to a shop.\n\n**Narration**\n\nSpoken two.\n"
    assert _spoken(md) == "Spoken one. Spoken two."


def test_unknown_bold_label_inside_narration_stays_spoken():
    md = "# T\n\n## A\n\n**NARRATION:**\n\n**Fun fact:** owls cannot move their eyes.\n"
    assert _spoken(md) == "Fun fact: owls cannot move their eyes."


def test_suspicious_flags_direction_like_narration():
    scenes = [{"n": 1, "text": "Hello. Cut to a phone screen. Bye."}, {"n": 2, "text": "Visuals: a shop."},
              {"n": 3, "text": "Just talking normally here."}]
    assert [n for n, _ in script.suspicious(scenes)] == [1, 2]


def test_real_expensive_brands_script_has_no_stage_directions():
    path = r"C:\YouTubeAI\Ssenariler\eli5_business_why_expensive_brands_make_people_want_them.md"
    if not os.path.isfile(path):
        pytest.skip("ssenari yoxdur")
    data = script.build(path)
    assert script.suspicious(data["scenes"]) == []
    words = sum(len(s["text"].split()) for s in data["scenes"])
    assert 2200 < words < 2300                              # yalniz **Voiceover** bloklari (awk ile sayilib: 2250)
    spoken = " ".join(s["text"] for s in data["scenes"])
    for bad in ("Voiceover", "Visuals", "On-screen text", "Pacing", "WHY PAY MORE"):
        assert bad not in spoken
