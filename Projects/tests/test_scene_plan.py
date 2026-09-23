import scene_plan


def test_positions_alternate_by_section_and_never_center():
    scenes = [{"section": s} for s in ("Hook", "Hook", "Section 1: A", "Section 2: B", "Call to Action")]
    assert scene_plan.assign_positions(scenes) == ["right", "right", "left", "right", "left"]


def test_clean_bg_prompt_drops_text_bearing_items():
    p = ("a game store with a sign saying 'New Releases', a shopping cart at the checkout, "
         "a scoreboard showing points, a credit card on the counter, a pie chart, a checklist")
    out = scene_plan.clean_bg_prompt(p)
    assert out == "a shopping cart at the checkout, a credit card on the counter"


def test_clean_bg_prompt_keeps_setting_when_everything_is_text():
    out = scene_plan.clean_bg_prompt("a financial dashboard showing credit limits, a graph")
    assert out and "'" not in out and "dashboard" not in out


def test_clean_bg_prompt_drops_dangling_fragments():
    out = scene_plan.clean_bg_prompt("a scoreboard showing limits and spending, with a credit card beside it")
    assert out == "a credit card beside it"
