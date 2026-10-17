import json

import plan

TEXT = "Only 2% of users pay. Twenty thousand people pay five dollars each."


def test_forty_percent_animation_spread_evenly():
    t = plan.assign_types(10)
    assert t.count("anim") == 4 and t.count("photo") == 6
    assert "anim anim" not in " ".join(t)


def test_no_same_kind_twice_and_cap_25_percent():
    counts = {}
    a = plan.pick_anim([{"kind": "percent", "value": 2, "label": "users pay"}], TEXT, None, counts, 8, 0)
    assert a["kind"] == "percent"
    counts["percent"] = 1
    b = plan.pick_anim([{"kind": "percent", "value": 2, "label": "users pay"},
                        {"kind": "counter", "value": 20000, "prefix": "", "suffix": "", "label": "people pay"}],
                       TEXT, "percent", counts, 8, 1)
    assert b["kind"] == "counter" and b["variant"] == 1
    counts = {"counter": 2}
    c = plan.pick_anim([{"kind": "counter", "value": 5, "prefix": "$", "suffix": "", "label": "each"}],
                       TEXT, None, counts, 8, 0)
    assert c["kind"] == "quote"


def test_invented_content_becomes_a_quote():
    a = plan.pick_anim([{"kind": "counter", "value": 999, "label": "users"}], TEXT, None, {}, 8, 0)
    assert a["kind"] == "quote" and a["text"] in TEXT


def _data(n):
    return {"title": "T", "slug": "t", "scenes": [
        {"n": i + 1, "section": "S", "section_start": i == 0, "visual": "A phone on a desk.", "text": TEXT,
         "type": None, "photo_prompt": "", "owl": "", "anim": None, "duration": 0.0} for i in range(n)]}


def test_plan_fills_every_scene_from_gpt():
    def ask(system, user):
        nums = [int(x) for x in user.split("SCENE ")[1:] for x in [x.split(":")[0]]]
        return {"scenes": [{"n": n, "photo_prompt": f"photo {n}", "owl": f"owl {n}",
                            "anim": [{"kind": "percent", "value": 2, "label": "users pay"}]} for n in nums]}
    got = plan.plan_scenes(_data(5), ask=ask)["scenes"]
    assert [s["type"] for s in got] == plan.assign_types(5)
    assert all(s["photo_prompt"] and s["owl"] for s in got)
    assert all((s["anim"] is not None) == (s["type"] == "anim") for s in got)


def test_gpt_failure_never_stops_the_plan():
    def boom(system, user):
        raise RuntimeError("down")
    got = plan.plan_scenes(_data(5), ask=boom)["scenes"]
    assert all(s["photo_prompt"].startswith("A phone on a desk.") for s in got)
    assert len({plan.norm(s["photo_prompt"]) for s in got}) == 5 and len({plan.norm(s["owl"]) for s in got}) == 5
    assert all(s["anim"]["kind"] == "quote" for s in got if s["type"] == "anim")


def test_malformed_item_is_skipped_rest_kept():
    def ask(system, user):
        return {"scenes": [{"n": "x", "photo_prompt": "bad"}, {"n": 2, "photo_prompt": "photo 2", "owl": "o"}]}
    got = plan.plan_scenes(_data(3), ask=ask)["scenes"]
    assert got[1]["photo_prompt"] == "photo 2"


def test_animation_kinds_vary_scene_to_scene():
    allk = [{"kind": "counter", "value": 2, "prefix": "", "suffix": "%", "label": "users"},
            {"kind": "bars", "items": [{"label": "users", "value": 2}, {"label": "people", "value": 20000}]},
            {"kind": "percent", "value": 2, "label": "users pay"},
            {"kind": "flow", "steps": ["users pay", "people pay"]},
            {"kind": "list", "items": ["users pay", "people pay"]},
            {"kind": "versus", "left": "users", "right": "people"},
            {"kind": "timeline", "events": ["users pay", "people pay"]}]

    def ask(system, user):
        nums = [int(x.split(":")[0]) for x in user.split("SCENE ")[1:]]
        return {"scenes": [{"n": n, "photo_prompt": "p", "owl": "o", "anim": allk} for n in nums]}
    got = plan.plan_scenes(_data(20), ask=ask)["scenes"]
    kinds = [s["anim"]["kind"] for s in got if s["anim"]]
    assert len(set(kinds)) >= 5
    assert max(kinds.count(k) for k in set(kinds)) <= len(kinds) * 0.25
    assert all(a != b for a, b in zip(kinds, kinds[1:]))


