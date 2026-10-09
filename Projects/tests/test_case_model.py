"""Faza 1.1 (istifadeci 2026-10-07): strukturlu case modeli + deterministik qerar hesabi.
Xeta sinfi: qerar neticesi case-in bir deyisenini buraxir ("40 customers x $5 = $200 extra" - musteri itkisi
unudulub), ve ya case reqemleri ssenaride bir-biri ile uygunsuzdur ("out of 100 customers", case-de 40)."""
import pytest

import case_model as cm

MODEL = {
    "variables": [
        {"name": "customers", "value": 40, "unit": "customers", "label": "weekly customers"},
        {"name": "price_old", "value": 50, "unit": "$", "label": "current price"},
        {"name": "price_new", "value": 55, "unit": "$", "label": "new price"},
        {"name": "unit_cost", "value": 40, "unit": "$", "label": "cost per order"},
        {"name": "retention", "value": 0.85, "unit": "share", "label": "customers who stay"},
    ],
    "before": {"revenue": "customers × price_old", "profit": "customers × (price_old − unit_cost)"},
    "after": {"revenue": "customers × retention × price_new",
              "profit": "customers × retention × (price_new − unit_cost)"},
    "threshold": {"name": "customers_needed", "expr": "before_profit ÷ (price_new − unit_cost)",
                  "rounding": "ceil", "meaning": "customers needed at the new price to keep the old profit"},
}
PLAN = {"decision": "Should Rosa raise her price from $50 to $55?", "model": MODEL,
        "case": {"owner": "Rosa", "business": "a catering firm", "city": "Austin", "state": "Texas"}}


def _plan():
    return {**PLAN, "model_result": cm.evaluate(MODEL)}


def _script(decision: str, hook: str = "Rosa runs a catering firm in Austin with 40 customers a week.") -> str:
    return ("# Raise Prices?\n\n## Cold Open\n\nRevenue falls to $1,870, yet profit rises to $510.\n\n"
            f"## Hook\n\n{hook}\n\n## Section 1: Margin\n\nRosa charges $50 and each order costs her $40.\n\n"
            f"## Section 2: Decision\n\n{decision}\n\n## Recap\n\nKnow your margin.\n")


def test_before_after_delta_and_threshold_are_computed():
    r = cm.evaluate(MODEL)
    assert r["before"] == {"revenue": 2000, "profit": 400}
    assert r["after"] == pytest.approx({"revenue": 1870, "profit": 510})
    assert r["delta"] == pytest.approx({"revenue": -130, "profit": 110})
    assert r["threshold"]["value"] == 27            # ceil(400 / 15)
    assert r["units"]["revenue"] == "$" and r["units"]["profit"] == "$"
    assert r["threshold"]["unit"] != "$"              # $ / $ = say


def test_insight_is_the_surprising_result_with_a_number():
    r = cm.evaluate(MODEL)
    assert "$1,870" in r["insight"] and "$510" in r["insight"]
    import script_qa
    assert script_qa.cold_open_problems(r["insight"]) == []


def test_expressions_never_use_eval():
    bad = {**MODEL, "after": {"revenue": "__import__('os').system('x')"}}
    with pytest.raises(cm.CaseModelError):
        cm.evaluate(bad)


def test_unknown_name_is_an_error():
    with pytest.raises(cm.CaseModelError):
        cm.evaluate({**MODEL, "after": {"revenue": "customers * price_newest"}})


def test_circular_reference_is_an_error():
    with pytest.raises(cm.CaseModelError):
        cm.evaluate({**MODEL, "before": {"a": "b + 1", "b": "a * 2"}})


def test_threshold_is_mandatory():
    with pytest.raises(cm.CaseModelError):
        cm.evaluate({k: v for k, v in MODEL.items() if k != "threshold"})


def test_results_may_reference_each_other_inside_a_block():
    m = {**MODEL, "before": {"revenue": "customers * price_old", "cost": "customers * unit_cost",
                              "profit": "revenue - cost"}}
    assert cm.evaluate(m)["before"]["profit"] == 400


def test_correct_decision_section_passes():
    md = _script("Rosa keeps 34 customers. Revenue drops from $2,000 to $1,870, but profit climbs from $400 to $510. "
                 "She needs at least 27 customers at the new price.")
    assert cm.case_problems(md, _plan()) == []


