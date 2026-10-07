"""Videoda hesablama sehvi olmur (istifadeci 2026-09-30).
Real hal (payment-fees): "100 dishes/week -> $20 savings. Over a month, that's eight hundred dollars."
LLM yalniz hesablamani ifade kimi cixarir; iddia olunan reqem metnden, netice Python-da hesablanir."""
import json

import pytest

import math_check as mc

REAL_BUG = """# Fees

## Section 4: Choosing the Right Processor

Let's say your restaurant sells a dish for twenty dollars. With the two percent processor, you lose forty cents on that sale. But with the one percent option, you only lose twenty cents. If you sell just a hundred dishes in a week, that's a savings of twenty dollars. Over a month, that's eight hundred dollars.

## Recap

Fees matter.
"""


@pytest.mark.parametrize("text,value", [
    ("eight hundred dollars", 800), ("twenty cents", 0.20), ("forty cents", 0.40),
    ("two dollars and fifty cents", 2.5), ("fifteen percent", 15), ("a hundred", 100),
    ("one thousand two hundred", 1200), ("$1,200", 1200), ("$39.99", 39.99), ("12%", 12),
    ("two point five", 2.5), ("three-dollar", 3), ("twenty-five", 25), ("six hundred dollars", 600),
    ("half", 0.5), ("1.5 million", 1_500_000),
    # why-9-99 2026-10-04: "saving money, even if it's just a dollar" (fark 1 sent) audit-e dusmurdu,
    # "nine ninety-nine" 108 oxunurdu
    ("a dollar", 1), ("a cent", 0.01), ("nine ninety-nine", 9.99), ("four ninety-nine", 4.99),
])
def test_parse_number_reads_spoken_and_digit_forms(text, value):
    assert mc.parse_number(text) == pytest.approx(value)


def test_parse_number_returns_none_without_a_number():
    assert mc.parse_number("a lot of money") is None


def test_safe_eval_computes_arithmetic_only():
    assert mc.safe_eval("20 * 4") == 80
    assert mc.safe_eval("(10 - 2) / 10 * 100") == 80
    with pytest.raises(ValueError):
        mc.safe_eval("__import__('os')")


def test_numeric_sentences_finds_every_sentence_with_a_number():
    sents = mc.numeric_sentences(REAL_BUG)
    texts = [s["sentence"] for s in sents]
    assert "Over a month, that's eight hundred dollars." in texts
    assert "Fees matter." not in texts
    assert all(s["section"] == "Section 4: Choosing the Right Processor" for s in sents)


def _item(sid, expr, claimed, approx=False):
    return {"id": sid, "calc": True, "expr": expr, "claimed_text": claimed, "approx": approx}


def _full(sents, items):
    """Qalan reqemli cumleler "hesablama deyil" kimi qaytarilir (LLM her cumleye cavab verir)."""
    given = {it["id"] for it in items}
    return items + [{"id": s["id"], "calc": False} for s in sents if s["id"] not in given]


def test_real_bug_monthly_total_is_caught():
    sents = mc.numeric_sentences(REAL_BUG)
    month = next(s for s in sents if s["sentence"].startswith("Over a month"))
    items = [_item(month["id"], "20 * 4", "eight hundred dollars")]
    problems = mc.check_items(sents, _full(sents, items))
    assert len(problems) == 1
    assert problems[0]["correct"] == pytest.approx(80)
    assert problems[0]["claimed"] == pytest.approx(800)


def test_claimed_value_comes_from_sentence_not_from_llm():
    """LLM iddianı yanlis oxusa bele (metnde olmayan soz) - problem sayilir, kecmir."""
    sents = mc.numeric_sentences(REAL_BUG)
    month = next(s for s in sents if s["sentence"].startswith("Over a month"))
    problems = mc.check_items(sents, _full(sents, [_item(month["id"], "20 * 4", "eighty dollars")]))
    assert problems and "metnde yoxdur" in problems[0]["reason"]


def test_correct_math_passes_and_percent_scale_is_accepted():
    md = REAL_BUG.replace("eight hundred dollars", "eighty dollars")
    sents = mc.numeric_sentences(md)
    by = {s["sentence"][:12]: s["id"] for s in sents}
    items = [_item(by["With the two"], "20 * 2 / 100", "forty cents"),
             _item(by["Over a month"], "20 * 4", "eighty dollars")]
    assert mc.check_items(sents, _full(sents, items)) == []
    fifteen = "You keep seventeen of twenty dollars. That's a loss of fifteen percent."
    s2 = mc.numeric_sentences(f"## Section 1: X\n\n{fifteen}\n")
    loss = [_item(s2[-1]["id"], "(20 - 17) / 20", "fifteen percent")]
    assert mc.check_items(s2, _full(s2, loss)) == []


def test_approximate_claims_get_ten_percent_tolerance():
    md = "## Section 1: X\n\nTwenty dollars a week is roughly eighty-five dollars a month.\n"
    s = mc.numeric_sentences(md)
    assert mc.check_items(s, [_item(s[0]["id"], "20 * 4.33", "eighty-five dollars", approx=True)]) == []
    assert mc.check_items(s, [_item(s[0]["id"], "20 * 4.33", "eighty-five dollars", approx=False)])


