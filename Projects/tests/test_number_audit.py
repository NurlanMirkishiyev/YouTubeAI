"""Ikinci qat: bolmedeki HER reqem ayrica yoxlanir, fail-closed (istifadeci 2026-10-02: "birdefelik hell et").
Real hal (why-9-99): "three clients a month at $50 an hour ... instead of earning $600 for those three clients,
you'd pull in $649.97 for four clients" - saat sayi yoxdur, 649.97 hec neye uygun gelmir. math_check-in 3
baxisi ferqli ifade verdi (49.99*4 / 3*50 / hesab deyil) -> "cogunluq eyni duzgun deyer" qaydasi susdu."""
import re

import pytest

import math_check as mc
import number_audit as na

REAL = """# Why

## Section 4: Pricing Strategy for Business

If you're a freelancer charging $50 per hour, consider setting your rate at $49.99 instead.

Let's say you typically land three clients a month at $50 an hour. If you switch to $49.99 and attract one more client, that could increase your monthly earnings. So, instead of earning $600 for those three clients, you'd pull in $649.97 for four clients. That's a significant jump.

## Recap

Prices ending in .99 feel cheaper.
"""

GOOD = """# Fees

## Section 1: Fees

A dish costs twenty dollars. With a two percent fee you lose forty cents per dish. Sell a hundred dishes in a week and that's forty dollars. Over four weeks in a month, that's a hundred and sixty dollars.
"""


def _nums(md):
    return [n for sec in na.marked_sections(md) for n in sec["numbers"]]


def _find(md, text):
    return next(n for n in _nums(md) if n["text"] == text)


def _given_all(md, **override):
    """Butun reqemler 'given'; override: {text: answer}."""
    out = {}
    for n in _nums(md):
        out[n["n"]] = override.get(n["text"], {"role": "given"})
    return out


def test_every_number_is_marked_with_its_dollar_sign():
    texts = [n["text"] for n in _nums(REAL)]
    assert "$600" in texts and "$649.97" in texts and "three" in texts and "$50" in texts
    sec = na.marked_sections(REAL)[0]
    [(marked, tags)] = na.batches(sec)
    n600 = _find(REAL, "$600")["n"]
    t600 = next(t for t, n in tags.items() if n == n600)
    assert f"$600⟦{t600}⟧" in marked
    # real hal: gpt-4o marker nomrelerini (⟦13⟧) operand kimi isletdi -> markerde reqem olmur
    assert not any(ch.isdigit() for ch in "".join(re.findall("⟦(.*?)⟧", marked)))


def test_markers_are_single_letters_even_in_long_sections():
    """Real hal: iki herfli markeri (BG) gpt-4o 'G' kimi qaytardi -> 5 reqem yoxlanmadi."""
    body = " ".join(f"Item {i} costs {i + 1} dollars." for i in range(1, 21))
    sec = na.marked_sections(f"## Section 1: X\n\n{body}\n")[0]
    assert len(sec["numbers"]) == 40
    got = na.batches(sec)
    assert len(got) == 2
    seen = []
    for text, tags in got:
        assert all(len(t) == 1 for t in tags) and len(tags) <= 26
        assert sorted(re.findall("⟦(.)⟧", text)) == sorted(tags)
        seen += tags.values()
    assert sorted(seen) == [n["n"] for n in sec["numbers"]]


def test_real_bug_disagreeing_passes_flag_both_results():
    """3 baxis ferqli sey deyir -> hec biri tesdiq olunmur -> problem (evvel susurdu)."""
    a = _given_all(REAL, **{"$649.97": {"role": "result", "expr": "49.99 * 4"}})
    b = _given_all(REAL, **{"$600": {"role": "result", "expr": "3 * 50"},
                            "$649.97": {"role": "missing"}})
    c = _given_all(REAL, **{"$600": {"role": "missing"}, "$649.97": {"role": "missing"}})
    probs = na.judge(na.marked_sections(REAL), [a, b, c])
    flagged = {p["text"] for p in probs}
    assert flagged == {"$600", "$649.97"}


def test_hours_cannot_be_smuggled_in_as_a_constant():
    """'3 * 4 * 50' - 4 hefte/ay sabiti yalniz metnde hefte VE ay olanda qebul olunur."""
    assert not mc._grounded(4, "three clients a month at $50 an hour")
    assert mc._grounded(4, "a hundred dishes in a week. Over a month")
    assert not mc._grounded(12, "fifty dollars an hour")
    assert mc._grounded(12, "ten dollars a month, over a year")
    assert not mc._grounded(5, "three clients")
    smuggle = _given_all(REAL, **{"$600": {"role": "result", "expr": "3 * 4 * 50"}})
    probs = na.judge(na.marked_sections(REAL), [smuggle] * 3)
    assert "$600" in {p["text"] for p in probs}


