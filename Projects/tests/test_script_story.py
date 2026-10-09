"""#59 (istifadeci 2026-10-05) - ssenari keyfiyyeti, HER yeni videoda:
1 B2B: her video biznes sahibinin konkret qerarina cavab verir; 2 anlayislar (terif/analogiya) yoxlanir, vəd olunan
suala cavab verilir; 3 en azi 1 yoxlanmis menbe; 4 ilk 3 saniyede konkret reqem; 5 bir case evvelden sona;
6 tekrar yox, Recap yalniz neticeler; 12 ABS auditoriyasi."""
import json

import pytest

import script_gen as sg
import script_qa as qa

MODEL = {"variables": [{"name": "price", "value": 14, "unit": "$", "label": "plate price"},
                       {"name": "rise", "value": 10, "unit": "%", "label": "price rise"},
                       {"name": "plates", "value": 100, "unit": "plates", "label": "plates a week"},
                       {"name": "margin", "value": 8, "unit": "%", "label": "margin"},
                       {"name": "stay", "value": 0.9, "unit": "share", "label": "customers who stay"}],
         "before": {"revenue": "plates * price"},
         "after": {"revenue": "plates * stay * price * (1 + rise / 100)"},
         "threshold": {"name": "margin_limit", "expr": "rise", "rounding": "none",
                       "meaning": "margin below which a price rise pays"}}
PLAN = {"decision": "Should Rosa raise her menu prices by 10% this year?",
        "answer": "Raise prices when your margin is under 10% and customers value you for more than price.",
        "case": {"owner": "Rosa", "business": "a 30-seat taqueria", "city": "Austin", "state": "Texas"},
        "cold_open": "A 10% price rise can lose you fewer customers than you fear.", "model": MODEL}
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
        "Section 4: Decision": "Rosa raises prices by 10% and revenue goes from $1,400 to $1,386, because her margin "
                               "was too thin.",
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


# --- E2E raise-your-prices (2026-10-05): redaktor "OK" dedi, amma cavab qeyri-mueyyen idi ("Aim for a balance
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
    assert [f["section"] for f in fixes if "$14" in f["problem"]] == ["Section 3: Testing"]


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
    plans = [{**PLAN, "decision": "Pricing basics", "sections": [{}] * 4},
             {**PLAN, "sections": [{}] * 4}]
    calls = []
    monkeypatch.setattr(sg, "chat_json", lambda system, user, **kw: {"ok": True} if kw.get("model") == "gpt-4o"
                        else calls.append(user) or plans[len(calls) - 1])
    plan = sg.outline("T")
    assert plan["answer"] == PLAN["answer"] and len(calls) == 2 and "Pricing basics" in calls[1]
    assert qa.plan_problems(plan) == []


def test_vague_answer_is_rewritten_from_the_computed_threshold(monkeypatch):
    """Real probe 2026-10-07: LLM threshold-u ozu hesablaya bilmir - cavab hesablanmis deyerle yazdirilir."""
    monkeypatch.setattr(sg, "chat_json", lambda *a, **k: {"ok": True} if k.get("model") == "gpt-4o"
                        else {**PLAN, "answer": "Find a balance.", "sections": [{}] * 4})
    seen = {}
    monkeypatch.setattr(sg, "chat", lambda system, user, **kw: seen.setdefault("u", user) and
                        "Make the change if your margin is under 10%.")
    plan = sg.outline("T")
    assert plan["answer"] == "Make the change if your margin is under 10%." and "10%" in seen["u"]


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


def test_reviewer_sees_the_source_year():
    """#93 (E2E hire-first-employee): #92 skriptde ili teleb edir, redaktorun VERIFIED FACT-inde il yox idi ->
    'in 2022' 3 raund 'menbe tehrif olunub' sayildi, script_gen dayandi."""
    fact = next(ln for ln in qa._review_user("x", PLAN, "T", {**SOURCE, "year": 2022}).splitlines()
                if ln.startswith("VERIFIED FACT"))
    assert "2022" in fact


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


# --- Faza 1 (istifadeci 2026-10-07): case modeli, cold open = insight, uydurma reqem qadagasi, tek case ---

def _model_plan():
    import case_model as cm
    from test_case_model import PLAN as CPLAN
    return {**PLAN, **CPLAN, "answer": "Raise the price if at least 27 customers stay at $55.",
            "model_result": cm.evaluate(CPLAN["model"])}