def test_naive_calculation_that_drops_a_variable_is_caught():
    md = _script("If Rosa raises her price, 40 customers × $5 = $200 extra each week.")
    probs = cm.case_problems(md, _plan())
    assert any("deyisen buraxilib" in p and "retention" in p for p in probs), probs


def test_case_quantity_that_contradicts_the_model_is_caught():
    md = _script("Rosa keeps 34 customers. Revenue drops to $1,870, but profit climbs to $510.",
                 hook="Rosa runs a catering firm in Austin. Out of 100 customers, most stay.")
    probs = cm.case_problems(md, _plan())
    assert any("100 customers" in p for p in probs), probs


def test_decision_figure_not_in_model_is_caught():
    md = _script("Profit climbs to $640 after the change.")
    probs = cm.case_problems(md, _plan())
    assert any("$640" in p for p in probs), probs


def test_allowed_numbers_contain_model_values():
    nums = cm.allowed_numbers(cm.evaluate(MODEL))
    for v in (40, 50, 55, 0.85, 85, 2000, 1870, 400, 510, 130, 110, 27, 5, 34, 6):
        assert any(abs(v - x) < 1e-6 for x in nums), v


def test_threshold_may_use_rounding_functions_and_bare_result_names():
    """Real probe 2026-10-07: LLM 'ceil(...)' ve prefikssiz 'monthly_cost' yazdi."""
    m = {**MODEL, "threshold": {"name": "n", "expr": "ceil(profit / (price_new - unit_cost))", "rounding": "none",
                                "meaning": "m"}}
    with pytest.raises(cm.CaseModelError):           # 'profit' iki blokda ferqlidir - qeyri-mueyyen
        cm.evaluate(m)
    m2 = {**MODEL, "before": {**MODEL["before"], "fixed": "unit_cost * 10"},
          "threshold": {"name": "n", "expr": "ceil(fixed / (price_new - unit_cost))", "rounding": "none",
                        "meaning": "m"}}
    assert cm.evaluate(m2)["threshold"]["value"] == 27


def test_only_safe_functions_are_allowed():
    with pytest.raises(cm.CaseModelError):
        cm.evaluate({**MODEL, "after": {"revenue": "open(customers)"}})


@pytest.mark.parametrize("name, value, unit", [
    ("employee_hourly_wage", 15, "$"), ("monthly_lease_cost", 2000, "$"), ("retention_rate", 0.8, "share"),
    ("current_customers", 40, "customers"), ("discount_percent", 10, "%")])
def test_missing_unit_is_inferred_from_the_name(name, value, unit):
    """Real probe 2026-10-07: unit-siz deyisen -> insight '$840' evezine '840'; LLM 5 cehdde vahid yazmadi."""
    m = {**MODEL, "variables": MODEL["variables"] + [{"name": name, "value": value}]}
    assert cm.evaluate(m)["var_units"][name] == unit


def test_rejection_hint_lists_the_names_a_formula_may_use():
    """Real probe 2026-10-07: LLM 5 cehdde eyni namelum adi (monthly_revenue_after) tekrarladi."""
    hint = cm.names_hint(MODEL)
    assert "customers" in hint and "before_profit" in hint and "after_revenue" in hint and "delta_profit" in hint


def test_after_block_may_refer_to_the_before_value_of_its_own_key():
    """Real probe 2026-10-07: after {"monthly_hours": "monthly_hours * 1.5"} - 'dovri istinad' deyil, evvelki deyer."""
    m = {**MODEL, "before": {**MODEL["before"], "hours": "customers * 2"},
         "after": {**MODEL["after"], "hours": "hours * 1.5", "orders": "customers"}}
    r = cm.evaluate(m)
    assert r["after"]["hours"] == 120 and r["before"]["hours"] == 80


def test_after_block_may_use_a_before_only_key():
    m = {**MODEL, "before": {**MODEL["before"], "base": "customers * 2"},
         "after": {**MODEL["after"], "base2": "base + 1"}}
    assert cm.evaluate(m)["after"]["base2"] == 81


