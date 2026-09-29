import json

import pytest

import check_bgs as cb
import render_bgs
import scene_plan


def _write_scenes(path, prompts):
    data = {"scenes": [{"bg_prompt": p, "narration": f"n{i}", "pos": "right"} for i, p in enumerate(prompts)]}
    path.write_text(json.dumps(data), encoding="utf-8")


# --- hakimin cavabi -------------------------------------------------------------------------

# Hakim her yoxlamaya ayrica beli/xeyr verir; umumi "ok" sualinda gpt-4o-mini 97 fonun 84-une
# "human" demisdi (narration-daki "you" sozunden). Yalniz acıq True problem sayilir.
def test_verdict_counts_only_checks_answered_true():
    v = cb.parse_verdict({"description": "a blender", "people": False, "writing": True,
                          "collage": False, "no_subject": False, "deformed": False, "off_topic": False,
                          "fix_prompt": "a red kettle"})
    assert not v.ok and v.problems == ("text",) and v.fix_prompt == "a red kettle"
    assert cb.parse_verdict({"people": False, "writing": False}).ok


def test_verdict_tolerates_malformed_judge_output():
    v = cb.parse_verdict({"people": "yes", "off_topic": True, "fix_prompt": 5})
    assert not v.ok and v.problems == ("mismatch",) and v.fix_prompt == ""


# --- yeni prompt ---------------------------------------------------------------------

def test_next_prompt_passes_judge_fix_through_word_filters():
    # hakimin teklifi de insan/yazi filtrinden kecir
    p = cb.next_prompt("a robot coach with a stopwatch, a tired athlete", attempt=1, used=set())
    assert p == "a robot coach with a stopwatch"


def test_next_prompt_uses_unused_fallback_on_last_attempt_or_empty_fix():
    used = {scene_plan.FALLBACK_POOL[0]}
    last = cb.next_prompt("a red kettle on a stove", attempt=cb.MAX_ATTEMPTS, used=used)
    empty = cb.next_prompt("", attempt=1, used=used)
    assert last in scene_plan.FALLBACK_POOL and last not in used
    assert empty in scene_plan.FALLBACK_POOL and empty not in used


def test_apply_changes_rereads_file_and_keeps_other_edits(tmp_path):
    path = tmp_path / "scenes.json"
    _write_scenes(path, ["a", "b", "c"])
    data = json.loads(path.read_text(encoding="utf-8"))
    data["scenes"][2]["duration"] = 4.2              # basqa proses eyni vaxtda yazib
    path.write_text(json.dumps(data), encoding="utf-8")
    cb.apply_changes(str(path), {2: "a new prompt"})
    s = json.loads(path.read_text(encoding="utf-8"))["scenes"]
    assert s[1]["bg_prompt"] == "a new prompt"
    assert s[2]["duration"] == 4.2 and s[0]["bg_prompt"] == "a"


# --- render_bgs -----------------------------------------------------------------------------

def test_render_save_keeps_prompts_edited_on_disk_meanwhile(tmp_path):
    # render_bgs evvel yaddasdaki kohne scenes.json-u uzerine yazir ve duzelisleri silirdi
    path = tmp_path / "scenes.json"
    _write_scenes(path, ["old one", "old two"])
    bg = tmp_path / "bg"
    bg.mkdir()
    (bg / "sc01.png").write_bytes(b"x")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["scenes"][1]["bg_prompt"] = "edited meanwhile"
    path.write_text(json.dumps(data), encoding="utf-8")
    render_bgs.save_bg_paths(str(path), str(bg))
    s = json.loads(path.read_text(encoding="utf-8"))["scenes"]
    assert s[1]["bg_prompt"] == "edited meanwhile"
    assert s[0]["bg"].endswith("sc01.png") and "bg" not in s[1]


# E2E ep3: sc89 API limiti (429) ucun yoxlanmadan "ok" kecdi - xetali fonlar gozleyib yeniden yoxlanir
def test_judge_all_rejudges_scenes_that_hit_api_errors():
    calls, waits = [], []

    def judge_fn(n):
        calls.append(n)
        if n == 2 and calls.count(2) == 1:
            return cb.JUDGE_ERROR
        return cb.Verdict(ok=n != 3, problems=() if n != 3 else ("text",), fix_prompt="")

    res = cb.judge_all([1, 2, 3], judge_fn, workers=2, sleep=waits.append)
    assert calls.count(2) == 2 and waits
    assert res[2].ok and not res[3].ok and res[1].ok