def test_plan_without_a_case_model_is_rejected():
    plan = {k: v for k, v in PLAN.items() if k != "model"}
    assert any("model" in p for p in qa.plan_problems(plan))


def test_plan_with_an_uncomputable_model_is_rejected():
    plan = {**PLAN, "model": {**MODEL, "after": {"revenue": "plates * price_x"}}}
    assert any("model" in p for p in qa.plan_problems(plan))


def test_answer_figures_must_come_from_the_model():
    assert qa.plan_problems(_model_plan()) == []
    bad = {**_model_plan(), "answer": "Raise the price if costs rose more than 9%."}
    assert any("9" in p and "model" in p for p in qa.plan_problems(bad))


def test_outline_stores_the_model_result(monkeypatch):
    plan = {k: v for k, v in _model_plan().items() if k != "model_result"}
    monkeypatch.setattr(sg, "chat_json", lambda *a, **k: {"ok": True} if k.get("model") == "gpt-4o"
                        else {**plan, "sections": [{}] * 4})
    got = sg.outline("T")
    assert got["model_result"]["threshold"]["value"] == 27


def test_outline_prompt_has_no_numeric_example_answers():
    import re
    assert re.findall(r"\$\d|\d+\s*%", sg.OUTLINE_USER) == []
    assert re.findall(r"e\.g\.[^)\n]*\d", sg.OUTLINE_USER) == []
    assert '"model"' in sg.OUTLINE_USER and "threshold" in sg.OUTLINE_USER


def test_cold_open_is_built_from_the_model_insight(monkeypatch):
    plan = _model_plan()
    monkeypatch.setattr(sg, "chat", lambda *a, **k: (_ for _ in ()).throw(AssertionError("LLM lazim deyil")))
    assert sg.make_cold_open(plan) == plan["model_result"]["insight"]


def test_cold_open_figure_must_be_in_the_model():
    import case_model as cm
    allowed = cm.allowed_numbers(_model_plan()["model_result"])
    assert qa.cold_open_problems("Profit rises from $400 to $510 after the change.", allowed) == []
    assert any("model" in p for p in qa.cold_open_problems("A 30% drop can still raise your profit.", allowed))


def test_story_checks_include_the_case_model():
    plan = _model_plan()
    md = _script(**{"Section 4: Decision": "Rosa adds 40 customers × $5 = $200 extra a week."})
    probs = qa.story_problems(md, plan, SOURCE)
    assert any("deyisen buraxilib" in p for p in probs)
    fixes = qa.story_fixes(md, plan, SOURCE, "Section 2: Demand")
    assert any(f["section"] == "Section 4: Decision" and "model" in f["instruction"].lower() for f in fixes)


def test_decision_section_is_told_to_use_exactly_the_model_figures():
    plan = {**_model_plan(), "sections": [{}] * 4, "source_section": 2}
    g = sg._section_guidance(plan, {}, 4, SOURCE)
    assert "use exactly these figures" in g.lower() and "$1,870" in g and "27" in g
    assert "$1,870" in sg.outline_text(plan)


def test_plan_analogy_with_a_number_is_rejected():
    plan = {**_model_plan(), "sections": [{"analogy": "Like a thermostat set to 70 degrees."}]}
    assert any("analogiya" in p for p in qa.plan_problems(plan))


def test_recap_with_an_example_is_rejected():
    md = _script(Recap="Check your margin first. For example, imagine a busy Friday night.")
    assert any("Recap" in p and "misal" in p for p in qa.story_problems(md, PLAN, SOURCE))


def test_answer_must_state_the_model_threshold():
    """Real probe 2026-10-07: cavab '80 customers', modelin threshold-u 250 idi."""
    bad = {**_model_plan(), "answer": "Raise the price if at least 34 customers stay."}
    assert any("threshold" in p for p in qa.plan_problems(bad))


def test_precomputed_result_as_a_variable_is_rejected():
    """Real probe: LLM 'before_profit' ve 'customers_needed'-i deyisen kimi yazdi (hesab yoxlanmir)."""
    import case_model as cm
    from test_case_model import MODEL as CM
    bad = {**CM, "variables": CM["variables"] + [{"name": "before_profit", "value": 400, "unit": "$"}]}
    with pytest.raises(cm.CaseModelError):
        cm.evaluate(bad)
    # real probe 2026-10-07: threshold 'new_price' giris deyiseni ile eyni adda idi - 5 cehd redd. Threshold adi
    # deyisdirilir (deyisen giris kimi qalir, threshold ondan asili olmadan hesablanir)
    bad2 = {**CM, "variables": CM["variables"] + [{"name": "customers_needed", "value": 27, "unit": "customers"}]}
    r = cm.evaluate(bad2)
    assert r["threshold"]["name"] == "customers_needed_threshold" and r["threshold"]["value"] == 27