def test_variable_may_share_its_name_with_a_result_key():
    """Real probe 2026-10-07: deyisen 'monthly_cost' + after {"monthly_cost": "monthly_cost + 100"} 5 cehdde."""
    m = {**MODEL, "variables": MODEL["variables"] + [{"name": "monthly_cost", "value": 500, "unit": "$"}],
         "before": {**MODEL["before"], "monthly_cost": "monthly_cost"},
         "after": {**MODEL["after"], "monthly_cost": "monthly_cost + 100"}}
    r = cm.evaluate(m)
    assert r["before"]["monthly_cost"] == 500 and r["after"]["monthly_cost"] == 600


def test_bare_name_in_threshold_prefers_the_input_variable():
    """Real probe 2026-10-07: threshold-da 'monthly_cost' hem deyisen, hem before/after acari idi - 5 cehd."""
    m = {**MODEL, "variables": MODEL["variables"] + [{"name": "monthly_cost", "value": 450, "unit": "$"}],
         "before": {**MODEL["before"], "monthly_cost": "monthly_cost"},
         "after": {**MODEL["after"], "monthly_cost": "monthly_cost + 100"},
         "threshold": {"name": "n", "expr": "monthly_cost / (price_new - unit_cost)", "rounding": "ceil",
                       "meaning": "m"}}
    assert cm.evaluate(m)["threshold"]["value"] == 30


def test_prefixed_names_work_inside_blocks_too():
    """Real probe 2026-10-07: LLM after blokunda 'before_monthly_cost' yazdi (5 cehd)."""
    m = {**MODEL, "after": {**MODEL["after"], "gain": "after_profit - before_profit"}}
    assert cm.evaluate(m)["after"]["gain"] == 110


def test_threshold_only_insight_reads_cleanly():
    """Real probe 2026-10-07: 'Everything hinges on 300: This is the amount ... running out..'"""
    m = {**MODEL, "after": dict(MODEL["before"]),
         "threshold": {**MODEL["threshold"], "meaning": "This is the stock you need."}}
    text = cm.evaluate(m)["insight"]
    assert ".." not in text and ": this is" in text


def test_model_errors_reach_the_llm_in_english():
    """Real probe 2026-10-07: 'threshold musbet deyil ... dustur sehvdir' LLM-e gedirdi - 15 cehd eyni xeta."""
    import script_qa as qa
    for bad in ({**MODEL, "after": {"revenue": "customers * nope"}},
                {**MODEL, "threshold": {**MODEL["threshold"], "expr": "after_revenue - before_revenue - 500"}}):
        probs = qa.plan_problems({"decision": "Should Rosa raise prices?", "answer": "Do it if 27 stay.",
                                  "case": {"state": "Texas"}, "model": bad})
        msg = " ".join(p for p in probs if "model" in p)
        assert any(w in msg for w in ("unknown name", "must be positive")), msg


def test_threshold_name_inside_a_block_gets_a_clear_message():
    """Real probe 2026-10-07: repair 'customer_loss_threshold'-u after-e qoydu - 15 cehd 'unknown name'."""
    m = {**MODEL, "after": {**MODEL["after"], "x": "customers_needed + 1"}}
    with pytest.raises(cm.CaseModelError, match="computed FROM before/after"):
        cm.evaluate(m)


def test_negative_money_is_formatted_with_the_sign_first():
    """Real probe 2026-10-07: insight '$-50'."""
    assert cm.fmt(-50, "$") == "-$50" and cm.fmt(-1250.5, "$") == "-$1,250.5" and cm.fmt(-5, "%") == "-5%"


def test_difference_of_count_variables_is_a_derived_figure():
    """Real probe 2026-10-07: 150 musteri - 15 itki = 135 'modelde yoxdur' sayildi."""
    m = {**MODEL, "variables": MODEL["variables"] + [{"name": "lost", "value": 10, "unit": "customers"}]}
    assert any(abs(x - 30) < 1e-6 for x in cm.allowed_numbers(cm.evaluate(m)))


