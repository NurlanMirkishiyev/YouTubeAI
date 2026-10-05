import remotion_build as rb

DATA = {
    "intro_seconds": 3.52, "outro_seconds": 6.0,
    "scenes": [
        {"section": "Hook", "duration": 7.013, "sprite": "three_q", "pos": "right", "spoken_title": None},
        {"section": "Section 1: What Is It?", "duration": 8.49, "sprite": "chart", "pos": "left",
         "spoken_title": "What Is It?"},
        {"section": "Section 1: What Is It?", "duration": 6.51, "sprite": "happy", "pos": "left",
         "spoken_title": None},
    ],
}
POSES = {"three_q": (1020, 1592), "chart": (1552, 1248), "front": (1108, 1604)}


def test_frames_follow_the_audio_clock_without_rounding_drift():
    frames = rb.cumulative_frames([1.01] * 300, fps=30)
    assert sum(frames) == round(303.0 * 30)
    assert set(frames) <= {30, 31}


def test_props_timeline_matches_narration():
    p = rb.episode_props(DATA, "What Is It?", [], POSES)
    total = p["introFrames"] + sum(s["frames"] for s in p["scenes"]) + p["outroFrames"]
    assert total == round((3.52 + 7.013 + 8.49 + 6.51 + 6.0) * 30)
    assert p["introFrames"] == round(3.52 * 30)


def test_props_titles_poses_and_motion():
    p = rb.episode_props(DATA, "What Is It?", [], POSES)
    assert [s["title"] for s in p["scenes"]] == [None, "What Is It?", None]
    assert [s["side"] for s in p["scenes"]] == ["right", "right", "right"]
    assert p["scenes"][2]["pose"] == "three_q"            # bust -> tam beden
    assert len({s["motion"] for s in p["scenes"]}) == 3
    assert p["poses"]["chart"]["flippable"] is False
    assert p["poses"]["three_q"]["flippable"] is True
    assert p["scenes"][0]["bg"] == "bg/sc01.jpg"


def test_words_are_compacted():
    words = [{"word": " Hello", "start": 0.0, "end": 0.4}, {"word": " world.", "start": 0.4, "end": 0.9}]
    assert rb.compact_words(words) == [{"w": "Hello", "s": 0.0, "e": 0.4}, {"w": "world.", "s": 0.4, "e": 0.9}]


def test_left_composed_backgrounds_are_mirrored_so_the_owl_stays_right():
    # Kohne epizodlarda fon bos yeri solda saxlayir; guzgu ile bos yer saga kecir (fonda yazi yoxdur)
    p = rb.episode_props(DATA, "What Is It?", [], POSES)
    assert [s["flip"] for s in p["scenes"]] == [False, True, True]


# Sehne bayqusu (render_owls): varsa o sehnede oz sekli, yoxdursa kohne poz; guzgulenmir (elinde esya var)
def test_scene_owls_replace_the_pose_where_they_exist():
    p = rb.episode_props(DATA, "What Is It?", [], POSES, scene_owls={2: (700, 1100)})
    assert [s["pose"] for s in p["scenes"]] == ["three_q", "sc02", "three_q"]
    assert p["poses"]["sc02"] == {"name": "sc02", "w": 700, "h": 1100, "height": rb.DEFAULT_HEIGHT,
                                  "flippable": False}


def test_subword_tokens_are_merged_into_previous_word():
    # Whisper "$39.99" -> " $39" + ".99" (no leading space) -> altyazida "$39 .99" gorunurdu
    words = [{"word": " a", "start": 0.0, "end": 0.2}, {"word": " $39", "start": 0.2, "end": 0.7},
             {"word": ".99", "start": 0.7, "end": 1.4}, {"word": " game.", "start": 1.4, "end": 1.9}]
    assert rb.compact_words(words) == [{"w": "a", "s": 0.0, "e": 0.2}, {"w": "$39.99", "s": 0.2, "e": 1.4},
                                       {"w": "game.", "s": 1.4, "e": 1.9}]


def test_chart_scene_gets_section_as_kicker_not_a_lower_third():
    """#55 (istifadeci 2026-10-05): bolme etiketi slayd basliginin ustune dusmesin."""
    data = {**DATA, "scenes": [DATA["scenes"][0], {**DATA["scenes"][1], "visual": {
        "kind": "counter", "title": "Monthly rent", "value": 4000, "unit": "$", "label": "Rent"}}]}
    p = rb.episode_props(data, "What Is It?", [], POSES)
    chart = p["scenes"][1]
    assert chart["title"] == "What Is It?"           # bolme kecidi (slide) qalir
    assert chart["lowerThird"] is False and chart["kicker"] == "What Is It?"
    photo = rb.episode_props(DATA, "What Is It?", [], POSES)["scenes"][1]
    assert photo["lowerThird"] is True and photo["kicker"] is None


def test_caption_words_prefer_script_captions(tmp_path):
    """#54: Remotion altyazisi ssenaridən (captions.words.json), yoxdursa whisper."""
    (tmp_path / "narration.words.json").write_text('[{"word": " whisper", "start": 0, "end": 1}]', encoding="utf-8")
    assert rb.load_words(str(tmp_path))[0]["word"] == " whisper"
    (tmp_path / "captions.words.json").write_text('[{"word": " $4,000", "start": 0, "end": 1}]', encoding="utf-8")
    assert rb.load_words(str(tmp_path))[0]["word"] == " $4,000"


def test_intro_card_shows_the_hook_line():
    """#56: ilk 3 saniyede konkret reqem/paradoks - giris karti hook cumlesini seslendirir ve gosterir."""
    data = {**DATA, "card_texts": {"intro": "A $9.99 price can earn less than $10.", "outro": "Bye."}}
    assert rb.episode_props(data, "What Is It?", [], POSES)["hook"] == "A $9.99 price can earn less than $10."
    assert rb.episode_props(DATA, "What Is It?", [], POSES)["hook"] is None


def test_stats_cards_reveal_when_each_figure_is_spoken():
    v = {"kind": "stats", "title": "Monthly costs", "cards": [{"value": 4000, "label": "Rent", "unit": "$"},
                                                             {"value": 12, "label": "Margin", "unit": "%"}]}
    assert [e["value"] for e in rb.visual_elements(v)] == [4000, 12]
    words = [{"w": w, "s": 1.0 + 0.5 * k, "e": 1.4 + 0.5 * k}
             for k, w in enumerate("Rosa pays $4,000 in rent and keeps a 12% margin.".split())]
    rev = rb.reveal_frames(v, words, 1.0, 200)
    assert rev[1] > rev[0]