def test_model_is_reviewed_by_gpt4o_and_rejected_plans_are_asked_again(monkeypatch):
    """Real probe 2026-10-07: gpt-4o-mini modelleri bezen mentiqsizdir (sehrli '/ 20', threshold menasi ile
    dustur uygunsuz) - gpt-4o yoxlayir (yoxlama modeli), redd -> plan yeniden."""
    good = {**_model_plan(), "sections": [{}] * 4}
    good.pop("model_result")
    seen = []

    def fake(system, user, **kw):
        if system == sg.MODEL_REPAIR_SYSTEM:
            return {"model": good["model"]}
        if kw.get("model") == "gpt-4o":
            seen.append(user)
            return {"ok": len(seen) > 1, "problems": [] if len(seen) > 1 else ["threshold ignores the unit cost"]}
        return good
    monkeypatch.setattr(sg, "chat_json", fake)
    plan = sg.outline("T")
    assert len(seen) == 2 and "$1,870" in seen[0] and plan["model_result"]["threshold"]["value"] == 27


def test_rejected_model_is_repaired_without_replanning(monkeypatch):
    """Real probe 2026-10-07: gpt-4o deqiq duzelis verdi, mini butun plani yeniden yazanda 5 defe tetbiq etmedi."""
    good = {**_model_plan(), "sections": [{}] * 4}
    good.pop("model_result")
    broken = {**good, "model": {**good["model"], "after": {"revenue": "customers * price_new",
                                                           "profit": "customers * (price_new - unit_cost)"}}}
    calls = {"plan": 0, "repair": 0, "review": 0}

    def fake(system, user, **kw):
        if system == sg.MODEL_REPAIR_SYSTEM:
            calls["repair"] += 1
            assert "after ignores retention" in user
            return {"model": good["model"]}
        if kw.get("model") == "gpt-4o":
            calls["review"] += 1
            return {"ok": calls["review"] > 1, "problems": ["after ignores retention"]}
        if system == sg.MODEL_REPAIR_SYSTEM:
            calls["repair"] += 1
            assert "after ignores retention" in user
            return {"model": good["model"]}
        calls["plan"] += 1
        return broken
    monkeypatch.setattr(sg, "chat_json", fake)
    monkeypatch.setattr(sg, "chat", lambda *a, **k: "Raise the price if at least 27 customers stay at $55.")
    plan = sg.outline("T")
    assert calls == {"plan": 1, "repair": 1, "review": 2}
    assert plan["model_result"]["after"]["profit"] == 510


def test_negative_or_zero_threshold_is_a_model_error():
    """Real probe 2026-10-07: threshold '$-2,000' - cavab duzelisi bunu hell ede bilmez, model sehvdir."""
    plan = {**_model_plan(), "model": {**_model_plan()["model"], "threshold": {
        "name": "t", "expr": "after_revenue - before_revenue", "rounding": "none", "meaning": "m"}}}
    plan.pop("model_result")
    assert any("case model" in p and "threshold" in p and "musbet" in p for p in qa.plan_problems(plan))


def test_model_repair_runs_on_the_verification_model(monkeypatch):
    seen = {}
    monkeypatch.setattr(sg, "chat_json", lambda system, user, **kw: seen.update(kw) or {"model": {}})
    sg.repair_model(_model_plan(), ["x"], provider="openai")
    assert seen["model"] == sg.MODEL_REVIEW_MODEL


def test_model_review_and_repair_accept_the_cli_llm_kwargs(monkeypatch):
    """Real run 2026-10-07: script_gen CLI temperature/model/provider oturur -> 'multiple values for temperature'."""
    import llm
    def strict(system, user, *, provider="openai", model=None, temperature=0.7, max_tokens=1000):
        return {"ok": True, "model": _model_plan()["model"]}
    monkeypatch.setattr(sg, "chat_json", strict)
    kw = {"provider": "openai", "model": None, "temperature": 0.7}
    assert sg.review_model(_model_plan(), **kw) == []
    assert sg.repair_model(_model_plan(), ["x"], **kw)


# --- Real probe 2026-10-07 (raise prices): model reqemleri her bolmede tekrarlandi, tekrar duzelisi qerar
#     bolmesinden reqemleri sildi -> redaktor 3 raund "qerara cavab verilmir" dedi ---