def test_unaudited_numeric_sentence_is_a_problem():
    sents = mc.numeric_sentences(REAL_BUG)
    problems = mc.check_items(sents, [])
    assert {p["id"] for p in problems} == {s["id"] for s in sents}
    assert all("yoxlanmayib" in p["reason"] for p in problems)


def test_audit_and_fix_rewrites_until_math_is_correct():
    def extract(sents):
        out = []
        for s in sents:
            t = s["sentence"]
            if t.startswith("Over a month"):
                claimed = "eighty dollars" if "eighty" in t else "eight hundred dollars"
                out.append(_item(s["id"], "20 * 4", claimed))
            else:
                out.append({"id": s["id"], "calc": False})
        return out

    calls = []

    def rewrite(paragraph, problems):
        calls.append(problems)
        return {p["id"]: p["sentence"].replace("eight hundred dollars", "eighty dollars") for p in problems}

    md, problems = mc.audit_and_fix(REAL_BUG, extract, rewrite)
    assert problems == []
    assert "eighty dollars" in md and "eight hundred" not in md
    assert len(calls) == 1 and calls[0][0]["correct"] == pytest.approx(80)


def test_audit_and_fix_reports_problems_when_rewrite_cannot_fix():
    def extract(sents):
        return [_item(s["id"], "20 * 4", "eight hundred dollars") if s["sentence"].startswith("Over")
                else {"id": s["id"], "calc": False} for s in sents]

    _, problems = mc.audit_and_fix(REAL_BUG, extract, lambda p, probs: {}, rounds=2)
    assert problems


def test_report_is_bound_to_exact_script_text(tmp_path):
    """verify_script: yoxlanmamis ve ya yoxlamadan sonra deyisen skript kecmir."""
    ep = tmp_path
    (ep / "script.md").write_text(REAL_BUG, encoding="utf-8")
    assert mc.report_problems(str(ep))  # hesabat yoxdur
    mc.write_report(str(ep), REAL_BUG, [])
    assert mc.report_problems(str(ep)) == []
    (ep / "script.md").write_text(REAL_BUG + "\nMore.\n", encoding="utf-8")
    assert mc.report_problems(str(ep))  # skript deyisib
    mc.write_report(str(ep), REAL_BUG + "\nMore.\n", [{"sentence": "x", "reason": "sehv"}])
    assert mc.report_problems(str(ep))
    assert json.loads((ep / "math_check.json").read_text(encoding="utf-8"))["problems"]


def test_verify_script_stage_fails_without_math_report(tmp_path):
    import stages
    import script_qa
    md = REAL_BUG.replace("## Recap", "## Cold Open\n\nx\n\n## Hook\n\nx\n\n## Section 1: a\n\nx\n\n"
                                      "## Section 2: b\n\nx\n\n## Section 3: c\n\nx\n\n## Common Mistakes\n\nx\n\n"
                                      "## Call to Action\n\nx\n\n## Recap")
    (tmp_path / "script.md").write_text(md, encoding="utf-8")
    ctx = stages.Ctx(topic="t", slug="s", ep_dir=str(tmp_path), words=1230, music=None,
                     min_seconds=480, max_seconds=600, provider="openai")
    script_qa.write_report(str(tmp_path), md, [])      # #59 hesabati ayrica yoxlanir (test_script_story.py)
    assert any("hesab" in p for p in stages.verify_script(ctx))
    mc.write_report(str(tmp_path), md, [])
    assert stages.verify_script(ctx) == []


def test_script_prompt_demands_explicit_simple_math():
    import script_gen as sg
    assert "calculation" in sg.SYSTEM.lower()
    assert "four weeks" in sg.SYSTEM.lower()


def test_formula_with_numbers_not_in_text_is_rejected():
    """LLM iddiaya uygunlasdirmaq ucun ifade uydursa (200 * 4) - kecmir."""
    sents = mc.numeric_sentences(REAL_BUG)
    month = next(s for s in sents if s["sentence"].startswith("Over a month"))
    problems = mc.check_items(sents, _full(sents, [_item(month["id"], "200 * 4", "eight hundred dollars")]))
    assert problems and "olmayan reqem" in problems[0]["reason"]
    bare = mc.check_items(sents, _full(sents, [_item(month["id"], "800", "eight hundred dollars")]))
    assert bare and "hesablama deyil" in bare[0]["reason"]


def test_rewrite_changes_only_the_wrong_sentence():
    """Real hal: abzasi butov yeniden yazan LLM qonsu cumlede yeni sehv etdi (three-dollar -> two-dollar)."""
    def extract(sents):
        return _full(sents, [_item(s["id"], "20 * 4", "eight hundred dollars") for s in sents
                             if s["sentence"].startswith("Over") and "eight hundred" in s["sentence"]])

    def rewrite(paragraph, problems):
        return {p["id"]: "Over a month, that's eighty dollars." for p in problems} | {1: "Sabotage one."}

    md, problems = mc.audit_and_fix(REAL_BUG, extract, rewrite)
    assert problems == []
    assert "Over a month, that's eighty dollars." in md
    assert "Let's say your restaurant sells a dish for twenty dollars." in md
    assert "Sabotage" not in md