def test_a_loss_said_without_its_sign_is_a_model_value():
    """#94 (E2E 2026-10-08, hire-first-employee): model -$450 heftelik menfeet verir, skript "a loss of $450" deyir ->
    450 = deyisen buraxilmis naive netice ile ust-uste dusdu, 'deyisen buraxilib' sayildi, script_gen dayandi."""
    m = {"variables": [{"name": "customers", "value": 150, "unit": "customers"},
                       {"name": "price", "value": 5, "unit": "$"},
                       {"name": "owner_hours", "value": 60, "unit": "hours"},
                       {"name": "new_hours", "value": 20, "unit": "hours"},
                       {"name": "wage", "value": 15, "unit": "$"}],
         "before": {"weekly_profit": "customers * price - owner_hours * wage"},
         "after": {"weekly_profit": "customers * price - (owner_hours + new_hours) * wage"},
         "threshold": {"name": "break_even", "expr": "(owner_hours + new_hours) * wage / price", "rounding": "ceil",
                       "meaning": "customers needed"}}
    allowed = cm.allowed_numbers(cm.evaluate(m))
    assert any(abs(x - 450) < 1e-6 for x in allowed) and 450.0 not in cm.naive_values(m)


def test_loss_pair_without_signs_counts_as_the_before_after_pair():
    """#94: 'her weekly loss grows from $150 to $450' - itki ishresiz deyilir, cut taninmali."""
    r = {"before": {"weekly_profit": -150.0}, "after": {"weekly_profit": -450.0}, "delta": {"weekly_profit": -300.0},
         "units": {"weekly_profit": "$"}, "threshold": {"value": 240.0, "raw": 240.0, "unit": "customers"}}
    probs = cm._decision_section_problems("Her weekly loss grows from $150 to $450. She needs 240 customers.", r, "S4")
    assert probs == []


def test_profit_must_subtract_costs():
    """#96 (E2E 2026-10-08, hire-first-employee): model 'weekly_profit = weekly_sales' (xercsiz menfeet) gpt-4o
    hakimden kecdi -> skript "profit $3,200 after expenses" dedi, redaktor 'ziddiyyet' tapdi."""
    m = {"variables": [{"name": "weekly_sales", "value": 4000, "unit": "$"},
                       {"name": "employee_cost", "value": 800, "unit": "$"}],
         "before": {"weekly_profit": "weekly_sales"},
         "after": {"weekly_profit": "weekly_sales - employee_cost"},
         "threshold": {"name": "t", "expr": "employee_cost / 20", "rounding": "ceil", "meaning": "x"}}
    with pytest.raises(cm.CaseModelError, match="profit"):
        cm.evaluate(m)
    ok = {**m, "variables": m["variables"] + [{"name": "costs", "value": 2500, "unit": "$"}],
          "before": {"weekly_profit": "weekly_sales - costs", "monthly_profit": "weekly_profit * 4"},
          "after": {"weekly_profit": "weekly_sales - costs - employee_cost"}}
    cm.evaluate(ok)


def test_count_threshold_is_not_matched_by_a_hundredfold_money_figure():
    """#95 (E2E 2026-10-08): esik 40 musteri, bolmede yalniz '$4,000' (=40*100) var -> 'esik deyilib' sayildi,
    skript 40-i hec demedi, redaktor 'qerar cavablanmir' dedi."""
    r = {"before": {"p": 4000.0}, "after": {"p": 3200.0}, "delta": {"p": -800.0}, "units": {"p": "$"},
         "threshold": {"value": 40.0, "raw": 40.0, "unit": ""}}
    probs = cm._decision_section_problems("Profit goes from $4,000 to $3,200.", r, "S4")
    assert any("threshold" in p for p in probs), probs


def test_threshold_counted_in_a_variable_must_move_the_decision():
    """#98 (E2E 2026-10-08, hire-first-employee): esik '60 customers', amma delta musteri sayindan asili deyil
    (iscinin xerci sabit) -> Sarah 80 musteri ile 'esiyi kecib', yene zerer artir; redaktor 'ziddiyyet', 3 raund."""
    m = {"variables": [{"name": "weekly_customers", "value": 80, "label": "customers per week"},
                       {"name": "price_per_item", "value": 5, "unit": "$"},
                       {"name": "rent", "value": 300, "unit": "$"},
                       {"name": "hourly_wage", "value": 15, "unit": "$"}],
         "before": {"weekly_profit": "weekly_customers * price_per_item - rent"},
         "after": {"weekly_profit": "weekly_customers * price_per_item - rent - hourly_wage * 20"},
         "threshold": {"name": "break_even_customers", "expr": "hourly_wage * 20 / price_per_item",
                       "rounding": "ceil", "meaning": "the minimum number of customers needed to cover the new employee"}}
    msg = cm.threshold_link_problem(m, cm.evaluate(m))
    assert msg and "weekly_customers" in msg
    assert cm.threshold_link_problem(MODEL, cm.evaluate(MODEL)) is None