def test_correct_paragraph_passes_with_one_sloppy_pass():
    assert {"forty cents", "forty", "hundred and sixty"} <= {n["text"] for n in _nums(GOOD)}
    ok = _given_all(GOOD, **{"forty cents": {"role": "result", "expr": "20 * 2 / 100"},
                             "forty": {"role": "result", "expr": "0.40 * 100"},
                             "hundred and sixty": {"role": "result", "expr": "40 * 4"}})
    sloppy = _given_all(GOOD, **{"hundred and sixty": {"role": "missing"}})
    assert na.judge(na.marked_sections(GOOD), [ok, sloppy, ok]) == []


def test_majority_agreeing_on_correct_value_gives_the_fix_value():
    bad = GOOD.replace("a hundred and sixty dollars", "sixteen hundred dollars")
    ans = _given_all(bad, **{"sixteen hundred": {"role": "result", "expr": "40 * 4"}})
    probs = na.judge(na.marked_sections(bad), [ans] * 3)
    assert len(probs) == 1 and probs[0]["correct"] == pytest.approx(160)


def test_number_no_pass_answered_is_a_problem():
    probs = na.judge(na.marked_sections(GOOD), [{}, {}, {}])
    assert len(probs) == len(_nums(GOOD))
    assert all(p["correct"] is None for p in probs)


def _audit_fake(md_bad_text):
    """Saxta LLM: $600/$649.97 varsa 'missing', qalan hamisi given."""
    def extract(sections):
        out = {}
        for sec in sections:
            for n in sec["numbers"]:
                out[n["n"]] = {"role": "missing"} if n["text"] in md_bad_text else {"role": "given"}
        return out
    return extract


def test_audit_and_fix_accepts_rewritten_paragraph():
    calls = []

    def rewrite(paragraph, problems):
        calls.append([p["text"] for p in problems])
        return paragraph.replace("$600", "six hundred dollars, ten hours each,").replace(
            "$649.97", "a bit more")

    md, probs = na.audit_and_fix(REAL, _audit_fake({"$600", "$649.97"}), rewrite, lambda s: "")
    assert probs == []
    assert "$649.97" not in md and "$600" not in md
    assert calls and set(calls[0]) == {"$600", "$649.97"}
    assert "If you're a freelancer charging $50 per hour" in md


def test_unfixable_sentence_is_rewritten_without_numbers():
    """Son care: hesab duzelmirse cumle reqemsiz yazilir - sehvli reqem videoya hec vaxt dusmur."""
    md, probs = na.audit_and_fix(REAL, _audit_fake({"$600", "$649.97"}), lambda p, pr: p,
                                 lambda s: "So your monthly earnings could grow.", rounds=2)
    assert probs == []
    assert "$649.97" not in md and "So your monthly earnings could grow." in md
    assert "Let's say you typically land three clients a month at $50 an hour." in md


def test_plain_rewrite_that_still_has_numbers_deletes_the_sentence():
    md, probs = na.audit_and_fix(REAL, _audit_fake({"$600", "$649.97"}), lambda p, pr: p,
                                 lambda s: "You'd earn $700.", rounds=1)
    assert probs == []
    assert "$700" not in md and "$649.97" not in md and "That's a significant jump." in md


def test_rewrite_that_breaks_paragraph_structure_is_rejected():
    md, _ = na.audit_and_fix(REAL, _audit_fake({"$600", "$649.97"}),
                             lambda p, pr: "One.\n\n## Hack\n\nTwo.", lambda s: "", rounds=1)
    assert "## Hack" not in md


def test_check_file_runs_number_audit_and_reports_it(tmp_path, monkeypatch):
    script = tmp_path / "script.md"
    script.write_text(REAL, encoding="utf-8")
    monkeypatch.setattr(mc, "llm_extract", lambda sents, **kw: [{"id": s["id"], "calc": False} for s in sents])
    monkeypatch.setattr(na, "llm_extract", lambda secs, **kw: _audit_fake({"$600", "$649.97"})(secs))
    monkeypatch.setattr(na, "llm_focus", lambda nums, secs, **kw: {n["n"]: {"role": "missing"} for n in nums})
    monkeypatch.setattr(na, "llm_rewrite", lambda p, pr, **kw: p)
    monkeypatch.setattr(na, "llm_plain", lambda s, **kw: "So your monthly earnings could grow.")
    problems = mc.check_file(str(script), provider="openai")
    assert problems == []
    text = script.read_text(encoding="utf-8")
    assert "$649.97" not in text
    assert mc.report_problems(str(tmp_path)) == []


def test_script_prompt_demands_every_input_stated():
    import script_gen as sg
    low = sg.SYSTEM.lower()
    assert "every input" in low and "unstated" in low


def test_percent_result_is_verified_with_its_unit():
    md = "## Section 1: X\n\nYou keep seventeen of twenty dollars. That's a loss of fifteen percent.\n"
    assert "fifteen percent" in {n["text"] for n in _nums(md)}
    ans = _given_all(md, **{"fifteen percent": {"role": "result", "expr": "(20 - 17) / 20"}})
    assert na.judge(na.marked_sections(md), [ans] * 3) == []


