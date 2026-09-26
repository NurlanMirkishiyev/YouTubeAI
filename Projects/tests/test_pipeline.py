import os

import pipeline as pl
import stages as st
import state


def _ctx(tmp_path, **kw):
    base = dict(topic="T", slug="t", ep_dir=str(tmp_path), words=1230, music=None,
                min_seconds=480.0, max_seconds=600.0, provider="openai")
    base.update(kw)
    return st.Ctx(**base)


def test_stage_order():
    assert [s.name for s in st.STAGES] == ["script_gen", "scene_plan", "render_bgs", "check_bgs",
                                           "upscale_bgs", "tts_gen", "make_srt", "build_episode", "publish"]
    assert [s.name for s in st.STAGES if s.needs_comfy] == ["upscale_bgs"]    # fonlar OpenAI-de, ComfyUI yalniz upscale ucun


def test_commands(tmp_path):
    ctx = _ctx(tmp_path, music="m.mp3")
    cmd = st.STAGES[0].command(ctx, True)
    assert cmd[0] == st.PY["projects"] and "--words" in cmd and "1230" in cmd and cmd[-1] == "--force"
    assert st.STAGES[st.stage_index("tts_gen")].command(ctx, False)[0] == st.PY["tts"]
    assert st.STAGES[st.stage_index("make_srt")].command(ctx, False)[0] == st.PY["whisper"]
    build = st.STAGES[st.stage_index("build_episode")].command(ctx, False)
    assert build[1].endswith("remotion_build.py") and build[-2:] == ["--music", "m.mp3"]


def test_check_bgs_stage_judges_backgrounds_before_upscale(tmp_path):
    ctx = _ctx(tmp_path)
    chk = st.STAGES[st.stage_index("check_bgs")]
    assert chk.command(ctx, False)[1].endswith("check_bgs.py")
    assert not chk.done(ctx)
    (tmp_path / "bg_qa.json").write_text('{"passed": true}', encoding="utf-8")
    assert chk.done(ctx)


def test_parse_args_requires_topic_or_resume():
    a = pl.parse_args(["Topic"])
    assert (a.words, a.min_seconds, a.max_seconds) == (1230, 480.0, 600.0)    # video 8-10 deq
    assert pl.parse_args(["--resume", "t", "--from", "build_episode"]).from_stage == "build_episode"


def test_invalidate_after_script(tmp_path):
    for d in ("bg", "bg_hd", "audio", "cards", "youtube"):
        (tmp_path / d).mkdir()
    for f in ("scenes.json", "narration.wav", "narration.srt", "t.mp4", "script.md"):
        (tmp_path / f).write_text("x")
    pl.invalidate_after_script(str(tmp_path), "t")
    assert sorted(os.listdir(tmp_path)) == ["script.md"]


def _fake_stage(name, done):
    return st.Stage(name, lambda c, f: ["x"], lambda c: done, lambda c: [])


def test_run_pipeline_skips_done_and_records_failure(tmp_path):
    stages = [_fake_stage("a", True), _fake_stage("b", False), _fake_stage("c", False)]
    ran = []

    def runner(stage, ctx, force, log_dir):
        ran.append(stage.name)
        return ["boom"] if stage.name == "c" else []

    path = str(tmp_path / "state.json")
    rc = pl.run_pipeline(_ctx(tmp_path), path, stages=stages, runner=runner, gates={}, sleep=lambda s: None)
    s = state.read_state(path)
    assert rc == 1 and ran == ["b"] + ["c"] * (1 + pl.STAGE_RETRIES)
    assert [s["stages"][n]["status"] for n in "abc"] == ["done", "done", "failed"]
    assert s["stages"]["c"]["error"] == "boom"


def test_run_pipeline_from_forces_rerun(tmp_path):
    stages = [_fake_stage("a", True), _fake_stage("b", True)]
    seen = []
    rc = pl.run_pipeline(_ctx(tmp_path), str(tmp_path / "s.json"), stages=stages, from_idx=1,
                         runner=lambda s, c, f, l: seen.append((s.name, f)) or [], gates={})
    assert rc == 0 and seen == [("b", True)]


