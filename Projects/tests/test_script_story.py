"""#59 (istifadeci 2026-10-05) - ssenari keyfiyyeti, HER yeni videoda:
1 B2B: her video biznes sahibinin konkret qerarina cavab verir; 2 anlayislar (terif/analogiya) yoxlanir, vəd olunan
suala cavab verilir; 3 en azi 1 yoxlanmis menbe; 4 ilk 3 saniyede konkret reqem; 5 bir case evvelden sona;
6 tekrar yox, Recap yalniz neticeler; 12 ABS auditoriyasi."""
import json

import pytest

import script_gen as sg
import script_qa as qa

PLAN = {"decision": "Should Rosa raise her menu prices by 10% this year?",
        "answer": "Raise prices when your margin is under 10% and customers value you for more than price.",
        "case": {"owner": "Rosa", "business": "a 30-seat taqueria", "city": "Austin", "state": "Texas"},
        "cold_open": "A 10% price rise can lose you fewer customers than you fear."}
SOURCE = {"cite_as": "the Federal Reserve", "figure": 48.0, "publisher": "Federal Reserve Banks",
          "url": "https://www.fedsmallbusiness.org/r.pdf", "year": 2025,
          "claim": "48% of employer firms raised prices in the prior 12 months."}


def _script(**over):
    parts = {
        "Cold Open": "A 10% price rise can lose you fewer customers than you fear.",
        "Hook": "Rosa runs a 30-seat taqueria in Austin. Should she raise prices this year?",
        "Section 1: Margin": "Rosa keeps $8 of every $100 in sales. That is her margin.",
        "Section 2: Demand": "According to the Federal Reserve, 48% of employer firms raised prices last year. Rosa "
                             "wonders if her regulars would leave.",
        "Section 3: Testing": "Rosa tests a higher price on two dishes for one month.",
        "Section 4: Decision": "Rosa raises prices because her margin was too thin.",
        "Common Mistakes": "Owners often wait too long.",
        "Recap": "Check your margin first. Test before you commit. Raise prices when value beats price.",
        "Call to Action": "Tell us in the comments how you set prices.",
    }
    parts.update(over)
    return "# Should You Raise Prices?\n\n" + "\n\n".join(f"## {h}\n\n{t}" for h, t in parts.items()) + "\n"


def test_cold_open_is_a_required_heading():
    assert "## Cold Open" in sg.check_headings("## Hook\n")


@pytest.mark.parametrize("line, ok", [
    ("A $9.99 price can earn you less than $10.", True),
    ("48% of small firms raised prices last year.", True),
    ("Pricing is hard for every small business owner today.", False),          # reqem yox
    ("Most owners who run small shops across the country and in every town lose 20%.", False),  # reqem gec
])
def test_cold_open_has_a_number_within_the_first_three_seconds(line, ok):
    assert (qa.cold_open_problems(line) == []) is ok


def test_complete_script_passes_story_checks():
    assert qa.story_problems(_script(), PLAN, SOURCE) == []


def test_case_owner_must_run_through_every_teaching_section():
    probs = qa.story_problems(_script(**{"Section 3: Testing": "Testing a higher price on two dishes helps."}),
                              PLAN, SOURCE)
    assert any("Section 3" in p and "Rosa" in p for p in probs)


def test_recap_states_only_conclusions():
    probs = qa.story_problems(_script(Recap="Rosa raised prices by 10% and kept $8 more."), PLAN, SOURCE)
    assert any("Recap" in p for p in probs)


def test_source_must_be_cited_with_its_figure():
    probs = qa.story_problems(_script(**{"Section 2: Demand": "Many firms raised prices last year, Rosa says."}),
                              PLAN, SOURCE)
    assert any("menbe" in p for p in probs)


def test_case_must_be_in_the_united_states():
    plan = {**PLAN, "case": {**PLAN["case"], "city": "Baku", "state": "Absheron"}}
    assert any("ABS" in p for p in qa.story_problems(_script(), plan, SOURCE))