def test_repeat_fix_never_strips_the_decision_section():
    md = _script(**{"Hook": "Rosa runs a 30-seat taqueria in Austin and charges $14 a plate.",
                    "Section 4: Decision": "Rosa raises the $14 plate.",
                    "Common Mistakes": "Owners keep the $14 plate too long."})
    probs = [p for p in qa.story_problems(md, PLAN, SOURCE) if "$14" in p and "tekrar" in p]
    assert probs and all(p.startswith("Common Mistakes") for p in probs)


def test_figures_are_allocated_to_sections():
    plan = {**_model_plan(), "sections": [{}] * 4, "source_section": 2}
    hook = sg._fill(dict((h, g) for h, _, g in sg.BLOCKS)["Hook"], plan) + sg.hook_figures(plan)
    assert "$50" in hook and "40" in hook                       # baslangic deyisenleri Hook-da bir defe
    mid = sg._section_guidance(plan, {}, 2, SOURCE)
    assert "do not state any case figure" in mid.lower() and "$1,870" not in mid
    assert "$1,870" in sg._section_guidance(plan, {}, 4, SOURCE)


def test_case_business_is_described_without_numbers():
    assert "no numbers" in sg.OUTLINE_USER.split('"business"')[1].split("\n")[0].lower()


def test_after_a_model_failure_the_next_attempt_starts_fresh(monkeypatch):
    """Real probe 2026-10-07: 'Previous plan' geri oturulende mini eyni sehv modeli 5 defe tekrarladi."""
    bad = {**_model_plan(), "sections": [{}] * 4,
           "model": {**_model_plan()["model"], "after": {"revenue": "customers * nope"}}}
    bad.pop("model_result")
    good = {**_model_plan(), "sections": [{}] * 4}
    good.pop("model_result")
    users = []

    def fake(system, user, **kw):
        if system == sg.MODEL_REPAIR_SYSTEM:
            return {"model": bad["model"]}
        if kw.get("model") == "gpt-4o":
            return {"ok": True}
        users.append(user)
        return bad if len(users) == 1 else good
    monkeypatch.setattr(sg, "chat_json", fake)
    sg.outline("T")
    assert "Previous plan" not in users[1] and "unknown name" in users[1]


def test_fixes_for_one_section_are_merged_into_one_rewrite():
    """Real probe 2026-10-07: Section 4 bir raundda 8 defe ayri-ayri yeniden yazildi (her biri bir reqem)."""
    calls = []

    def rewrite(system, user, **kw):
        calls.append(user)
        return "Rosa raises prices by 10% and revenue goes from $1,400 to $1,386."
    fixes = [{"section": "Section 4: Decision", "problem": "a", "instruction": "fix A"},
             {"section": "Section 4: Decision", "problem": "b", "instruction": "fix B"}]
    qa.apply_fixes(_script(), PLAN, fixes, rewrite)
    assert len(calls) == 1 and "fix A" in calls[0] and "fix B" in calls[0]


# --- Faza 5.5 xeta sinfi: real sexs/sirket haqqinda menbesiz huquqi iddia (2026-10-08) ---

def test_unsourced_legal_claim_about_a_real_company_is_caught():
    import script_qa as qa
    plan = {"case": {"owner": "Rosa Diaz", "business": "Rosa's Bakery", "city": "Austin", "state": "Texas"}}
    bad = "## Section 1: Prices\nWalmart was sued for price gouging, so Rosa should be careful.\n"
    assert qa.legal_claim_problems(bad, plan)
    ok = ("## Section 1: Prices\nRosa could be fined by the IRS if she files late.\n"
          "Rosa's Bakery would face a penalty from the SBA rules.\n")
    assert qa.legal_claim_problems(ok, plan) == []


def test_story_checks_include_legal_claims():
    import inspect
    import script_qa as qa
    assert "legal_claim_problems" in inspect.getsource(qa.story_problems)


def test_repeat_fix_says_how_many_mentions_the_section_keeps():
    """#97 (E2E 2026-10-08, hire-first-employee): Hook + qerar bolmesinde 2 defe '$800' (esik = xerc). Telimat
    'do not restate' idi - yazici qerar qaydasi ucun reqemi saxladi, hec birini silmedi, 3 cehd dayandi."""
    md = _script(**{"Hook": "Rosa runs a 30-seat taqueria in Austin. The new hire costs $800 a week.",
                    "Section 4: Decision": "The hire costs $800. Rosa hires if she adds $800 in weekly sales."})
    fixes = [f for f in qa.story_fixes(md, PLAN, SOURCE, "Section 2: Demand") if "$800" in f["instruction"]]
    assert fixes and fixes[0]["section"] == "Section 4: Decision"
    assert "exactly once" in fixes[0]["instruction"] and "current price" not in fixes[0]["instruction"]


