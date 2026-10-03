"""Reyestr #45 (2026-10-03): sehnelerin ~60%-i analitik animasiya. Chart-daki her reqem sehne danisiginda
olmalidir (hesab sehvi QETI olmur) - olmasa reqemsiz keypoints-e, o da alinmasa fotoya dusur."""
from visuals import ANIM_SHARE, choose_animated, plan_visuals, to_keypoints, validate_visual

NARR = "A $10 lunch drops to $9.99 and sales jump 40% in three months."


def test_bars_with_spoken_numbers_pass():
    v = {"kind": "bars", "title": "Same lunch, new price", "unit": "$",
         "items": [{"label": "Before", "value": 10}, {"label": "After", "value": 9.99}]}
    out = validate_visual(v, NARR)
    assert out["kind"] == "bars" and [i["value"] for i in out["items"]] == [10, 9.99]


def test_number_not_in_narration_is_rejected():
    v = {"kind": "bars", "title": "Sales", "unit": "%",
         "items": [{"label": "Before", "value": 100}, {"label": "After", "value": 140}]}
    assert validate_visual(v, NARR) is None


def test_digits_inside_labels_must_be_spoken():
    v = {"kind": "flow", "title": "Pricing steps", "steps": ["Set price", "Wait 6 weeks", "Measure"]}
    assert validate_visual(v, NARR) is None
    v["steps"][1] = "Wait three months"
    assert validate_visual(v, NARR) is not None


def test_ring_must_be_a_spoken_percentage_between_0_and_100():
    assert validate_visual({"kind": "ring", "title": "Sales jump", "value": 40, "label": "more sales"}, NARR)
    assert validate_visual({"kind": "ring", "title": "Sales", "value": 140, "label": "x"}, NARR) is None
    assert validate_visual({"kind": "ring", "title": "Sales", "value": 9.99, "label": "x"}, NARR) is None


def test_equation_arithmetic_is_checked():
    narr = "Revenue of $500 minus costs of $300 leaves $200 profit."
    ok = {"kind": "equation", "title": "Profit", "op": "-",
          "terms": [{"label": "Revenue", "value": 500}, {"label": "Costs", "value": 300}],
          "result": {"label": "Profit", "value": 200}}
    assert validate_visual(ok, narr)
    bad = {**ok, "op": "+"}
    assert validate_visual(bad, narr) is None


def test_equation_without_values_is_allowed():
    v = {"kind": "equation", "title": "Profit", "op": "-",
         "terms": [{"label": "Revenue"}, {"label": "Costs"}], "result": {"label": "Profit"}}
    assert validate_visual(v, "Profit is what is left after costs.")


def test_unknown_kind_and_long_text_are_rejected():
    assert validate_visual({"kind": "pie3d", "title": "x"}, NARR) is None
    v = {"kind": "keypoints", "title": "T", "points": ["a" * 60, "b"]}
    assert validate_visual(v, NARR) is None


def test_keypoints_fallback_drops_numbers():
    v = {"kind": "bars", "title": "Sales", "points": ["Charm prices", "Left digit wins", "Costs 7 cents"]}
    out = to_keypoints(v, NARR)
    assert out["kind"] == "keypoints" and out["points"] == ["Charm prices", "Left digit wins"]
    assert to_keypoints({"kind": "bars", "title": "x", "points": ["only one"]}, NARR) is None


def test_choose_animated_takes_share_and_keeps_first_scene_photo():
    scores = [9, 8, 7, 6, 5, 4, 3, 2, 1, 0.5]
    picked = choose_animated(scores, 0.6)
    assert len(picked) == 6 and 0 not in picked


def test_choose_animated_never_runs_more_than_three_in_a_row():
    picked = choose_animated([1] + [9] * 9, 0.9)
    run = best = 0
    for i in range(10):
        run = run + 1 if i in picked else 0
        best = max(best, run)
    assert best <= 3


def test_choose_animated_skips_scenes_without_valid_visual():
    assert choose_animated([5, -1, -1, 8], 0.6) == {3}