def test_gate_restart_jumps_back(tmp_path):
    stages = [_fake_stage("a", False), _fake_stage("b", False)]
    seen = []
    calls = {"n": 0}

    def gate(ctx, log_dir, attempt):
        calls["n"] += 1
        return pl.Gate("restart", "short", "a") if attempt == 0 else pl.Gate("ok")

    rc = pl.run_pipeline(_ctx(tmp_path), str(tmp_path / "s.json"), stages=stages,
                         runner=lambda s, c, f, l: seen.append(s.name) or [], gates={"b": gate})
    assert rc == 0 and seen == ["a", "b", "a", "b"] and calls["n"] == 2


def test_make_ctx_falls_back_to_meta_topic(tmp_path, monkeypatch):
    monkeypatch.setattr(pl, "EPISODES", str(tmp_path))
    (tmp_path / "old").mkdir()
    (tmp_path / "old" / "meta.json").write_text('{"topic": "Old Topic"}', encoding="utf-8")
    ctx = pl.make_ctx(pl.parse_args(["--resume", "old"]))
    assert ctx.topic == "Old Topic" and ctx.slug == "old"


def test_build_stage_renders_with_remotion():
    import stages
    ctx = stages.Ctx(topic="T", slug="t", ep_dir="E", words=100, music=None, min_seconds=480.0,
                       max_seconds=600.0, provider="openai")
    cmd = stages._build_cmd(ctx, False)
    assert cmd[1].endswith("remotion_build.py") and "E" in cmd and "--music" not in cmd


# Muveqqeti xeta (sebeke, ComfyUI/Remotion cokmesi) butun videonu dayandirmasin - merhele yeniden cehd edilir
def test_run_pipeline_retries_a_stage_after_transient_failure(tmp_path):
    stages = [_fake_stage("a", False), _fake_stage("b", False)]
    ran, waits = [], []

    def runner(stage, ctx, force, log_dir):
        ran.append(stage.name)
        return ["network down"] if stage.name == "a" and ran.count("a") == 1 else []

    rc = pl.run_pipeline(_ctx(tmp_path), str(tmp_path / "s.json"), stages=stages, runner=runner,
                         gates={}, sleep=waits.append)
    assert rc == 0 and ran == ["a", "a", "b"] and len(waits) == 1


def _script(tmp_path, n):
    (tmp_path / "script.md").write_text("# T\n\n## Hook\n\n" + "w " * n, encoding="utf-8")


def test_word_gate_shortens_a_script_that_would_run_over_10_minutes(tmp_path, monkeypatch):
    _script(tmp_path, 1700)
    cuts = []

    def fake_shorten(ctx, words, log_dir):
        cuts.append(words)
        _script(tmp_path, 1400)
        return []

    monkeypatch.setattr(pl, "shorten_script", fake_shorten)
    g = pl.word_gate(_ctx(tmp_path), str(tmp_path), 0)
    assert g.status == "ok" and cuts == [1700 - 1455]


def test_length_gate_shortens_and_restarts_when_narration_is_too_long(tmp_path, monkeypatch):
    monkeypatch.setattr(pl, "duration", lambda p: 700.0)
    seen = []
    monkeypatch.setattr(pl, "shorten_script", lambda c, w, l: seen.append(w) or [])
    monkeypatch.setattr(pl, "invalidate_after_script", lambda ep, slug: None)
    g = pl.length_gate(_ctx(tmp_path), str(tmp_path), 0)
    assert g.status == "restart" and g.restart_at == "scene_plan" and seen and seen[0] > 0


def test_verify_video_rejects_a_video_longer_than_max(tmp_path, monkeypatch):
    import checks
    monkeypatch.setattr(checks, "final_video_problems", lambda p: [])
    monkeypatch.setattr(st, "duration", lambda p: 650.0)
    assert any("650" in p for p in st.verify_video(_ctx(tmp_path)))
    monkeypatch.setattr(st, "duration", lambda p: 560.0)
    assert st.verify_video(_ctx(tmp_path)) == []
