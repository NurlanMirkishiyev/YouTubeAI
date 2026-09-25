import scene_plan


def test_positions_alternate_by_section_and_never_center():
    scenes = [{"section": s} for s in ("Hook", "Hook", "Section 1: A", "Section 2: B", "Call to Action")]
    assert scene_plan.assign_positions(scenes) == ["right", "right", "left", "right", "left"]


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
    out = scene_plan.clean_bg_prompt("a counter with a credit card reader, a toy on the counter")
    assert out == "a toy on the counter"


def test_clean_bg_prompt_turns_pizza_box_into_tray():
    out = scene_plan.clean_bg_prompt("an empty pizza box on a table")
    assert out == "an empty pizza tray on a table"