def test_plan_must_name_a_business_decision_question():
    assert any("qerar" in p for p in qa.story_problems(_script(), {**PLAN, "decision": "Pricing basics"}, SOURCE))


def test_system_prompt_targets_us_business_owners_and_decisions():
    low = sg.SYSTEM.lower()
    assert "adult" in low and "business owner" in low and "decision" in low and "united states" in low
    assert "$4,000" in sg.SYSTEM                     # reqemler reqemle yazilir (altyazi/TTS ucun)
    recap = dict((h, g) for h, _, g in sg.BLOCKS)["Recap"].lower()
    assert "no examples" in recap and "no numbers" in recap


def test_review_rewrites_only_the_flagged_sections():
    script = _script()
    calls = []

    def fake_review(system, user, **kw):
        calls.append("review")
        if len(calls) == 1:
            return {"definitions_ok": False, "analogies_ok": True, "answers_decision": True, "repeats": [],
                    "recap_only_conclusions": True, "consistent": True, "source_faithful": True, "single_case": True,
                    "fixes": [{"section": "Section 1: Margin", "problem": "margin defined as profit",
                               "instruction": "Define margin as the share of each sale kept as profit."}]}
        return {"definitions_ok": True, "analogies_ok": True, "answers_decision": True, "repeats": [],
                "recap_only_conclusions": True, "consistent": True, "source_faithful": True, "single_case": True, "fixes": []}

    def fake_rewrite(system, user, **kw):
        assert "share of each sale" in user
        return "Rosa keeps $8 of every $100 in sales - an 8% margin, the share of each sale she keeps."

    out, problems = qa.review_loop(script, PLAN, SOURCE, "Should You Raise Prices?",
                                   review=fake_review, rewrite=fake_rewrite)
    assert problems == [] and "share of each sale she keeps" in out
    assert out.split("## Section 2")[1] == script.split("## Section 2")[1]       # qalan bolmeler toxunulmur


def test_review_problems_remain_when_rewrites_do_not_help():
    bad = {"definitions_ok": True, "analogies_ok": True, "answers_decision": False, "repeats": [],
           "recap_only_conclusions": True, "consistent": True, "source_faithful": True, "single_case": True, "fixes": [{"section": "Section 4: Decision", "problem": "no clear answer",
                                                      "instruction": "Answer the decision."}]}
    _, problems = qa.review_loop(_script(), PLAN, SOURCE, "T", review=lambda *a, **k: bad,
                                 rewrite=lambda *a, **k: "Rosa raises prices because her margin was too thin.")
    assert problems and any("qerar" in p for p in problems)


def test_quality_report_is_bound_to_the_script(tmp_path):
    (tmp_path / "script.md").write_text(_script(), encoding="utf-8")
    assert qa.report_problems(str(tmp_path)) == ["ssenari keyfiyyet yoxlamasi aparilmayib (script_qa.json yoxdur)"]
    qa.write_report(str(tmp_path), _script(), [])
    assert qa.report_problems(str(tmp_path)) == []
    (tmp_path / "script.md").write_text(_script() + "\nextra\n", encoding="utf-8")
    assert qa.report_problems(str(tmp_path))
    qa.write_report(str(tmp_path), _script(), ["Recap: reqem var"])
    (tmp_path / "script.md").write_text(_script(), encoding="utf-8")
    assert qa.report_problems(str(tmp_path)) == ["Recap: reqem var"]


def test_verify_script_stage_requires_quality_report(tmp_path):
    import stages as st
    (tmp_path / "script.md").write_text(_script(), encoding="utf-8")
    (tmp_path / "math_check.json").write_text(json.dumps({"script_sha256": "x", "problems": []}), encoding="utf-8")
    ctx = st.Ctx(topic="T", slug="t", ep_dir=str(tmp_path), words=1, music=None, min_seconds=1, max_seconds=2,
                 provider="openai")
    assert any("script_qa" in p for p in st.verify_script(ctx))


