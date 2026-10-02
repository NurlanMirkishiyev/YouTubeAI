"""Reyestr #38 (2026-10-01, "Why $9.99 Feels Cheaper Than $10"): qiymet movzusunda LLM demek olar her
sehneye "price tag $9.99" yazir - 65 sehneden 57-si bos fona dusdu, ehtiyat hovuz catmadi, scene_plan
3 defe cokdu. Hem de "$10" kimi reqemler filtrden kecirdi (sekilde yazi olur)."""
import scene_plan as sp


def test_prices_and_digits_never_reach_the_background_prompt():
    for raw in ("a scale balancing $9.99, a shelf", "a coffee cup, the other $10",
                "a coffee shop display with pastries, a coffee priced at $2.99",
                "a shopping cart filled with products priced at .99"):
        cleaned = sp.clean_bg_prompt(raw)
        assert "$" not in cleaned and not any(ch.isdigit() for ch in cleaned), (raw, cleaned)


def test_printed_things_are_dropped():
    # ikinci E2E diaqnostikasi: bunlar yazi ile cekilir, amma filtrden kecirdi
    for raw in ("a collection of price labels with different endings", "a quality seal sticker on a product",
                "a feedback form sitting on a table", "a recommendation card placed on a table",
                "a modern brand logo displayed in a professional setting",
                "a bottle of Brand A on a shelf", "a visual of an online comment section with comments",
                "an optical illusion with numbers", "a single digit page flipping on a wooden desk",
                "a stack of product boxes with positive reviews", "a quality badge next to a product",
                "a price comparison display", "a consumer choosing between two detergent bottles"):
        assert sp.clean_bg_prompt(raw) == sp.FALLBACK_BG, raw


def test_price_clause_is_cut_but_the_object_stays():
    assert sp.clean_bg_prompt("a shopping bag with a shirt tagged $9.99 peeking out, a wooden counter") == \
        "a shopping bag, a wooden counter"
    assert sp.clean_bg_prompt("a coffee cup placed on a counter with a price tag of $2.99") == \
        "a coffee cup placed on a counter"


def test_counted_objects_are_kept():
    assert sp.clean_bg_prompt("two bottles of laundry detergent side by side on a supermarket shelf") == \
        "two bottles of laundry detergent side by side on a supermarket shelf"


def test_prompt_without_article_keeps_its_subject():
    # gpt-4o artikl yazmir - evvel hamisi bos fona dusurdu
    assert sp.clean_bg_prompt("shirt on a rack with a $9.99 price tag") == "a shirt on a rack"
    assert sp.clean_bg_prompt("coffee cup and pastry, cafe table") == "a coffee cup"
    assert sp.clean_bg_prompt("no extra fees, a wooden desk") == "a wooden desk"


def test_side_by_side_is_not_the_hero():
    assert sp.hero("two detergent bottles side by side on a supermarket shelf") == "bottle"


def test_close_up_is_not_the_hero():
    assert sp.hero("a close-up of a coffee cup on a cafe table") == "cup"
    assert sp.hero("a close up of a product") == "product"


def test_topic_pool_is_clean_and_unique(monkeypatch):
    raw = ["a clothing rack in a boutique", "a price tag reading $9.99", "a clothing rack by a window",
           "a cash register with its drawer open", "espresso cup on a saucer at a cafe bar", "a mug"]
    monkeypatch.setattr(sp, "chat_json", lambda *a, **k: {"pictures": raw})
    pool = sp.topic_pool("Why $9.99 Feels Cheaper Than $10", {"register"}, 10)
    assert pool == ["a clothing rack in a boutique", "an espresso cup on a saucer at a cafe bar"]


def test_topic_pool_asks_for_full_phrases():
    # "checkout counter, cash register, busy supermarket" -> 3 soz qalirdi, hovuz 0 oldu
    assert 'starts with "a" or "an"' in sp.TOPIC_POOL and "8-20 words" in sp.TOPIC_POOL


def test_leftover_scenes_get_topic_pictures_before_generic_pool(monkeypatch):
    scenes = [{"section": "S", "narration": f"line {i}"} for i in range(3)]
    monkeypatch.setattr(sp, "_ask", lambda sc, numbers, *a, **k: [
        {"bg_prompt": "a price tag", "subject": "tag", "sprite": "front", "owl_action": ""} for _ in numbers])
    monkeypatch.setattr(sp, "topic_pool", lambda topic, used, n, **k: ["a clothing rack in a boutique"])
    out = sp.plan(scenes, list(sp.VIDEO_POSES), topic="T")
    assert out[0]["bg_prompt"] == "a clothing rack in a boutique"
    assert [s["bg_prompt"] for s in out[1:]] == list(sp.FALLBACK_POOL[:2])


def test_llm_is_told_no_price_tags():
    for text in (sp.SYSTEM, sp.RETRY_NOTE):
        low = text.lower()
        assert "price tag" in low and "digits" in low


def test_fallback_pool_has_no_look_alike_bags():
    # why-9-99 check_bgs: "leather briefcase" ve "leather messenger bag" CLIP+hakim ucun eyni kadr idi
    bags = [p for p in sp.FALLBACK_POOL if "briefcase" in p or " bag " in f"{p} "]
    assert len(bags) <= 1, bags


def test_srt_gate_counts_prices_as_spoken():
    # why-9-99 make_srt: whisper bir isde "$9.99" -> "9 dollars and 99 cents" (5 soz), "$10" -> "10 dollars";
    # 2026-10-03 isinde ise "$9 .99" (2 token). Her iki terefe eyni kanonik forma - format ferqi qapini yixmir.
    import stages
    script = "One is priced at $9.99, and the other at $10. Prices ending in .99 work."
    want = stages.spoken_words(script)
    assert want == len(script.split())
    spelled = "One is priced at 9 dollars and 99 cents, and the other at 10 dollars. Prices ending in .99 work."
    split = "One is priced at $9 .99, and the other at $10. Prices ending in .99 work."
    assert stages.whisper_word_count(spelled.split()) == want
    assert stages.whisper_word_count(split.split()) == want
    assert stages.whisper_word_count("a 1,500 dollars plan".split()) == 3
    assert stages.spoken_words("# Title\nplain words here") == 3