def test_plan_rejects_a_threshold_unlinked_to_the_decision():
    """#98: esik musteri sayi ile olculur, delta ondan asili deyil -> plan modeli yeniden istenir."""
    model = {"variables": [{"name": "weekly_customers", "value": 80, "label": "customers per week"},
                           {"name": "price", "value": 5, "unit": "$"}, {"name": "rent", "value": 300, "unit": "$"},
                           {"name": "wage", "value": 15, "unit": "$"}],
             "before": {"weekly_profit": "weekly_customers * price - rent"},
             "after": {"weekly_profit": "weekly_customers * price - rent - wage * 20"},
             "threshold": {"name": "need", "expr": "wage * 20 / price", "rounding": "ceil",
                           "meaning": "customers needed to cover the employee"}}
    plan = {**_model_plan(), "model": model, "answer": "Hire when you have at least 60 customers a week."}
    plan.pop("model_result")
    assert any("not linked" in p for p in qa.plan_problems(plan))


def test_repeat_fix_quotes_the_sentence_to_change():
    """#101 (E2E 2026-10-08): 'Say $3,000 exactly once' 2 raund icra olunmadi (gpt-4o-mini) - telimat artiq
    reqemi silinecek cumleni sitat getirir, qerar qaydasi (son deyilis) qalir."""
    md = _script(**{"Hook": "Rosa runs a 30-seat taqueria in Austin and earns $3,000 a month.",
                    "Section 4: Decision": "Currently, Rosa's monthly profit is $3,000. Her profit goes from $3,000 "
                                           "to $1,000 if she hires."})
    fixes = [f for f in qa.story_fixes(md, PLAN, SOURCE, "Section 2: Demand") if "$3,000" in f["instruction"]]
    assert fixes and "Currently, Rosa's monthly profit is $3,000." in fixes[0]["instruction"]
    assert "goes from $3,000" not in fixes[0]["instruction"].split("Keep")[0]


def test_reviewer_rules_match_the_cold_open_and_two_mentions_rules():
    """#103 (E2E 2026-10-08, Gemini Pro redaktor): Cold Open tizerindeki reqemleri 'tanitilmadan isledilib' (consistent
    false) ve qerar bolmesindeki 2-ci deyilisi 'tekrar' saydi - bizim qaydalar (Cold Open reqemi, reqem <= 2) ile zidd."""
    low = qa.REVIEW_SYSTEM.lower()
    assert "cold open" in low and "teaser" in low
    assert "at most twice" in low


def test_decision_guidance_forbids_copying_model_labels():
    """#103: Gemini Flash 'monthly revenue before of $12,000', '40 monthly jobs completed solo' yazdi - etiketler herfen."""
    plan = {**_model_plan(), "sections": [{}] * 4, "source_section": 2}
    g = sg._section_guidance(plan, {}, 4, SOURCE).lower()
    assert "never copy" in g and "labels" in g


def test_settle_repeats_drops_a_pure_restatement_and_keeps_the_decision_sentence():
    """#105 (E2E 2026-10-08): 14 ugursuz cehdin 7-si 'qerar bolmesinde reqem 3 defe' - gpt-4o-mini sitatli telimata
    da emel etmedi. LLM raundlarindan sonra artiq deyilis DETERMINISTIK duzelir: yeni melumatsiz cumle silinir."""
    md = _script(**{"Hook": "Rosa runs a 30-seat taqueria in Austin and earns $3,000 a month.",
                    "Section 4: Decision": "Currently, Rosa's monthly profit is $3,000. Her profit goes from $3,000 "
                                           "to $1,000 if she hires."})
    out = qa.settle_repeats(md)
    assert "Currently, Rosa's monthly profit is $3,000." not in out
    assert "Her profit goes from $3,000 to $1,000 if she hires." in out
    assert not qa.repeated_figures(qa.sections(out))


