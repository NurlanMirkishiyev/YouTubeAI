import scene_plan


def test_positions_alternate_by_section_and_never_center():
    scenes = [{"section": s} for s in ("Hook", "Hook", "Section 1: A", "Section 2: B", "Call to Action")]
    assert scene_plan.assign_positions(scenes) == ["right", "right", "left", "right", "left"]
