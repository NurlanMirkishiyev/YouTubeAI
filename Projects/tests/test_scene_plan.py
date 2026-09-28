import scene_plan


def test_owl_stays_on_one_side_for_the_whole_episode():
    # Istifadeci 2026-09-27: personaj sabit dayansin - bolme deyisende sag/sol tullanmasin
    scenes = [{"section": s} for s in ("Hook", "Hook", "Section 1: A", "Section 2: B", "Call to Action")]
    assert scene_plan.assign_positions(scenes) == ["right"] * 5


def test_clean_bg_prompt_drops_text_bearing_items():
    p = ("a game store with a sign saying 'New Releases', a shopping cart at the checkout, "
         "a scoreboard showing points, a credit card on the counter, a pie chart, a checklist")
    out = scene_plan.clean_bg_prompt(p)
    assert out == f"a shopping cart at the checkout, a {scene_plan.BLANK_CARD} on the counter"


def test_clean_bg_prompt_keeps_setting_when_everything_is_text():
    out = scene_plan.clean_bg_prompt("a financial dashboard showing credit limits, a graph")
    assert out and "'" not in out and "dashboard" not in out


def test_clean_bg_prompt_drops_dangling_fragments():
    out = scene_plan.clean_bg_prompt("a scoreboard showing limits and spending, with a credit card beside it")
    assert out == f"a {scene_plan.BLANK_CARD}"


# FAZA F E2E (how-credit-cards): eyni seed ile yoxlanildi - guclu negativ prompt gibberish-i
# aradan qaldirmir, yaziyi obyektin adi getirir (kart, teqvim, pizza qutusu, kalkulyator).
def test_clean_bg_prompt_swaps_payment_cards_for_blank_card():
    out = scene_plan.clean_bg_prompt("a credit card, a debit card on a desk")
    assert "credit" not in out and "debit" not in out
    assert out == f"a {scene_plan.BLANK_CARD}, a {scene_plan.BLANK_CARD} on a desk"


def test_clean_bg_prompt_drops_objects_that_carry_print():
    p = ("a calendar indicating due dates, a calculator on a table, a stack of bills, "
         "a newspaper, a piggy bank")
    assert scene_plan.clean_bg_prompt(p) == "a piggy bank"


def test_clean_bg_prompt_strips_abstract_participle_tails():
    p = "a wallet showing balance, a clock showing time passing, a piggy bank indicating savings"
    assert scene_plan.clean_bg_prompt(p) == "a wallet, a clock, a piggy bank"


def test_clean_bg_prompt_drops_card_readers_instead_of_mangling_them():
    out = scene_plan.clean_bg_prompt("a counter with a credit card reader, a vase on the counter")
    assert out == "a vase on the counter"


# E2E what-is-business-automation sc35: "a basketball player" negativ promptdaki "person, boy"-a
# baxmayaraq cizgi oglan cekdi - insan ismi ozu insani getirir. Robot personaj movzuya aiddir, qalir.
def test_clean_bg_prompt_drops_human_nouns_but_keeps_robots():
    p = ("a basketball player practicing with a shooting machine, a basketball hoop, "
         "a robot chef stirring soup, a customer at the counter, the chef chops vegetables")
    assert scene_plan.clean_bg_prompt(p) == "a basketball hoop, a robot chef stirring soup"


# E2E how-ai-agents-change-automation: sc48 "an athlete" cizgi oglan, sc02 "a pair of hands" insan eli cekdi
def test_clean_bg_prompt_drops_athletes_and_hands():
    p = ("a robot guiding an athlete in training, a running track, "
         "a robotic arm tossing three balls to a pair of hands, a robot coach with a whistle")
    assert scene_plan.clean_bg_prompt(p) == "a running track, a robot coach with a whistle"


def test_clean_bg_prompt_turns_pizza_box_into_tray():
    out = scene_plan.clean_bg_prompt("an empty pizza box on a table")
    assert out == "an empty pizza tray on a table"


# Istifadeci: "sekiller oxsar ve tekrardir", "personaj eyni formada". E2E business-automation:
# 40 sehnenin 32-si three_q, 8 sehne eyni FALLBACK_BG, sehne ~20 s bir sekil.
def test_split_scenes_makes_short_shots():
    md = "## Hook\n\n" + " ".join(f"Sentence number {i} has exactly seven words." for i in range(12))
    scenes = scene_plan.split_scenes(md)
    assert len(scenes) >= 3
    assert all(len(s["narration"].split()) <= scene_plan.MAX_WORDS for s in scenes)


def test_video_poses_are_full_body_only():
    assert set(scene_plan.VIDEO_POSES) == {"front", "three_q", "side", "box", "chart"}


def test_poses_follow_the_scene_even_when_repeated():
    # Poz sehnenin mezmununa uygun secilir; zorla novbelesdirme uygun pozu pozurdu
    out = scene_plan.fit_poses(["chart", "chart", "box", "happy", ""])
    assert out == ["chart", "chart", "box", "three_q", "three_q"]


def test_pose_prompt_asks_for_a_fitting_pose_not_a_change():
    assert "Change the pose" not in scene_plan.USER
    assert "fits" in scene_plan.USER


def test_clean_bg_prompt_keeps_at_most_three_parts():
    p = "a kitchen counter, a robot arm, a soup pot, a spoon, a bowl of salad"
    assert scene_plan.clean_bg_prompt(p) == "a kitchen counter, a robot arm, a soup pot"