def test_restated_earlier_number_counts_as_verified():
    """Real hal (payment-fees): 'instead of making ten dollars' - evvelki 10-un tekrari, ifade '10'."""
    md = "## Section 1: X\n\nTen cups make ten dollars. So, instead of making ten dollars, you keep eight.\n"
    nums = _nums(md)
    third = nums[2]
    assert na._vote(third, {"role": "result", "expr": "10"})[0] == "ok"
    assert na._vote(third, {"role": "result", "expr": "11"})[0] != "ok"


def test_focused_second_look_clears_a_correct_number():
    """Real hal: 'a three dollar fee on twenty dollars is a loss of fifteen percent' - 3 baxis 'missing' dedi."""
    md = ("## Section 1: X\n\nA shirt costs twenty dollars and the fee is three dollars. "
          "That's a loss of fifteen percent.\n")
    missing = _given_all(md, **{"fifteen percent": {"role": "missing"}})
    focus_ok = lambda nums: {n["n"]: {"role": "result", "expr": "3 / 20"} for n in nums}
    focus_bad = lambda nums: {n["n"]: {"role": "missing"} for n in nums}
    md1, probs = na.audit_and_fix(md, lambda secs: missing, lambda p, pr: p, lambda s: "", focus=focus_ok)
    assert probs == [] and md1 == md
    md2, _ = na.audit_and_fix(md, lambda secs: missing, lambda p, pr: p, lambda s: "", focus=focus_bad, rounds=1)
    assert "fifteen percent" not in md2


def test_recap_can_use_inputs_from_earlier_sections():
    """Real hal (payment-fees Recap): 'ten coffees ... two dollars go to fees' - 20 sent evvelki bolmede."""
    md = ("## Section 1: X\n\nEach sale costs you twenty cents in fees.\n\n"
          "## Recap\n\nSelling ten coffees means two dollars go straight to fees.\n")
    two = _find(md, "two dollars") if any(n["text"] == "two dollars" for n in _nums(md)) else _find(md, "two")
    assert "twenty cents" in two["context"]
    assert na._vote(two, {"role": "result", "expr": "10 * 0.20"})[0] == "ok"
    sec = na.marked_sections(md)[-1]
    assert "twenty cents" in sec["earlier"]


def test_number_from_the_title_restated_in_hook_is_not_flagged():
    """Real hal: Hook-dakı '$9.99' (basliqda var) '10 - 0.01' kimi oxundu, yenidən yazilanda '$10' oldu."""
    md = "# Why $9.99 Feels Cheaper Than $10\n\n## Hook\n\nOne item is priced at $9.99, the other at $10.\n"
    n999 = _find(md, "$9.99")
    assert na._vote(n999, {"role": "result", "expr": "10 - 0.01"})[0] == "ok"
    # kicik tam ededler hər yerde var - onlarin "tekrari" sübut deyil
    md2 = "## S\n\nYou buy four apples. Two plus one is four.\n"
    assert na._vote(_nums(md2)[-1], {"role": "result", "expr": "2 + 1"})[0] != "ok"


def test_rewrite_may_not_change_numbers_that_were_not_flagged():
    """Yenidən yazma yalniz bayraqli reqemi deyise biler; '$9.99 -> $10' kimi pozulma qebul olunmur."""
    def rewrite(paragraph, problems):
        return paragraph.replace("$49.99", "$45").replace("$600", "six hundred dollars over four weeks")

    md, _ = na.audit_and_fix(REAL, _audit_fake({"$600"}), rewrite, lambda s: "So it grows.", rounds=1)
    assert "$49.99" in md and "$45" not in md


def test_number_audit_is_the_final_authority(tmp_path, monkeypatch):
    """Real hal: 1-ci qatin son yoxlamasi duzgun cumleleri ('try $49.99' = 50 - 49.99) sehv sayib
    pipeline-i dayandirdi. 1-ci qat yalniz duzelis ucundur; son qerar her reqemi yoxlayan 2-ci qatdir."""
    script = tmp_path / "script.md"
    script.write_text(GOOD, encoding="utf-8")
    monkeypatch.setattr(mc, "llm_extract", lambda sents, **kw: [])      # 1-ci qat: hec ne tesdiqlemir
    monkeypatch.setattr(na, "llm_extract", lambda secs, **kw: _given_all(GOOD))
    monkeypatch.setattr(na, "llm_focus", lambda nums, secs, **kw: {})
    monkeypatch.setattr(na, "llm_rewrite", lambda p, pr, **kw: p)
    monkeypatch.setattr(na, "llm_plain", lambda s, **kw: "")
    monkeypatch.setattr(mc, "llm_rewrite", lambda p, pr, **kw: {})
    assert mc.check_file(str(script), provider="openai") == []
    assert script.read_text(encoding="utf-8").strip() == GOOD.strip()