def test_empty_balance_in_plan_is_not_swallowed():
    import llm
    import pytest

    def ask(system, user):
        raise llm.LLMError("OpenAI balansi bitib: x")
    with pytest.raises(llm.LLMError):
        plan.plan_scenes(_data(3), ask=ask)


def test_other_gpt_errors_still_fall_back_to_visual():
    def ask(system, user):
        raise RuntimeError("timeout")
    got = plan.plan_scenes(_data(3), ask=ask)["scenes"]
    assert got[0]["photo_prompt"].startswith("A phone on a desk.")


def test_quote_is_not_repeated_when_a_capped_kind_fits():
    counts = {"percent": 2}
    a = plan.pick_anim([{"kind": "percent", "value": 2, "label": "users pay"}], TEXT, "quote", counts, 8, 0)
    assert a["kind"] == "percent"


def _walk(node):
    yield node
    for v in node.values() if isinstance(node, dict) else []:
        for x in (v if isinstance(v, list) else [v]):
            if isinstance(x, dict):
                yield from _walk(x)


def test_plan_schema_is_strict_and_covers_every_animation_kind():
    anim = plan.SCHEMA["properties"]["scenes"]["items"]["properties"]["anim"]["items"]["anyOf"]
    kinds = {a["properties"]["kind"]["enum"][0] for a in anim}
    assert kinds == set(plan.ROTATION)
    for node in _walk(plan.SCHEMA):
        if node.get("type") == "object":
            assert node["additionalProperties"] is False and set(node["required"]) == set(node["properties"])


def test_failed_gpt_batch_is_retried_before_falling_back():
    calls = {"n": 0}

    def ask(system, user):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("gozlenilmeyen chat cavabi")
        return {"scenes": [{"n": 1, "photo_prompt": "photo one", "owl": "o", "anim": []}]}
    got = plan.plan_scenes(_data(1), ask=ask)["scenes"]
    assert got[0]["photo_prompt"] == "photo one" and calls["n"] == 2


def test_rejected_animation_scenes_get_a_second_gpt_pass_with_the_reason():
    users = []

    def ask(system, user):
        users.append(user)
        nums = [int(x.split(":")[0]) for x in user.split("SCENE ")[1:]]
        good = len(users) > 1
        anim = ([{"kind": "flow", "steps": ["users pay", "people pay"]}] if good
                else [{"kind": "flow", "steps": ["Invented words here", "More invention"]}])
        return {"scenes": [{"n": n, "photo_prompt": "p", "owl": "o", "anim": anim} for n in nums]}
    got = plan.plan_scenes(_data(3), ask=ask)["scenes"]
    anims = [s["anim"] for s in got if s["anim"]]
    assert anims and all(a["kind"] == "flow" for a in anims)
    assert any("REJECTED" in u and "Invented" in u for u in users)


def test_enumeration_is_used_before_a_quote():
    text = "It might show ads, offer paid features, or sell subscriptions."
    a = plan.pick_anim([], text, None, {}, 8, 0)
    assert a["kind"] == "list" and a["items"] == ["show ads", "offer paid features", "sell subscriptions"]


def test_photo_prompt_never_shows_the_owl_mascot():
    assert plan.photo_safe("The owl watches a video on a laptop.") == "A person watches a video on a laptop."
    assert plan.photo_safe("A split screen showing the owl mascot using a free app.") == \
        "A split screen showing a person using a free app."
    assert "owl" not in plan.photo_safe("An owl putting down a phone.").lower()


def test_planned_photo_prompts_are_owl_free():
    def ask(system, user):
        nums = [int(x.split(":")[0]) for x in user.split("SCENE ")[1:]]
        return {"scenes": [{"n": n, "photo_prompt": "The owl taps a phone", "owl": "o", "anim": []} for n in nums]}
    got = plan.plan_scenes(_data(3), ask=ask)["scenes"]
    assert all("owl" not in s["photo_prompt"].lower() for s in got)