def test_repeats_flags_fallback_and_recent_same_subject():
    subjects = ["robot chef", "slow cooker", "robot chef", "watering can", "slow cooker"]
    prompts = [f"a shiny {n} on a wooden table" for n in ("kettle", "lamp", "vase", "clock", "globe")]
    prompts[2] = scene_plan.FALLBACK_BG
    assert scene_plan.repeats(prompts, subjects, window=3) == [2, 4]


def test_fallbacks_are_never_reused():
    got = [scene_plan.fallback_bg(k) for k in range(len(scene_plan.FALLBACK_POOL))]
    assert len(set(got)) == len(got)


def test_align_maps_partial_llm_answer_by_scene_number():
    items = [{"n": 7, "subject": "b"}, {"n": 5, "subject": "a"}]
    out = scene_plan.align(items, [5, 6, 7])
    assert [it.get("subject") for it in out] == ["a", None, "b"]


def test_align_falls_back_to_order_when_numbers_missing():
    out = scene_plan.align([{"subject": "a"}, {"subject": "b"}], [3, 4])
    assert [it["subject"] for it in out] == ["a", "b"]


def test_align_uses_order_when_llm_renumbers_from_one():
    out = scene_plan.align([{"n": 1, "subject": "a"}, {"n": 2, "subject": "b"}], [97, 98])
    assert [it["subject"] for it in out] == ["a", "b"]


def test_repeats_flags_prompts_stripped_too_thin():
    prompts = ["a smartphone", "a robot arm stirring a pot of soup on a stove"]
    assert scene_plan.repeats(prompts, ["phone", "robot arm"]) == [0]


def test_clean_bg_prompt_drops_screen_devices():
    got = scene_plan.clean_bg_prompt("a smartphone on a desk, a laptop, a brass bell ringing")
    assert "phone" not in got and "laptop" not in got and "bell" in got


def test_clean_bg_prompt_drops_someone_and_blackboard():
    got = scene_plan.clean_bg_prompt("a robot stirring soup, someone cooking, a blackboard")
    assert "someone" not in got and "blackboard" not in got and "robot" in got


def test_clean_bg_prompt_drops_sheets_and_written_things():
    got = scene_plan.clean_bg_prompt("an attendance sheet with checkmarks, some with reminders written on them, a brass bell")
    assert "sheet" not in got and "written" not in got and "bell" in got


# E2E ep3 sc23: "smart kitchen scale" 3 raund ardicil ekraninda reqem cekdi; "smart robot" qalmalidir
def test_clean_bg_prompt_drops_digital_and_smart_devices_but_keeps_smart_robots():
    p = "a smart kitchen scale with vegetables, a digital thermometer, a smart robot sorting fruit"
    assert scene_plan.clean_bg_prompt(p) == "a smart robot sorting fruit"


# E2E ep4 (cash flow): 52 sehnede 7 "sikke bankasi" - subyektler ferqli adlanirdi ("savings jar",
# "positive cash flow") ve yalniz son 8 sehneye baxilirdi. Esas isim promptdan cixarilir.
def test_hero_noun_is_the_head_of_the_first_noun_phrase():
    assert scene_plan.hero("a glass jar slowly filling with golden coins on a wooden table") == "jar"
    assert scene_plan.hero("a transparent jar filled with coins") == "jar"
    assert scene_plan.hero("A flowing river with stepping stones") == "river"
    assert scene_plan.hero("a cracked piggy bank with coins spilling out") == "bank"
    assert scene_plan.hero("a tray of freshly baked cookies cooling on a rack") == "tray"


def test_avoid_list_names_the_real_objects_not_only_abstract_subjects():
    prompts = ["a glass jar filled with coins", "a jar of coins on a desk", "a red kettle on a stove"]
    subjects = ["positive cash flow", "savings", "boiling point"]
    got = scene_plan.avoid_list(prompts, subjects, skip={2})
    assert "jar" in got and "positive cash flow" in got and "kettle" not in got


# E2E ep4: tekrar yoxlamasindan SONRA qoyulan ehtiyat fon ozu "a glass jar ... coins" idi -> 3-cu jar
def test_fallbacks_skip_heroes_already_in_the_episode():
    jar = next(p for p in scene_plan.FALLBACK_POOL if scene_plan.hero(p) == "jar")
    got = scene_plan.pick_fallbacks(len(scene_plan.FALLBACK_POOL) - 1, used_heroes={"jar"})
    assert jar not in got and len(set(got)) == len(got)


# Istifadeci 2026-09-27: bayqus her sehnede metne uygun gorunusde olsun (ChatGPT ile cekilir)
def _fake_plan_llm(monkeypatch, action):
    def fake(system, user, **kw):
        import re as _re
        nums = [int(n) for n in _re.findall(r"^(\d+)\. \[", user, _re.M)]
        return {"scenes": [{"n": n, "subject": f"thing {n}", "bg_prompt": f"a shiny brass object number {n} on a wooden desk",
                            "sprite": "front", "owl_action": action} for n in nums]}
    monkeypatch.setattr(scene_plan, "chat_json", fake)


def test_plan_keeps_the_owl_action_for_each_scene(monkeypatch):
    _fake_plan_llm(monkeypatch, "shaking hands with a small robot, smiling")
    scenes = [{"section": "Hook", "narration": "AI helps people at work every day."}] * 2
    out = scene_plan.plan(scenes, list(scene_plan.VIDEO_POSES))
    assert [s["owl_action"] for s in out] == ["shaking hands with a small robot, smiling"] * 2


def test_owl_action_drops_people_and_writing():
    out = scene_plan.clean_owl_action("holding a book and waving to a customer, a sign that says HELLO")
    assert "book" not in out and "customer" not in out and "sign" not in out
    assert scene_plan.clean_owl_action("") == ""