def test_threshold_link_accepts_any_variable_of_the_same_noun():
    """#98 real probe: 'weekly_customers' + 'new_customers_per_employee' - delta ikinciden asilidir, yalniz birinci
    yoxlanirdi -> duzgun model 'not linked' ile redd olundu (plan 4 defe redd)."""
    m = {"variables": [{"name": "new_customers_per_employee", "value": 50, "unit": "customers"},
                       {"name": "weekly_customers", "value": 200, "unit": "customers"},
                       {"name": "price", "value": 5, "unit": "$"}, {"name": "rent", "value": 300, "unit": "$"},
                       {"name": "wage_cost", "value": 200, "unit": "$"}],
         "before": {"weekly_profit": "weekly_customers * price - rent"},
         "after": {"weekly_profit": "(weekly_customers + new_customers_per_employee) * price - rent - wage_cost"},
         "threshold": {"name": "need", "expr": "wage_cost / price", "rounding": "ceil",
                       "meaning": "extra customers needed to pay the employee"}}
    assert cm.threshold_link_problem(m, cm.evaluate(m)) is None


def test_plan_prompt_says_what_an_added_cost_brings():
    """#98: 'hire first employee' plan modeli 4 defe xerci sabit yazdi (delta musteriden asili deyil) - telimat
    elave xercin getirdiyini (extra customers) modelde gostermeyi deyir."""
    import script_gen as sg
    text = sg.OUTLINE_USER.lower()
    assert "adds a cost" in text and "revenue minus" in text


def test_profit_minus_zero_is_still_without_costs():
    """#99 (E2E 2026-10-08): #96-dan sonra LLM 'weekly_revenue - 0' yazdi - cixilan terefde deyisen olmalidir."""
    m = {"variables": [{"name": "weekly_revenue", "value": 6000, "unit": "$"},
                       {"name": "employee_cost", "value": 1000, "unit": "$"}],
         "before": {"weekly_profit": "weekly_revenue - 0"},
         "after": {"weekly_profit": "weekly_revenue - employee_cost"},
         "threshold": {"name": "t", "expr": "employee_cost / 20", "rounding": "ceil", "meaning": "x"}}
    with pytest.raises(cm.CaseModelError, match="profit"):
        cm.evaluate(m)


def test_intermediate_of_a_model_formula_is_an_allowed_figure():
    """#100 (E2E 2026-10-08): '$20 per customer' = weekly_revenue / weekly_customers modelin oz dusturunda var,
    amma 'case modelinde yoxdur' sayildi."""
    m = {"variables": [{"name": "weekly_customers", "value": 300, "unit": "customers"},
                       {"name": "weekly_revenue", "value": 6000, "unit": "$"},
                       {"name": "costs", "value": 4000, "unit": "$"},
                       {"name": "extra_customers", "value": 150, "unit": "customers"},
                       {"name": "employee_cost", "value": 1000, "unit": "$"}],
         "before": {"weekly_profit": "weekly_revenue - costs"},
         "after": {"weekly_profit": "weekly_revenue + extra_customers * (weekly_revenue / weekly_customers) "
                                    "- costs - employee_cost"},
         "threshold": {"name": "need", "expr": "employee_cost / (weekly_revenue / weekly_customers)",
                       "rounding": "ceil", "meaning": "extra customers needed"}}
    allowed = cm.allowed_numbers(cm.evaluate(m))
    assert any(abs(x - 20) < 1e-9 for x in allowed) and any(abs(x - 3000) < 1e-9 for x in allowed)


def test_insight_verb_agrees_with_a_plural_label():
    """#103 real probe: Cold Open 'Monthly costs rises from $4,400 to $11,000.'"""
    r = {"before": {"monthly_costs": 4400.0}, "after": {"monthly_costs": 11000.0}, "delta": {"monthly_costs": 6600.0},
         "units": {"monthly_costs": "$"}, "labels": {}, "threshold": {"value": 20.0, "unit": "", "meaning": "m"}}
    assert cm.insight(r).startswith("Monthly costs rise from $4,400")