def test_plan_visuals_validates_llm_output_and_falls_back():
    scenes = [{"section": "S", "narration": "Intro words here about prices."},
              {"section": "S", "narration": NARR},
              {"section": "S", "narration": "Costs and fees add up over time for a shop."}]

    def fake_chat(system, user, **kw):
        return {"scenes": [
            {"n": 1, "score": 1, "visual": {"kind": "keypoints", "title": "Hi", "points": ["a", "b"]}},
            {"n": 2, "score": 9, "visual": {"kind": "ring", "title": "Sales jump", "value": 40, "label": "sales"}},
            {"n": 3, "score": 8, "visual": {"kind": "bars", "title": "Fees", "unit": "$",
                                             "items": [{"label": "A", "value": 70}, {"label": "B", "value": 90}]},
             "points": ["Fees add up", "Costs grow"]}]}

    out = plan_visuals(scenes, "Why prices", chat=fake_chat, share=ANIM_SHARE)
    assert out[0] is None                       # ilk sehne foto
    assert out[1]["kind"] == "ring"
    assert out[2]["kind"] == "keypoints"        # 70/90 danisiqda yoxdur -> reqemsiz


def test_plan_visuals_survives_llm_error():
    from llm import LLMError

    def broken(*a, **k):
        raise LLMError("down")

    assert plan_visuals([{"section": "S", "narration": NARR}] * 3, "t", chat=broken) == [None] * 3


# --- scene_plan / stages inteqrasiyasi ---------------------------------------------------------

def _same_cookie_llm(monkeypatch):
    import re as _re

    import scene_plan
    monkeypatch.setattr(scene_plan, "chat_json", lambda system, user, **kw: {"scenes": [
        {"n": int(n), "subject": "cookie", "bg_prompt": "a single cookie on a wooden table next to a plate",
         "sprite": "front", "owl_action": "pointing, curious"}
        for n in _re.findall(r"(?m)^(\d+)\. \[", user)]})


def test_animated_scenes_get_no_photo_prompt(monkeypatch):
    import scene_plan
    _same_cookie_llm(monkeypatch)
    spec = {"kind": "keypoints", "title": "T", "points": ["a", "b"]}
    scenes = [{"narration": f"line {k} about prices", "section": "S"} for k in range(4)]
    out = scene_plan.plan(scenes, list(scene_plan.VIDEO_POSES), visuals=[None, spec, spec, None])
    assert [s["bg_prompt"] == "" for s in out] == [False, True, True, False]
    assert out[1]["visual"] == spec and out[0]["visual"] is None
    photos = [s["bg_prompt"] for s in out if s["bg_prompt"]]
    assert len(set(photos)) == len(photos) == 2
    assert all(s["owl_action"] for s in out)          # bayqus her sehnede qalir


def test_verify_scenes_accepts_photo_or_animation(tmp_path):
    import json

    import stages as st
    scenes = [{"narration": "a", "bg_prompt": "a lamp on a desk in light", "sprite_token": "front@right"},
              {"narration": "b", "bg_prompt": "", "visual": {"kind": "keypoints"}, "sprite_token": "front@right"},
              {"narration": "c", "bg_prompt": "", "visual": None, "sprite_token": "front@right"}]
    (tmp_path / "scenes.json").write_text(json.dumps({"scenes": scenes}), encoding="utf-8")
    ctx = st.Ctx("t", "t", str(tmp_path), 100, None, 600, 720, "openai")
    assert st.verify_scenes(ctx) == ["natamam sehneler: [3]"]
    assert st.photo_numbers(ctx) == [1, 3]
    assert [p[-8:] for p in st.photo_files(ctx, "bg")] == ["sc01.png", "sc03.png"]
    assert len(st.numbered(ctx, "audio", ".wav")) == 3          # ses her sehne ucun qalir


# --- foto merheleleri animasiya sehnelerini otur -----------------------------------------------

def test_prune_removes_old_photos_of_animated_scenes(tmp_path):
    import render_bgs as rb
    for n in (1, 2, 3):
        (tmp_path / f"sc{n:02d}.png").write_bytes(b"x")
    rb.prune_extra(str(tmp_path), 3, animated={2})
    assert sorted(p.name for p in tmp_path.iterdir()) == ["sc01.png", "sc03.png"]


def test_check_bgs_judges_only_photo_scenes():
    import check_bgs as cb
    scenes = [{"bg_prompt": "a lamp"}, {"bg_prompt": "", "visual": {"kind": "flow"}}, {"bg_prompt": "a cup"}]
    assert cb.photo_scene_numbers(scenes) == [1, 3]


