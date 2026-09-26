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