def _content(scenes):
    return [s for s in scenes if s["type"] in ("photo", "anim")]


def test_missing_scenes_are_asked_again():
    calls = []

    def ask(system, user):
        nums = [int(x.split(":")[0]) for x in user.split("SCENE ")[1:]]
        calls.append(nums)
        keep = nums if len(calls) > 1 else nums[:1]          # first call drops scenes
        return {"scenes": [{"n": n, "photo_prompt": f"photo {n}", "owl": f"pose {n}", "anim": []} for n in keep]}
    got = _content(plan.plan_scenes(_data(3), ask=ask)["scenes"])
    assert [s["photo_prompt"] for s in got] == ["photo 1", "photo 2", "photo 3"]
    assert [s["owl"] for s in got] == ["pose 1", "pose 2", "pose 3"]


def test_duplicate_prompts_and_poses_are_repaired_by_gpt():
    def ask(system, user):
        nums = [int(x.split(":")[0]) for x in user.split("SCENE ")[1:]]
        fix = "DUPLICATE" in user
        return {"scenes": [{"n": n, "photo_prompt": f"new photo {n}" if fix else "same photo",
                            "owl": f"new pose {n}" if fix else "same pose", "anim": []} for n in nums]}
    got = _content(plan.plan_scenes(_data(4), ask=ask)["scenes"])
    assert len({plan.norm(s["photo_prompt"]) for s in got}) == 4
    assert len({plan.norm(s["owl"]) for s in got}) == 4


def test_already_used_prompts_are_shown_to_later_batches():
    users = []

    def ask(system, user):
        users.append(user)
        nums = [int(x.split(":")[0]) for x in user.split("SCENE ")[1:]]
        return {"scenes": [{"n": n, "photo_prompt": f"photo {n}", "owl": f"pose {n}", "anim": []} for n in nums]}
    plan.plan_scenes(_data(4), ask=ask, batch=2)
    assert "ALREADY USED" in users[1] and "photo 1" in users[1]


def test_unique_guard_makes_leftovers_unique():
    scenes = [{"n": i, "type": "photo", "visual": "A phone.", "text": "Same sentence. More.",
               "photo_prompt": "x", "owl": "y"} for i in (1, 2, 3)]
    plan.unique_guard(scenes)
    assert len({plan.norm(s["photo_prompt"]) for s in scenes}) == 3
    assert len({plan.norm(s["owl"]) for s in scenes}) == 3
    assert all("owl" not in s["photo_prompt"].lower() for s in scenes)


BOOK = {"greeting": "Hi friends, welcome to ELI5 Business! Today: how free apps make money.",
        "farewell": "Thanks for watching! If this helped, subscribe and hit the bell for more simple business stories.",
        "bg_prompt": "Smartphones with colorful apps on a wooden desk", "owl_intro": "waving hello holding a phone",
        "owl_outro": "waving goodbye and pointing to a subscribe button"}


def test_intro_and_outro_wrap_the_planned_scenes():
    data = plan.plan_scenes(_data(5), ask=lambda s, u: {"scenes": []})
    got = plan.add_bookends(data, ask=lambda s, u: dict(BOOK))["scenes"]
    assert got[0]["type"] == "intro" and got[0]["n"] == 0 and got[0]["text"] == BOOK["greeting"]
    assert got[-1]["type"] == "outro" and got[-1]["n"] == 6 and got[-1]["text"] == BOOK["farewell"]
    assert got[0]["photo_prompt"] == got[-1]["photo_prompt"] == BOOK["bg_prompt"]
    assert got[0]["owl"] == BOOK["owl_intro"] and got[-1]["owl"] == BOOK["owl_outro"]
    assert got[0]["section"] == "" and got[0]["section_start"] is False and got[0]["anim"] is None
    assert [s["type"] for s in got[1:-1]] == plan.assign_types(5)


def test_add_bookends_is_idempotent():
    data = plan.add_bookends(plan.plan_scenes(_data(2), ask=lambda s, u: {"scenes": []}), ask=lambda s, u: dict(BOOK))
    again = plan.add_bookends(data, ask=lambda s, u: (_ for _ in ()).throw(AssertionError("no second call")))
    assert [s["type"] for s in again["scenes"]].count("intro") == 1