def test_settle_repeats_replaces_the_number_when_the_sentence_has_new_facts():
    md = _script(**{"Hook": "Rosa runs a 30-seat taqueria in Austin and earns $3,000 a month.",
                    "Section 4: Decision": "On $3,000 a month she pays $700 in rent. Her profit goes from $3,000 "
                                           "to $1,000 if she hires."})
    out = qa.settle_repeats(md)
    assert "On that amount a month she pays $700 in rent." in out and "$700" in out
    assert not qa.repeated_figures(qa.sections(out))


def test_quality_gate_settles_repeats_the_llm_left(monkeypatch, tmp_path):
    """#105: quality_gate LLM raundlarindan sonra settle_repeats-i cagirir - tekrar problemi ile dayanmir."""
    import argparse
    md = _script(**{"Hook": "Rosa runs a 30-seat taqueria in Austin and earns $3,000 a month.",
                    "Section 4: Decision": "Currently, Rosa's monthly profit is $3,000. Her profit goes from $3,000 "
                                           "to $1,000 if she hires."})
    (tmp_path / "meta.json").write_text(json.dumps({"plan": PLAN}), encoding="utf-8")
    (tmp_path / "research.json").write_text(json.dumps(SOURCE), encoding="utf-8")
    path = tmp_path / "script.md"
    path.write_text(md, encoding="utf-8")
    monkeypatch.setattr(qa, "apply_fixes", lambda m, *a, **k: m)          # LLM tekrari duzeltmir (real probe)
    monkeypatch.setattr(qa, "review_loop", lambda m, *a, **k: (m, []))
    monkeypatch.setattr(sg, "verify_math", lambda a, p: None)
    a = argparse.Namespace(provider="openai", model=None, temperature=0.7, topic="Raise Prices?")
    try:
        sg.quality_gate(a, str(tmp_path), str(path))
    except SystemExit:
        pass                                   # fixturede basqa problemler ola biler - yalniz tekrar yoxlanir
    assert not qa.repeated_figures(qa.sections(path.read_text(encoding="utf-8")))


def test_settle_repeats_keeps_count_sentences_grammatical():
    """#108 (E2E 2026-10-09 real probe): '4' sayi 'that amount' ile evezlenirdi -> 'those that amount extra clients',
    '$800 divided by $200 equals that amount'. Teyinedicidən sonra say silinir, qalan yerde 'that many'."""
    md = _script(**{"Hook": "Rosa runs a 30-seat taqueria in Austin and needs 4 extra tables.",
                    "Section 4: Decision": "She needs 4 tables. So, $800 divided by $200 equals 4. If she adds those "
                                           "4 extra tables at $700, profit goes from $400 to $510 with 4 tables."})
    out = qa.sections(qa.settle_repeats(md))["Section 4: Decision"]
    assert "that amount" not in out and "those that" not in out
    assert "those extra tables" in out or "equals that many" in out
    assert not qa.repeated_figures(qa.sections(qa.settle_repeats(md)))


def test_settle_repeats_sees_spelled_out_mentions():
    """#117 (E2E №2 2026-10-09): 'three thousand dollars' sayilirdi (find_numbers), amma duzelis yalniz '$3,000'
    regexini axtarirdi -> drop=0, tekrar qalirdi, script_gen dusdu."""
    md = _script(**{"Hook": "Emily runs a coffee shop in Austin and the new spot costs $3,000 a month.",
                    "Section 4: Decision": "The new site costs three thousand dollars each month. She would earn "
                                           "$3,000 more from 300 new customers."})
    out = qa.settle_repeats(md)
    assert not qa.repeated_figures(qa.sections(out))
    assert "$3,000 more from 300 new customers" in out


def test_settle_repeats_never_points_that_amount_at_a_different_figure():
    """#118 (E2E №2 2026-10-09): '...she'll have $2,000 in profit. Currently ... yielding a monthly profit of $17,400'
    -> 'of that amount' = $2,000 kimi esidilir (yanlis fakt). Araliqda basqa reqem varsa cumle silinir."""
    md = _script(**{"Hook": "Sarah runs a coffee shop in Austin and earns $17,400 a month.",
                    "Section 4: Decision": "After $1,000 in costs, she keeps $2,000 from the new spot. Currently, "
                                           "she serves 300 customers, yielding $17,400 a month. Her profit goes "
                                           "from $17,400 to $19,400."})
    out = qa.sections(qa.settle_repeats(md))["Section 4: Decision"]
    assert "that amount" not in out
    assert "from $17,400 to $19,400" in out
    assert not qa.repeated_figures(qa.sections(qa.settle_repeats(md)))