def test_remotion_props_carry_the_visual_and_no_photo():
    import remotion_build as rb
    spec = {"kind": "ring", "title": "Sales", "value": 40, "label": "more"}
    data = {"intro_seconds": 3.0, "outro_seconds": 5.0, "scenes": [
        {"duration": 6.0, "sprite": "front", "pos": "right", "spoken_title": None},
        {"duration": 6.0, "sprite": "front", "pos": "right", "spoken_title": None, "visual": spec,
         "narration": "Sales jump 40% fast."}]}
    p = rb.episode_props(data, "T", [], {"front": (100, 200), "three_q": (100, 200)})
    assert p["scenes"][0]["bg"] == "bg/sc01.jpg" and p["scenes"][0]["visual"] is None
    assert p["scenes"][1]["bg"] is None and p["scenes"][1]["visual"]["kind"] == "ring"


def test_prepare_public_skips_animated_scenes(tmp_path, monkeypatch):
    from PIL import Image

    import remotion_build as rb
    ep = tmp_path / "ep"
    (ep / "bg").mkdir(parents=True)
    Image.new("RGB", (64, 36)).save(ep / "bg" / "sc01.png")
    (ep / "narration.wav").write_bytes(b"x")
    monkeypatch.setattr(rb, "SPRITE_DIR", str(tmp_path / "spr"))
    monkeypatch.setattr(rb, "FONTS_DIR", str(tmp_path))
    (tmp_path / "spr").mkdir()
    for name in rb.VIDEO_POSES:
        Image.new("RGBA", (8, 8)).save(tmp_path / "spr" / f"{name}.png")
    monkeypatch.setattr(rb, "BG_SIZE", (64, 36))
    pub = rb.prepare_public(str(ep), 2, animated={2})
    assert sorted(p.name for p in (tmp_path / "ep" / "remotion" / "bg").iterdir()) == ["sc01.jpg"]
    assert pub.endswith("remotion")


# --- reveal: element reqemi/etiketi seslenende acilir ---------------------------------------------

def _w(text, t0, step=0.4):
    return [{"w": w, "s": round(t0 + k * step, 2), "e": round(t0 + k * step + 0.3, 2)}
            for k, w in enumerate(text.split())]


def test_reveal_follows_the_spoken_numbers():
    import remotion_build as rb
    v = {"kind": "bars", "items": [{"label": "Before", "value": 10}, {"label": "After", "value": 9.99}]}
    words = _w("So here is the deal: a $10 lunch drops to $9.99 today and more words follow", 20.0)
    r = rb.reveal_frames(v, words, start_s=20.0, frames=300)
    assert r[0] == round(2.4 * 30) - rb.REVEAL_LEAD           # "$10" 22.4 s-de
    assert r[1] == round(4.0 * 30) - rb.REVEAL_LEAD           # "$9.99" 24.0 s-de


def test_reveal_falls_back_to_even_steps_and_stays_ordered():
    import remotion_build as rb
    v = {"kind": "flow", "steps": ["Plan", "Build", "Ship"]}
    r = rb.reveal_frames(v, _w("nothing matches in this narration at all", 5.0), start_s=5.0, frames=240)
    assert r == sorted(r) and len(r) == 3 and r[0] >= rb.REVEAL_MIN and r[-1] <= 240 - rb.REVEAL_TAIL


def test_reveal_counts_elements_per_kind():
    import remotion_build as rb
    eq = {"kind": "equation", "terms": [{"label": "Revenue"}, {"label": "Costs"}], "result": {"label": "Profit"}}
    assert len(rb.reveal_frames(eq, [], 0.0, 300)) == 3
    assert len(rb.reveal_frames({"kind": "ring", "value": 40}, [], 0.0, 300)) == 1
    assert len(rb.reveal_frames({"kind": "compare", "left": {"label": "A"}, "right": {"label": "B"}}, [], 0.0, 300)) == 2


def test_props_include_reveal_for_animated_scenes():
    import remotion_build as rb
    spec = {"kind": "ring", "title": "Sales", "value": 40, "label": "more"}
    data = {"intro_seconds": 3.0, "outro_seconds": 5.0, "scenes": [
        {"duration": 6.0, "sprite": "front", "pos": "right", "spoken_title": None, "visual": spec}]}
    words = [{"word": " Sales", "start": 3.2, "end": 3.5}, {"word": " jump", "start": 3.5, "end": 3.8},
             {"word": " 40%", "start": 4.0, "end": 4.4}]
    p = rb.episode_props(data, "T", words, {"front": (100, 200), "three_q": (100, 200)})
    assert p["scenes"][0]["reveal"] == [30 - rb.REVEAL_LEAD]