def test_cold_open_is_spoken_on_the_intro_card_not_as_a_scene():
    import scene_plan
    from timeline import cold_open
    md = _script()
    assert cold_open(md) == "A 10% price rise can lose you fewer customers than you fear."
    assert all(s["section"] != "Cold Open" for s in scene_plan.split_scenes(md))


# --- E2E raise-your-prices (2026-10-05): redaktor "OK" dedi, amma cavab qeyri-muəyyen idi ("Aim for a balance
#     between value and profitability"), "$2,000 per project" 4 bolmede, agentlik 2 defe yeniden tanidildi ---

def test_answer_must_be_a_concrete_conditional_rule():
    vague = {**PLAN, "answer": "Aim for a balance between value and profitability."}
    assert any("cavab" in p for p in qa.story_problems(_script(), vague, SOURCE))
    assert not any("cavab" in p for p in qa.story_problems(_script(), PLAN, SOURCE))


def test_same_figure_in_more_than_two_sections_is_a_repeat():
    md = _script(**{"Section 1: Margin": "Rosa charges $14 a plate and keeps $8 of every $100 in sales.",
                    "Section 3: Testing": "Rosa still charges $14 a plate while she tests two dishes.",
                    "Section 4: Decision": "Rosa raises the $14 plate because her margin was too thin."})
    probs = qa.story_problems(md, PLAN, SOURCE)
    assert any("$14" in p and "Section 3" in p for p in probs)
    fixes = qa.story_fixes(md, PLAN, SOURCE, "Section 2: Demand")
    assert [f["section"] for f in fixes if "$14" in f["instruction"]] == ["Section 3: Testing"]


def test_review_prompt_demands_concrete_answer_and_counts_restated_facts():
    low = qa.REVIEW_SYSTEM.lower()
    assert "condition" in low and "vague" in low and "restat" in low


def test_owner_fix_targets_the_full_section_heading():
    md = _script(**{"Section 3: Testing": "Testing a higher price on two dishes helps."})
    assert [f["section"] for f in qa.story_fixes(md, PLAN, SOURCE, "Section 2: Demand")] == ["Section 3: Testing"]


def test_outline_and_sections_ask_for_a_concrete_rule_and_no_reintroductions():
    assert "threshold" in sg.OUTLINE_USER.lower()
    g = sg._section_guidance({**PLAN, "sections": [{}] * 4, "source_section": 2}, {}, 3, SOURCE)
    assert "do not re-introduce" in g.lower()


def test_outline_is_asked_again_until_the_plan_is_valid(monkeypatch):
    plans = [{**PLAN, "answer": "Find a balance.", "sections": [{}] * 4},
             {**PLAN, "sections": [{}] * 4}]
    calls = []
    monkeypatch.setattr(sg, "chat_json", lambda system, user, **kw: calls.append(user) or plans[len(calls) - 1])
    plan = sg.outline("T")
    assert plan["answer"] == PLAN["answer"] and len(calls) == 2 and "Find a balance." in calls[1]
    assert qa.plan_problems(plan) == []


def test_failed_script_is_regenerated_on_stage_retry(tmp_path):
    """Keyfiyyet qapisinda dusen skript yazilib qalir - retry (--force-suz) onu yeniden yazmalidir."""
    (tmp_path / "script.md").write_text(_script(), encoding="utf-8")
    assert sg.needs_regeneration(str(tmp_path)) is True              # hesabat yoxdur
    qa.write_report(str(tmp_path), _script(), ["Recap: reqem var"])
    assert sg.needs_regeneration(str(tmp_path)) is True
    qa.write_report(str(tmp_path), _script(), [])
    import math_check as mc
    mc.write_report(str(tmp_path), _script(), [])
    assert sg.needs_regeneration(str(tmp_path)) is False