def test_model_example_for_added_cost_decisions_passes_every_rule():
    """#106 (E2E 2026-10-08): gpt-4o-mini 'hire' modelini 5 cehdde hakimden kecire bilmedi (xerc sabit, hedd bagli
    deyil). Plan promptuna isleyen numune (yalniz STRUKTUR) verilir - numunenin ozu butun qaydalardan kecmelidir."""
    import script_gen as sg
    r = cm.evaluate(sg.MODEL_EXAMPLE)
    assert cm.threshold_link_problem(sg.MODEL_EXAMPLE, r) is None and r["threshold"]["value"] > 0
    assert "structure only" in sg.model_example_text().lower()


# --- #136 (2026-10-10 reproduksiya: 5 plandan 3-4-u ziddiyyetli) ------------------------------------------------
# Real probe planlari ("Should You Raise Your Menu Prices?"): LLM threshold-un adini/menasini bir kemiyyet, expr-ini
# basqa kemiyyet kimi yazirdi ("customers_lost" = saxlanmali musteri), cavab bu menadan yazilirdi.

def _menu(after, extra=None, before="weekly_customers * (price_per_meal - cost_per_meal)"):
    variables = [{"name": "weekly_customers", "value": 200, "unit": "customers", "label": "customers served each week"},
                 {"name": "price_per_meal", "value": 15, "unit": "$", "label": "current menu price per meal"},
                 {"name": "cost_per_meal", "value": 8, "unit": "$", "label": "cost to prepare each meal"},
                 {"name": "new_price", "value": 18, "unit": "$", "label": "new menu price per meal"}] + (extra or [])
    return {"variables": variables, "before": {"weekly_profit": before}, "after": {"weekly_profit": after},
            "threshold": {"name": "customers_lost", "expr": "before_weekly_profit / (new_price - cost_per_meal)",
                          "rounding": "ceil", "meaning": "customers lost that keep profit the same"}}


LOST = [{"name": "expected_customers_lost", "value": 20, "unit": "customers", "label": "customers lost each week"}]
SHARE = [{"name": "customer_loss_rate", "value": 0.1, "unit": "share", "label": "share of customers who leave"}]


def test_decision_rule_is_the_break_even_of_the_change_variable():
    from decision_visuals import decision_rule
    m = _menu("(weekly_customers - expected_customers_lost) * (new_price - cost_per_meal)", LOST)
    rule = decision_rule(m, cm.evaluate(m))
    assert rule["var"] == "expected_customers_lost" and rule["value"] == 60 and rule["direction"] == "max"
    assert rule["text"] == "Make the change only if customers lost each week stays at 60 or less."


def test_share_threshold_is_spoken_as_a_percent():
    from decision_visuals import decision_rule
    m = _menu("weekly_customers * (1 - customer_loss_rate) * (new_price - cost_per_meal)", SHARE)
    rule = decision_rule(m, cm.evaluate(m))
    assert rule["var"] == "customer_loss_rate" and abs(rule["value"] - 0.3) < 1e-9
    assert "30% or less" in rule["text"]


def test_price_rise_without_a_downside_has_no_decision_rule():
    from decision_visuals import decision_rule
    m = _menu("weekly_customers * (new_price - cost_per_meal)")
    m["threshold"] = {**m["threshold"], "expr": "new_price * 10"}      # esik kesisme deyil, mensi tesir yoxdur
    assert decision_rule(m, cm.evaluate(m)) is None
    import script_qa
    plan = {"decision": "Should I raise my menu prices?", "answer": "Make the change if 140 customers stay.",
            "case": {"owner": "Lisa", "business": "cafe", "city": "Austin", "state": "Texas"}, "model": m}
    assert any("break-even" in p for p in script_qa.plan_problems(plan))


def test_settled_plan_gets_the_computed_threshold_and_answer():
    import script_gen
    m = _menu("(weekly_customers - expected_customers_lost) * (new_price - cost_per_meal)", LOST)
    plan = script_gen.apply_decision_rule({"model": m, "answer": "Make the change if you lose under 140."})
    r = cm.evaluate(plan["model"])
    assert r["threshold"]["value"] == 60 and "60 or less" in plan["answer"]
    assert "customers lost each week" in r["threshold"]["meaning"]