def test_vague_reference_phrases_are_problems():
    """#119 (E2E №2): 'every extra customer brings in that same cost' ($5 idi), 'a significant amount' -
    reqem bos ifade ile evezlenmisdi, script_qa buraxdi."""
    secs = {"Section 2: Revenue": "Each customer brings in that same cost. She makes a significant amount.",
            "Section 3: Costs": "She earns that amount again."}
    probs = qa.vague_amount_problems(secs)
    assert any("that same cost" in p for p in probs) and any("a significant amount" in p for p in probs)
    assert not any("Section 3" in p for p in probs)       # settle_repeats-in 'that amount' geri istinadi qalir


def test_repeat_fix_instruction_does_not_suggest_placeholder_phrases():
    """#119: telimat 'that amount', 'the same cost' numune verirdi -> gpt-4o-mini 'that same cost' yazdi."""
    md = _script(**{"Hook": "Rosa runs a 30-seat taqueria in Austin and earns $3,000 a month.",
                    "Section 2: Costs": "Rosa earns $3,000 a month.",
                    "Section 4: Decision": "Her profit goes from $3,000 to $1,000 if she hires."})
    fixes = qa.story_fixes(md, PLAN, SOURCE, "Section 2: Costs")
    text = " ".join(f["instruction"] for f in fixes if "restated" in f["problem"])
    assert text and "the same cost" not in text and "'that amount'" not in text


ANALOGY_PLAN = {**PLAN, "sections": [{"domain": "grocery shopping"}, {"domain": "fitness goals"}]}


def test_settle_analogies_keeps_one_analogy_sentence_per_section():
    """#120 (E2E №2): analogiya 4 cumle idi (grocery cart, shopping trip...) - qayda: bir cumle (2026-10-07)."""
    md = _script(**{"Hook": "Rosa runs a 30-seat taqueria in Austin and earns $3,000 a month.",
                    "Section 2: Revenue": "Think of revenue like the total at the grocery store. When you fill your "
                                          "cart with groceries, the total climbs. That total is your shopping trip. "
                                          "Rosa multiplies 300 guests by $10 each.",
                    "Section 4: Decision": "Think of it like reaching your fitness goals. You need to know how many "
                                           "hours you have to work out. Rosa needs 40 more guests. This is like the "
                                           "calorie intake you need. Her profit goes from $3,000 to $1,000."})
    out = qa.sections(qa.settle_analogies(md, ANALOGY_PLAN))
    rev, dec = out["Section 2: Revenue"], out["Section 4: Decision"]
    assert rev.startswith("Think of revenue like the total at the grocery store.")
    assert "cart" not in rev and "shopping trip" not in rev and "Rosa multiplies 300 guests" in rev
    assert "work out" not in dec and "calorie" not in dec and "Rosa needs 40 more guests" in dec
    assert not qa.analogy_problems(out, ANALOGY_PLAN)
    assert qa.analogy_problems(qa.sections(md), ANALOGY_PLAN)


def test_settle_script_clears_every_deterministic_case_problem():
    """#109 (istifadeci 2026-10-09: 'qeti sekilde hell et'): 21 cehdin son problemleri hamisi deterministik siniflerdir
    (modelde olmayan reqem, deyisen buraxilib, evvel/sonra cutu, esik, tekrar, kohne menbe ili). LLM-e buraxilmir:
    settle_script modelden kenar cumleni silir, cutu/esiyi modelden yazir, ili elave edir."""
    import case_model as cm
    plan = _model_plan()
    md = _script(**{"Section 4: Decision": "Rosa would earn $9,999 more. Today Rosa keeps $400 a month. At the new "
                                           "price she keeps $510."})
    secs = qa.sections(md)
    assert any("Section 4" in p for p in cm.case_problems(md, plan, SOURCE))
    out = qa.settle_script(md, plan, SOURCE)
    assert "$9,999" not in out
    assert not [p for p in cm.case_problems(out, plan, SOURCE) if p.startswith("Section 4")]
    assert not qa.repeated_figures(qa.sections(out)) and secs


def test_settle_script_says_the_year_of_an_old_source():
    import research
    old = {**SOURCE, "year": 2019}
    md = _script()
    if not research.is_old(old) or qa.citation_problems(md, old) == []:
        pytest.skip("fixture source paragraph not old/cited")
    assert any("kohnedir" in p for p in qa.citation_problems(md, old))
    assert qa.citation_problems(qa.settle_script(md, _model_plan(), old), old) == []


