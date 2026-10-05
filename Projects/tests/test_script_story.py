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
                    "recap_only_conclusions": True,
                    "fixes": [{"section": "Section 1: Margin", "problem": "margin defined as profit",
                               "instruction": "Define margin as the share of each sale kept as profit."}]}
        return {"definitions_ok": True, "analogies_ok": True, "answers_decision": True, "repeats": [],
                "recap_only_conclusions": True, "fixes": []}

    def fake_rewrite(system, user, **kw):
        assert "share of each sale" in user
        return "Rosa keeps $8 of every $100 in sales - an 8% margin, the share of each sale she keeps."

    out, problems = qa.review_loop(script, PLAN, SOURCE, "Should You Raise Prices?",
                                   review=fake_review, rewrite=fake_rewrite)
    assert problems == [] and "share of each sale she keeps" in out
    assert out.split("## Section 2")[1] == script.split("## Section 2")[1]       # qalan bolmeler toxunulmur


def test_review_problems_remain_when_rewrites_do_not_help():
    bad = {"definitions_ok": True, "analogies_ok": True, "answers_decision": False, "repeats": [],
           "recap_only_conclusions": True, "fixes": [{"section": "Section 4: Decision", "problem": "no clear answer",
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