# --- E2E raise-your-prices run 2: uzatma bolmesi qerardan SONRA dusdu ve ziddiyyet yaratdi ($3.30 vs $3.10);
#     menbe tehrif olundu ("61% raised prices" -> "...without losing their customer base") ---

def test_extension_goes_before_the_decision_section_and_sections_are_renumbered(monkeypatch):
    md = _script()
    monkeypatch.setattr(sg, "chat_json", lambda *a, **k: {"title": "Pilot Test", "idea": "Test first",
                                                          "domain": "a farm", "analogy": "Trial plots."})
    seen = {}

    def fake_chat(system, user, **kw):
        seen["user"] = user
        return "Rosa tests the new price on two dishes before deciding."
    monkeypatch.setattr(sg, "chat", fake_chat)
    out, _ = sg.extend("T", md, 150, [], {**PLAN, "sections": [{}] * 4, "source_section": 2})
    heads = sg.teaching_headings(out)
    assert heads == ["Section 1: Margin", "Section 2: Demand", "Section 3: Testing", "Section 4: Pilot Test",
                     "Section 5: Decision"]
    assert "do not make or announce the final decision" in seen["user"].lower()


def test_review_checks_story_consistency_and_source_faithfulness():
    low = qa.REVIEW_SYSTEM.lower()
    assert "consistent" in low and "source_faithful" in low
    r = {"definitions_ok": True, "analogies_ok": True, "answers_decision": True, "repeats": [],
         "recap_only_conclusions": True, "consistent": True, "source_faithful": True, "single_case": True, "consistent": False, "source_faithful": False}
    probs = qa.review_problems(r)
    assert any("ziddiyyet" in p for p in probs) and any("menbe" in p for p in probs)
    assert "61%" in qa._review_user("x", PLAN, "T", {**SOURCE, "claim": "61% raised prices."})


def test_decision_figure_is_limited_to_two_mentions_too():
    """Istifadeci 2026-10-07: her reqem en cox 2 defe - qerar reqemi de ('$1,150' 3 sehnede gorunurdu)."""
    md = _script(**{"Section 1: Margin": "Rosa wonders about a 10% rise.",
                    "Section 3: Testing": "Rosa tests the 10% rise on two dishes.",
                    "Section 4: Decision": "Rosa raises prices by 10% because her margin was too thin."})
    assert any("10%" in p and "Section 3" in p for p in qa.story_problems(md, PLAN, SOURCE))


def test_same_figure_three_times_in_one_section_is_a_repeat():
    md = _script(**{"Section 4: Decision": "Her new price is $1,150. At $1,150 she keeps 9 of 10 clients. "
                                           "So $1,150 it is."})
    probs = qa.story_problems(md, PLAN, SOURCE)
    assert any("$1,150" in p and p.startswith("Section 4") for p in probs)
    fixes = qa.story_fixes(md, PLAN, SOURCE, "Section 2: Demand")
    assert any(f["section"] == "Section 4: Decision" and "$1,150" in f["instruction"] for f in fixes)


def test_a_figure_said_twice_is_fine():
    md = _script(**{"Section 1: Margin": "Rosa charges $14 a plate.",
                    "Section 4: Decision": "Rosa raises the $14 plate."})
    assert not any("$14" in p for p in qa.story_problems(md, PLAN, SOURCE))



def test_analogies_are_everyday_images_never_another_business():
    """Istifadeci 2026-10-07: case-den basqa biznes misali yox (asbaz, yuk dasima sirketi kadri). Analogiya qalir."""
    import script_gen as sg
    low = (sg.SYSTEM + sg.OUTLINE_USER + sg.EXTEND_USER).lower()
    assert "never another business" in low
    for biz in ("commercial kitchen", "trucking route", "car dealership", "dental office", "a warehouse."):
        assert biz not in low, biz


def test_reviewer_flags_examples_from_other_businesses():
    assert "single_case" in qa.REVIEW_SYSTEM
    assert any("basqa biznes" in p for p in qa.review_problems({"single_case": False}))