def test_bookend_prompt_gets_the_title_and_opening_narration():
    seen = []
    plan.bookends("How Free Apps Make Billions", ["Imagine an app you use every day."],
                  ask=lambda s, u: seen.append((s, u)) or dict(BOOK))
    assert "How Free Apps Make Billions" in seen[0][1] and "Imagine an app" in seen[0][1]
    assert "ELI5 Business" in seen[0][0]


def test_overlong_texts_are_retried_then_capped():
    calls = []
    long = "Hello there friend. " + "word " * 40

    def ask(system, user):
        calls.append(user)
        return {**BOOK, "greeting": long, "farewell": "Bye now. " + "more " * 40}
    b = plan.bookends("T", ["x"], ask)
    assert len(calls) == 2 and "TOO LONG" in calls[1]
    assert len(b["greeting"].split()) <= plan.GREETING_MAX and b["greeting"] == "Hello there friend."
    assert len(b["farewell"].split()) <= plan.FAREWELL_MAX and "subscribe" in b["farewell"].lower()


def test_bookend_photo_never_shows_the_owl():
    b = plan.bookends("T", ["x"], lambda s, u: {**BOOK, "bg_prompt": "The owl mascot at a desk with phones"})
    assert "owl" not in b["bg_prompt"].lower()


def test_bookend_gpt_failure_raises_after_one_retry():
    import pytest
    n = {"n": 0}

    def ask(system, user):
        n["n"] += 1
        raise RuntimeError("down")
    with pytest.raises(RuntimeError):
        plan.bookends("T", ["x"], ask)
    assert n["n"] == 2


def test_theme_is_picked_once_from_the_known_palettes(tmp_path):
    hist = str(tmp_path / "themes.json")
    data = {"slug": "lux", "title": "Why Luxury Brands Win", "scenes": [{"n": 1, "text": "Luxury bags cost more."}]}
    got = plan.with_theme(data, ask=lambda s, u, a: {"theme": "gold"}, path=hist)
    assert got["theme"] == "gold"
    no_call = lambda s, u, a: (_ for _ in ()).throw(AssertionError("no call"))  # noqa: E731
    assert plan.with_theme(got, ask=no_call, path=hist)["theme"] == "gold"
    assert plan.with_theme({**data, "theme": None}, ask=no_call, path=hist)["theme"] == "gold"   # resume


def test_unknown_or_failed_theme_uses_an_unused_palette(tmp_path):
    hist = str(tmp_path / "themes.json")
    data = {"slug": "a", "title": "T", "scenes": [{"n": 1, "text": "x"}]}
    assert plan.with_theme(data, ask=lambda s, u, a: {"theme": "neon-pink"}, path=hist)["theme"] == plan.THEMES[0]

    def boom(s, u, a):
        raise RuntimeError("down")
    assert plan.with_theme({**data, "slug": "b"}, ask=boom, path=hist)["theme"] == plan.THEMES[1]


def test_theme_does_not_repeat_until_every_palette_is_used(tmp_path):
    hist = str(tmp_path / "themes.json")
    offered = []

    def tech(system, user, allowed):
        offered.append(allowed)
        assert all(t in system for t in allowed)
        return {"theme": "electric"}          # GPT her defe ayni temani isteyir
    got = [plan.with_theme({"slug": f"v{i}", "title": "AI", "scenes": [{"n": 1, "text": "x"}]}, ask=tech,
                           path=hist)["theme"] for i in range(len(plan.THEMES) + 1)]
    assert got[0] == "electric" and "electric" not in offered[1]
    assert sorted(got[:len(plan.THEMES)]) == sorted(plan.THEMES)       # 12 video = 12 ferqli tema
    assert got[-1] != got[-2]                                           # yeni dovr: son tema tekrar olmur
    with open(hist, encoding="utf-8") as f:
        assert list(json.load(f)) == [f"v{i}" for i in range(len(plan.THEMES) + 1)]


def test_every_anim_schema_asks_for_an_icon():
    for sch in plan.ANIM_SCHEMAS:
        assert "icon" in sch["properties"] and sch["properties"]["icon"]["enum"] == list(plan.grounding.ICONS)
