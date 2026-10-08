"""Faza 5.3/5.5/5.7 (istifadeci 2026-10-07): vahid keyfiyyet qapisi - butun hesabatlar movcud, skriptin cari sha256-si
ile uygun, "problems": []; elave yoxlamalar; deliver/publish yalniz qapi kecende. Fail-closed: hesabat yoxdursa xeta."""
import hashlib
import json
import os

import pytest

import quality_gate as qg
import qa_stamp

SCRIPT = "# T\n\n## Hook\nRosa charges $55.\n"


def _dump(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def _episode(tmp_path, decision=True):
    ep = tmp_path / "ep"
    ep.mkdir(parents=True)
    (ep / "script.md").write_text(SCRIPT, encoding="utf-8")
    e = str(ep)
    sha = qa_stamp.script_sha(e)
    _dump(os.path.join(e, "script_qa.json"), {"script_sha256": hashlib.sha256(SCRIPT.encode()).hexdigest(),
                                              "problems": []})
    _dump(os.path.join(e, "math_check.json"), {"script_sha256": hashlib.sha256(SCRIPT.strip().encode()).hexdigest(),
                                               "problems": []})
    model = {"variables": [], "before": {}, "after": {}, **({"threshold": {"name": "x"}} if decision else {})}
    _dump(os.path.join(e, "meta.json"), {"plan": {"model": model, "model_result": {"before": {}, "after": {}}}})
    for name, extra in (("captions_qa.json", {}), ("bg_qa.json", {"duplicates": [], "generic_share": 0.05}),
                        ("owl_qa.json", {"scenes": {"1": {"ok": True}}, "cards": {"intro": {}, "outro": {}}}),
                        (os.path.join("qa", "motion.json"), {"similarity_max": 0.2, "chart_empty_share": 0.0,
                                                             "typewriter_cold_open": True}),
                        (os.path.join("qa", "sfx.json"), {"count": 9})):
        _dump(os.path.join(e, name), {"script_sha256": sha, "problems": [], **extra})
    kinds = ["table", "threshold"] if decision else ["stats"]
    _dump(os.path.join(e, "scenes.json"), {"scenes": [{"visual": {"kind": k}} for k in kinds] + [{"visual": None}]})
    words = [{"w": "Rosa", "s": 0.1, "e": 0.4}, {"w": "$55", "s": 0.5, "e": 0.9}]
    _dump(os.path.join(e, "remotion_props.json"), {
        "fps": 30, "introFrames": 0, "words": words, "motion": {"cold_open": "typewriter"},
        "scenes": [{"frames": 60, "visual": None, "overlay": {"value": 55}}]})
    return e


def _run(ep, **kw):
    kw.setdefault("video", lambda path: [])
    kw.setdefault("pack", lambda ydir: [])
    return qg.gate(ep, "slug", **kw)


def test_complete_episode_passes(tmp_path):
    res = _run(_episode(tmp_path))
    assert res["passed"], res["checks"]


@pytest.mark.parametrize("report", ["captions_qa.json", "bg_qa.json", "owl_qa.json", "qa/motion.json",
                                    "qa/sfx.json", "script_qa.json", "math_check.json"])
def test_missing_report_fails_closed(tmp_path, report):
    ep = _episode(tmp_path)
    os.remove(os.path.join(ep, report))
    assert not _run(ep)["passed"]


def test_report_from_an_older_script_is_stale(tmp_path):
    ep = _episode(tmp_path)
    with open(os.path.join(ep, "script.md"), "a", encoding="utf-8") as f:
        f.write("She keeps 40%.\n")
    res = _run(ep)
    assert not res["passed"]
    assert any("kohne" in p for p in res["checks"]["captions_qa"])


def test_any_problem_in_a_report_fails(tmp_path):
    ep = _episode(tmp_path)
    qa_stamp.write(ep, "captions_qa.json", {"problems": ["sc03: 9.99 esidilmedi"]})
    assert _run(ep)["checks"]["captions_qa"] == ["sc03: 9.99 esidilmedi"]


def test_sfx_must_have_events(tmp_path):
    ep = _episode(tmp_path)
    qa_stamp.write(ep, os.path.join("qa", "sfx.json"), {"count": 0, "problems": []})
    assert _run(ep)["checks"]["sfx"]


def test_photo_figures_need_overlays(tmp_path):
    ep = _episode(tmp_path)
    props = json.load(open(os.path.join(ep, "remotion_props.json"), encoding="utf-8"))
    props["scenes"][0]["overlay"] = None
    _dump(os.path.join(ep, "remotion_props.json"), props)
    assert _run(ep)["checks"]["overlay"]


def test_decision_topic_needs_table_and_threshold(tmp_path):
    ep = _episode(tmp_path)
    _dump(os.path.join(ep, "scenes.json"), {"scenes": [{"visual": {"kind": "table"}}]})
    assert _run(ep)["checks"]["decision_visuals"]
    assert _run(_episode(tmp_path / "b", decision=False))["passed"]


def test_case_model_result_is_required(tmp_path):
    ep = _episode(tmp_path)
    _dump(os.path.join(ep, "meta.json"), {"plan": {}})
    assert _run(ep)["checks"]["case_model"]


def test_typewriter_and_motion_history(tmp_path):
    ep = _episode(tmp_path)
    qa_stamp.write(ep, os.path.join("qa", "motion.json"), {"similarity_max": 0.6, "chart_empty_share": 0.0,
                                                          "typewriter_cold_open": False, "problems": []})
    probs = _run(ep)["checks"]["motion"]
    assert any("typewriter" in p for p in probs) and any("50%" in p for p in probs)


def test_video_and_pack_problems_block_the_gate(tmp_path):
    ep = _episode(tmp_path)
    assert _run(ep, video=lambda p: ["loudness -16.0 LUFS"])["checks"]["video"] == ["loudness -16.0 LUFS"]
    assert _run(ep, pack=lambda y: ["midrolls.txt yoxdur"])["checks"]["publish"] == ["midrolls.txt yoxdur"]


def test_gate_writes_its_report_and_the_self_audit(tmp_path):
    ep = _episode(tmp_path)
    qg.write_outputs(ep, _run(ep))
    rep = json.load(open(os.path.join(ep, "qa", "quality_gate.json"), encoding="utf-8"))
    assert rep["passed"] is True
    audit = open(os.path.join(ep, "qa", "self_audit.md"), encoding="utf-8").read()
    for c in qg.ERROR_CLASSES:
        assert c["name"] in audit
    assert "XƏTA" not in audit


def test_every_error_class_points_to_a_gate_check_and_an_existing_test():
    import re
    checks = set(qg.CHECKS)
    tests_dir = os.path.dirname(__file__)
    for c in qg.ERROR_CLASSES:
        assert c["checks"] and set(c["checks"]) <= checks, c["name"]
        for ref in c["tests"]:
            path, name = ref.split("::")
            src = open(os.path.join(tests_dir, path), encoding="utf-8").read()
            assert re.search(rf"def {name}\(", src), ref


def test_error_class_catalog_doc_is_generated_from_the_code():
    doc = open(r"C:\YouTubeAI\docs\error_classes.md", encoding="utf-8").read()
    assert doc == qg.catalog_markdown()


def test_quality_gate_is_the_last_pipeline_stage():
    import stages as st
    assert st.STAGES[-1].name == "quality_gate"
    assert st.STAGES[-2].name == "publish"


def test_build_qa_reports_are_stamped_with_the_script(tmp_path):
    import remotion_build as rb
    (tmp_path / "script.md").write_text(SCRIPT, encoding="utf-8")
    rb.write_qa(str(tmp_path), "sfx.json", {"count": 3, "problems": []})
    rep = json.load(open(tmp_path / "qa" / "sfx.json", encoding="utf-8"))
    assert qa_stamp.is_fresh(str(tmp_path), rep)


@pytest.mark.parametrize("module", ["captions.py", "check_bgs.py", "render_owls.py"])
def test_stage_reports_are_written_through_the_stamp(module):
    src = open(os.path.join(os.path.dirname(os.path.dirname(__file__)), module), encoding="utf-8").read()
    assert "qa_stamp.write(" in src, module
