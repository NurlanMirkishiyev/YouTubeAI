import grounding as g

TEXT = ("Advertising brought in about $196 billion of Meta's $201 billion revenue. "
        "Only 2% of users pay, about five dollars each. Twenty thousand people pay.")


def test_numbers_include_digits_scales_and_spoken_words():
    nums = g.numbers_in(TEXT)
    assert {196.0, 196e9, 201.0, 201e9, 2.0, 5.0, 20000.0} <= nums


def test_grounded_counter_passes_invented_one_is_rejected():
    ok = {"kind": "counter", "value": 201, "prefix": "$", "suffix": " billion", "label": "Meta revenue"}
    assert g.validate(ok, TEXT)["value"] == 201
    assert g.validate({**ok, "value": 300}, TEXT) is None
    assert g.validate({**ok, "label": "Google profit"}, TEXT) is None


def test_bars_need_two_grounded_items():
    spec = {"kind": "bars", "items": [{"label": "Advertising", "value": 196}, {"label": "Revenue", "value": 201}]}
    assert g.validate(spec, TEXT) is not None
    assert g.validate({"kind": "bars", "items": spec["items"][:1]}, TEXT) is None


def test_text_kinds_use_only_narration_words():
    assert g.validate({"kind": "versus", "left": "Advertising", "right": "Users pay"}, TEXT)
    assert g.validate({"kind": "flow", "steps": ["Users", "Advertising", "Profit"]}, TEXT) is None
    assert g.validate({"kind": "nope"}, TEXT) is None


def test_quote_is_a_verbatim_piece_of_the_narration():
    q = g.quote_for(TEXT)
    assert q["kind"] == "quote" and q["text"].rstrip("…").strip() in TEXT


def test_quote_fallback_is_verbatim_with_newlines_and_double_spaces():
    text = ("First  line of the narration has  double spaces and it keeps going\n"
            "past the limit with many more words here so that no sentence is short enough to pick\n"
            "and the tail keeps running on and on without any full stop at all here")
    q = g.quote_for(text)
    assert q["text"].endswith("…")
    assert q["text"].rstrip("…") in text


def test_empty_quote_is_rejected():
    assert g.validate({"kind": "quote", "text": "…"}, TEXT) is None
    assert g.validate({"kind": "quote", "text": ""}, TEXT) is None


def test_scale_word_needs_a_word_boundary():
    nums = g.numbers_in("We know 200 millionaires exist.")
    assert 200.0 in nums and 200e6 not in nums
    assert 200e6 in g.numbers_in("About 200 million users.")


def test_counter_suffix_word_is_normalized_to_leading_space():
    text = "Meta earned 201 billion dollars."
    spec = {"kind": "counter", "value": 201, "prefix": "$", "suffix": "billion", "label": "Meta"}
    assert g.validate(spec, text)["suffix"] == " billion"
    assert g.validate({**spec, "suffix": "%"}, text)["suffix"] == "%"


def test_counter_scale_suffix_only_when_the_narration_says_it():
    spec = {"kind": "counter", "value": 2, "prefix": "", "suffix": " billion", "label": "users"}
    assert g.validate(spec, "Only 2% of users pay.")["suffix"] == ""
    assert g.validate(spec, "About 2 billion users.")["suffix"] == " billion"
    assert g.validate({**spec, "value": 20, "suffix": "thousand"}, "Twenty thousand users.")["suffix"] == " thousand"


def test_dollar_prefix_only_for_dollar_amounts():
    spec = {"kind": "counter", "value": 2, "prefix": "$", "suffix": "", "label": "users"}
    assert g.validate(spec, "Only 2% of users pay.")["prefix"] == ""
    assert g.validate(spec, "Users pay $2 each.")["prefix"] == "$"
    assert g.validate({**spec, "value": 5}, "Users pay about five dollars each.")["prefix"] == "$"
    assert g.validate({**spec, "value": 201, "suffix": " billion"}, "Users made 201 billion dollars.")["prefix"] == "$"


def test_enumeration_in_the_narration_becomes_a_verbatim_list():
    text = ("Running an app isn't free. Companies have to pay engineers, maintain servers, protect user accounts, "
            "and keep everything working.")
    spec = g.enumeration(text)
    assert spec["kind"] == "list" and spec["items"] == ["pay engineers", "maintain servers", "protect user accounts",
                                                         "keep everything working"]
    assert g.validate(spec, text)


def test_no_enumeration_gives_none():
    assert g.enumeration("This is one plain sentence without a list.") is None


def test_long_phrases_do_not_fit_the_screen_and_are_rejected():
    text = "The person using the product and the person paying for it are not always the same person."
    assert g.validate({"kind": "versus", "left": "person using the product",
                       "right": "the person paying for it are not always the same"}, text) is None
    assert g.validate({"kind": "versus", "left": "person using the product", "right": "person paying for it"}, text)