def _split_pair_script():
    return _script(**{"Section 4: Decision": "Today Rosa keeps $400 a month. At the new price she keeps $510 if "
                                             "27 customers stay."})


def test_settle_decision_pair_states_before_and_after_in_one_sentence():
    """#107 (E2E 2026-10-09, GPT): butun redaktor/audit raundlari kecdi, yalniz 'evvel/sonra cutu eyni cumlede
    deyil' qaldi ($2,500 ve $500 ayri cumlelerde). LLM-e buraxilmir - cumle modelden deterministik elave olunur."""
    import case_model as cm
    plan = _model_plan()
    md = _split_pair_script()
    head = "Section 4: Decision"
    assert any("evvel/sonra" in p for p in cm._decision_section_problems(qa.sections(md)[head],
                                                                          plan["model_result"], head))
    out = qa.settle_decision_pair(md, plan)
    assert "Rosa's profit goes from $400 to $510." in out
    assert not cm._decision_section_problems(qa.sections(out)[head], plan["model_result"], head)
    assert qa.settle_decision_pair(out, plan) == out                    # artiq varsa toxunmur


def test_quality_gate_reaudits_when_the_number_audit_splits_the_pair(monkeypatch, tmp_path):
    """#107: reqem auditi abzasi yeniden yaza biler - cut itirse elave olunur ve audit yeniden isleyir (sha)."""
    import argparse
    plan = _model_plan()
    (tmp_path / "meta.json").write_text(json.dumps({"plan": plan}), encoding="utf-8")
    (tmp_path / "research.json").write_text(json.dumps(SOURCE), encoding="utf-8")
    path = tmp_path / "script.md"
    path.write_text(_split_pair_script(), encoding="utf-8")
    audits = []

    def audit(a, p):                                   # 1-ci audit cut cumlesini parcalayir (real probe)
        audits.append(p)
        if len(audits) == 1:
            path.write_text(_split_pair_script(), encoding="utf-8")
    monkeypatch.setattr(qa, "apply_fixes", lambda m, *a, **k: m)
    monkeypatch.setattr(qa, "review_loop", lambda m, *a, **k: (m, []))
    monkeypatch.setattr(sg, "verify_math", audit)
    a = argparse.Namespace(provider="openai", model=None, temperature=0.7, topic="Raise Prices?")
    try:
        sg.quality_gate(a, str(tmp_path), str(path))
    except SystemExit:
        pass
    assert len(audits) == 2
    assert "goes from $400 to $510" in path.read_text(encoding="utf-8")


def test_plan_and_repair_prompts_carry_the_model_example(monkeypatch):
    """#106: numune plan promptunda da, model temiri promptunda da olmalidir."""
    seen = []

    def stop(system, user, **kw):
        seen.append(user)
        raise sg.LLMError("stop")
    monkeypatch.setattr(sg, "chat_json", stop)
    with pytest.raises(sg.LLMError):
        sg.outline("Should You Hire Your First Employee?", provider="openai")
    with pytest.raises(sg.LLMError):
        sg.repair_model(_model_plan(), ["x"], provider="openai")
    assert len(seen) == 2 and all("EXAMPLE of a correct case model" in u for u in seen)


# #115 (E2E hire-first-employee): "her monthly profit stands at a specific amount" - yazan reqemi bulandirdi,
# yoxlamalar kecdi, izleyici qerar reqemini esitmedi
@pytest.mark.parametrize("phrase", ["a specific amount", "a certain amount", "some amount of money",
                                    "a particular number", "a certain percentage"])
def test_vague_placeholder_amount_is_a_problem(phrase):
    sec = f"Rosa keeps {phrase} of every sale. That is her margin."
    probs = qa.story_problems(_script(**{"Section 1: Margin": sec}), PLAN, SOURCE)
    assert any("Section 1: Margin" in p and "qeyri-mueyyen" in p for p in probs)


def test_back_reference_to_a_said_figure_is_not_vague():
    sec = "Rosa keeps $8 of every $100 in sales. That amount is her margin."
    assert qa.story_problems(_script(**{"Section 1: Margin": sec}), PLAN, SOURCE) == []


def test_vague_amount_fix_asks_for_the_exact_case_figure():
    md = _script(**{"Section 1: Margin": "Rosa keeps a specific amount of every sale. That is her margin."})
    fix = next(f for f in qa.story_fixes(md, PLAN, SOURCE, "Section 2: Demand") if f["section"] == "Section 1: Margin")
    assert "a specific amount" in fix["instruction"] and "CASE MODEL" in fix["instruction"]