def test_cents_result_matches_dollar_claim():
    md = ("## Section 1: X\n\nWith two percent you lose forty cents. With one percent you lose twenty cents. "
          "That's a difference of twenty cents per dish.\n")
    s = mc.numeric_sentences(md)
    diff = next(x for x in s if "difference" in x["sentence"])
    assert mc.check_items(s, _full(s, [_item(diff["id"], "40 - 20", "twenty cents")])) == []
    assert mc.check_items(s, _full(s, [_item(diff["id"], "0.40 - 0.20", "twenty cents")])) == []
    assert mc.check_items(s, _full(s, [_item(diff["id"], "0.40 - 0.30", "twenty cents")]))


def _month(sents):
    return next(s for s in sents if s["sentence"].startswith("Over a month"))


def test_single_sloppy_pass_cannot_flag_a_correct_sentence():
    """Real hal: bir cavab '20 * 4 * 100' yazdi ve duzgun '80'-i '8000'-e 'duzeltdi'."""
    md = REAL_BUG.replace("eight hundred dollars", "eighty dollars")
    s = mc.numeric_sentences(md)
    good = _full(s, [_item(_month(s)["id"], "20 * 4", "eighty dollars")])
    sloppy = _full(s, [_item(_month(s)["id"], "20 * 4 * 100", "eighty dollars")])
    assert mc.judge(s, [good, sloppy, good]) == []


def test_majority_agreeing_on_the_correct_value_flags_the_error():
    s = mc.numeric_sentences(REAL_BUG)
    a = _full(s, [_item(_month(s)["id"], "20 * 4", "eight hundred dollars")])
    b = _full(s, [_item(_month(s)["id"], "20 * 4 * 100", "eight hundred dollars")])
    probs = mc.judge(s, [a, b, a])
    assert len(probs) == 1 and probs[0]["correct"] == pytest.approx(80)


def test_malformed_answers_do_not_vote():
    """'losing money on sales' (reqemsiz iddia) ve '3' (operatorsuz ifade) - reqem uydurmaga sebeb olmur."""
    s = mc.numeric_sentences(REAL_BUG)
    bad = _full(s, [_item(_month(s)["id"], "3", "eight hundred dollars")])
    ok = _full(s, [])
    assert mc.judge(s, [bad, ok, ok]) == []
    none = [[_item(x["id"], "3", "zzz") for x in s]] * 3
    assert all("yoxlanmayib" in p["reason"] for p in mc.judge(s, none))


def test_rewrite_without_the_correct_value_is_rejected():
    def extract(sents):
        return _full(sents, [_item(s["id"], "20 * 4", "eight hundred dollars") for s in sents
                             if s["sentence"].startswith("Over") and "eight hundred" in s["sentence"]])

    md, problems = mc.audit_and_fix(REAL_BUG, extract,
                                    lambda p, pr: {x["id"]: "Over a month, that's eight thousand dollars."
                                                   for x in pr}, rounds=1)
    assert "eight thousand" not in md
    assert problems


def test_youtube_metadata_prompt_forbids_numbers_and_calculations():
    """Description/basliq/thumbnail yoxlanmir - ona gore orada hesab/reqem ümumiyyetle olmur."""
    import publish_pack as pp
    assert "no numbers" in pp.SYSTEM.lower()


def test_loss_stated_as_positive_amount_matches_negative_difference():
    """E2E raise-your-prices (2026-10-05): "losing $250 for each client" - 750 - 1000 = -250; itki musbet deyilir."""
    s = {"id": 1, "section": "S", "paragraph": "p", "sentence": "If Laura keeps $750 instead of $1,000, she's "
         "losing $250 for each client.", "context": "If Laura keeps $750 instead of $1,000, she's losing $250 for "
         "each client."}
    assert mc._check_one(s, {"claimed_text": "$250", "expr": "750 - 1000"}) is None
    assert mc._check_one(s, {"claimed_text": "$250", "expr": "750 + 1000"}) is not None


def test_first_layer_never_rewrites_a_case_model_figure():
    """Real probe 2026-10-07: modelin '$3,600'-u LLM-in sehv ifadesi (1000 * 4) ile '$4,000'-a 'duzeldildi'."""
    import math_check as mc
    md = "# T\n\n## Section 4: Decision\n\nRevenue goes from $3,000 to $3,600 a week.\n"
    extract = lambda sents: [{"id": s["id"], "claimed_text": "$3,600", "expr": "1000 * 4"} for s in sents]
    rewrites = []
    out, probs = mc.audit_and_fix(md, extract, lambda p, pr: rewrites.append(p) or {}, trusted=[3000.0, 3600.0])
    assert out == md and not rewrites and probs == []