def test_judge_all_gives_up_after_retries_without_blocking():
    res = cb.judge_all([1], lambda n: cb.JUDGE_ERROR, workers=1, sleep=lambda s: None)
    assert res[1] is cb.JUDGE_ERROR and res[1].ok


# --- reyestr #32: hakim teklifi rədd olunur -> movzudan kenar ehtiyat fon -> yene "mismatch" dovresi ----

def test_judge_text_lists_objects_already_used_in_the_episode():
    scene = {"narration": "Prices ending in 99 feel lower.", "bg_prompt": "a price tag on a shirt"}
    text = cb.judge_text(scene, {"a shopping cart in a store", "a price tag on a shirt"})
    assert "shopping cart" in text and "do not suggest" in text.lower()


def test_pool_fallback_is_not_redrawn_only_for_being_off_topic():
    pool = scene_plan.FALLBACK_POOL[0]
    mism = cb.Verdict(ok=False, problems=("mismatch",), fix_prompt="x")
    assert not cb.needs_redo(mism, pool, tries=1)
    assert cb.needs_redo(mism, "a shopping cart in a store", tries=1)


def test_pool_fallback_with_a_real_defect_is_still_redrawn():
    bad = cb.Verdict(ok=False, problems=("text", "mismatch"), fix_prompt="x")
    assert cb.needs_redo(bad, scene_plan.FALLBACK_POOL[0], tries=1)
    assert not cb.needs_redo(bad, "a cart", tries=cb.MAX_ATTEMPTS)


def test_attempts_survive_a_resume_while_the_prompt_is_unchanged(tmp_path):
    (tmp_path / "bg_qa.json").write_text(json.dumps({"scenes": {
        "1": {"attempts": 3, "prompt": "a lighthouse"}, "2": {"attempts": 2, "prompt": "old prompt"}}}))
    scenes = [{"bg_prompt": "a lighthouse"}, {"bg_prompt": "new prompt"}]
    assert cb.load_tries(str(tmp_path), scenes) == {1: 3}


def test_load_tries_without_report_is_empty(tmp_path):
    assert cb.load_tries(str(tmp_path), [{"bg_prompt": "x"}]) == {}


def test_verdict_reads_several_fix_options():
    v = cb.parse_verdict({"off_topic": True, "fix_prompts": ["a price tag on a shirt", " a paper bag ", 7]})
    assert v.fix_options == ("a price tag on a shirt", "a paper bag") and v.fix_prompt == "a price tag on a shirt"


def test_next_prompt_takes_the_first_fix_option_that_passes_filters():
    # pricing E2E-2: yegane teklif (qiymet etiketi / artiq olan "shelf") redd olunub hovuza dusurdu
    used = {"a retail store shelf with products"}
    opts = ("A price tag showing .99 on a product", "a grocery shelf with pasta", "a pasta box on a kitchen counter")
    assert cb.next_prompt(opts, attempt=1, used=used) == "a pasta box on a kitchen counter"


def test_next_prompt_falls_back_to_pool_when_no_option_passes():
    p = cb.next_prompt(("a menu board with prices",), attempt=1, used=set())
    assert p in scene_plan.FALLBACK_POOL


# --- butun teklifler redd olunanda hakime sebeb bildirilir, ikinci teklif alinir (#32) -------------

def test_rejection_reason_names_writing_or_the_repeated_object():
    used = {"a cash register in a store"}
    assert "writing" in cb.rejection_reason("A menu board with prices", used)
    assert "register" in cb.rejection_reason("A cash register with a total", used)
    assert cb.rejection_reason("a pasta box on a kitchen counter", used) is None


def test_choose_prompt_asks_again_with_reasons_when_every_option_is_rejected():
    seen = {}

    def suggest(feedback):
        seen["fb"] = feedback
        return ("a handmade leather handbag on a boutique shelf",)

    v = cb.Verdict(ok=False, problems=("mismatch",), fix_prompt="", fix_options=("A menu board with prices",))
    p = cb.choose_prompt(v, attempt=1, used=set(), suggest=suggest)
    assert p == "a handmade leather handbag on a boutique shelf" and "menu board" in seen["fb"]


def test_choose_prompt_does_not_ask_again_when_an_option_is_fine():
    v = cb.Verdict(ok=False, problems=("mismatch",), fix_prompt="", fix_options=("a pasta box on a counter",))
    p = cb.choose_prompt(v, attempt=1, used=set(), suggest=lambda fb: pytest.fail("lazim deyil"))
    assert p == "a pasta box on a counter"
