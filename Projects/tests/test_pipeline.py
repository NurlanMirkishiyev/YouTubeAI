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
                                           "render_owls", "upscale_bgs", "tts_gen", "make_srt", "captions", "music_gen",
                                           "build_episode", "publish", "quality_gate"]
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


def test_render_owls_stage_is_done_when_its_report_exists(tmp_path):
    ctx = _ctx(tmp_path)
    owl = st.STAGES[st.stage_index("render_owls")]
    assert owl.command(ctx, False)[1].endswith("render_owls.py")
    assert not owl.done(ctx)
    (tmp_path / "owl_qa.json").write_text('{"scenes": {}}', encoding="utf-8")
    assert owl.done(ctx)


def test_parse_args_requires_topic_or_resume():
    a = pl.parse_args(["Topic"])
    # istifadeci 2026-09-30: video 10-12 deq (evvel 8-10); 1230 soz ~8.85 deq verirdi -> 1530 ~11 deq
    assert (a.words, a.min_seconds, a.max_seconds) == (1530, 600.0, 720.0)
    assert pl.parse_args(["--resume", "t", "--from", "build_episode"]).from_stage == "build_episode"


def test_invalidate_after_script(tmp_path):
    for d in ("bg", "bg_hd", "owl", "audio", "cards", "youtube"):
        (tmp_path / d).mkdir()
    for f in ("scenes.json", "narration.wav", "narration.srt", "t.mp4", "script.md", "bg_qa.json", "owl_qa.json"):
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


def test_failed_stage_shows_the_last_log_line_and_quota_errors_are_not_retried(tmp_path, monkeypatch):
    stage = _fake_stage("publish", False)
    monkeypatch.setattr(pl, "_logged_call", lambda cmd, log: open(log, "a", encoding="utf-8").write(
        "noise\npublish paketi xetasi: OpenAI BALANSI BITIB - kredit elave et\n") and 1)
    problems = pl.run_stage(stage, _ctx(tmp_path), False, str(tmp_path))
    assert "BALANSI BITIB" in problems[0]
    calls = []
    got = pl._step_with_retries(stage, _ctx(tmp_path), False, str(tmp_path),
                                lambda *a: calls.append(1) or problems, None, [], lambda s: None)
    assert len(calls) == 1 and got == problems


# Istifadeci 2026-09-27: musiqi lisenziyasiz/pulsuz - her epizoda oz AI musiqisi (music_gen, lokal GPU)
def test_make_ctx_uses_the_episodes_own_ai_music(tmp_path, monkeypatch):
    monkeypatch.setattr(pl, "EPISODES", str(tmp_path))
    ctx = pl.make_ctx(pl.parse_args(["Some Topic"]))
    assert ctx.music == str(tmp_path / "some-topic" / "music.wav")


def test_music_gen_stage_runs_in_its_own_venv_before_the_build(tmp_path):
    ctx = _ctx(tmp_path, music=str(tmp_path / "music.wav"))
    names = [s.name for s in st.STAGES]
    assert names.index("music_gen") == names.index("build_episode") - 1
    stage = st.STAGES[st.stage_index("music_gen")]
    cmd = stage.command(ctx, False)
    assert cmd[0] == st.PY["music"] and cmd[1].endswith("music_gen.py") and cmd[2] == str(tmp_path)
    assert not stage.done(ctx)
    (tmp_path / "music.wav").write_bytes(b"x")
    assert stage.done(ctx)


def test_user_given_music_skips_generation(tmp_path):
    track = tmp_path / "my.mp3"
    track.write_bytes(b"x")
    ctx = _ctx(tmp_path, music=str(track))
    assert st.STAGES[st.stage_index("music_gen")].done(ctx)


def test_publish_stage_passes_music_for_the_credit():
    ctx = st.Ctx(topic="T", slug="t", ep_dir="E", words=100, music="M.mp3", min_seconds=480.0,
                 max_seconds=600.0, provider="openai")
    stage = next(s for s in st.STAGES if s.name == "publish")
    cmd = stage.command(ctx, False)
    assert cmd[cmd.index("--music") + 1] == "M.mp3"


def _finished_episode(tmp_path):
    ep = tmp_path / "Episodes" / "cash"
    (ep / "youtube").mkdir(parents=True)
    (ep / "cash.mp4").write_bytes(b"video")
    (ep / "youtube" / "thumbnail.png").write_bytes(b"png")
    (ep / "youtube" / "midrolls.txt").write_text("02:09\n", encoding="utf-8")
    (ep / "youtube" / "upload_checklist.txt").write_text("[ ] Not made for kids\n", encoding="utf-8")
    (ep / "youtube" / "title.txt").write_text("Cash Title\n", encoding="utf-8")
    (ep / "youtube" / "description.txt").write_text("Desc 00:00 Intro\n", encoding="utf-8")
    (ep / "youtube" / "tags.txt").write_text("a,b\n", encoding="utf-8")
    return ep


def test_deliver_puts_each_topic_in_its_own_folder(tmp_path):
    # Istifadeci 2026-09-27: her movzunun oz qovlugu - movzular qarismasin
    ep = _finished_episode(tmp_path)
    (ep / "narration.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n", encoding="utf-8")
    (ep / "script.md").write_text("# Cash\n", encoding="utf-8")
    out = tmp_path / "Hazir_Videolar"
    pl.deliver(str(ep), "cash", str(out))
    assert [p.name for p in out.iterdir()] == ["cash"]
    topic = out / "cash"
    assert sorted(p.name for p in topic.iterdir()) == [
        "cash.mp4", "midrolls.txt", "script.md", "subtitles.srt", "thumbnail.png", "upload_checklist.txt",
        "youtube.txt"]
    assert (topic / "cash.mp4").read_bytes() == b"video"
    text = (topic / "youtube.txt").read_text(encoding="utf-8")
    assert "Cash Title" in text and "Desc 00:00 Intro" in text and "a,b" in text


def test_deliver_skips_missing_optional_files(tmp_path):
    ep = _finished_episode(tmp_path)
    out = tmp_path / "Hazir_Videolar"
    pl.deliver(str(ep), "cash", str(out))
    assert sorted(p.name for p in (out / "cash").iterdir()) == [
        "cash.mp4", "midrolls.txt", "thumbnail.png", "upload_checklist.txt", "youtube.txt"]


def test_deliver_replaces_an_older_copy(tmp_path):
    ep = _finished_episode(tmp_path)
    out = tmp_path / "Hazir_Videolar"
    pl.deliver(str(ep), "cash", str(out))
    (ep / "cash.mp4").unlink()
    (ep / "cash.mp4").write_bytes(b"new video")
    pl.deliver(str(ep), "cash", str(out))
    assert (out / "cash" / "cash.mp4").read_bytes() == b"new video"


def test_captions_stage_builds_subtitles_from_the_script(tmp_path):
    """#54: altyazi ssenaridən; whisper yalniz vaxt. Reqem sehv oxunubsa merhele kecmir."""
    ctx = _ctx(tmp_path)
    stage = st.STAGES[st.stage_index("captions")]
    assert stage.command(ctx, False)[1].endswith("captions.py")
    (tmp_path / "captions_qa.json").write_text('{"problems": ["sc03: 9.99 esidilmedi"]}', encoding="utf-8")
    assert stage.verify(ctx) == ["sc03: 9.99 esidilmedi"]


def test_deliver_prefers_script_captions(tmp_path):
    ep, out = tmp_path / "ep", tmp_path / "out"
    (ep / "youtube").mkdir(parents=True)
    (ep / "cash.mp4").write_bytes(b"v")
    (ep / "youtube" / "thumbnail.png").write_bytes(b"p")
    for name in ("title.txt", "description.txt", "tags.txt", "midrolls.txt", "upload_checklist.txt"):
        (ep / "youtube" / name).write_text("x", encoding="utf-8")
    (ep / "narration.srt").write_text("whisper", encoding="utf-8")
    (ep / "captions.srt").write_text("script $4,000", encoding="utf-8")
    pl.deliver(str(ep), "cash", str(out))
    assert (out / "cash" / "subtitles.srt").read_text(encoding="utf-8") == "script $4,000"


def test_length_gate_counts_spoken_words_with_numbers_expanded():
    """#68: TTS reqemleri soze acir ("$4,000" -> "four thousand dollars"); skript sozu ile hesab 10.9 deq
    dedi, sesi 12.1 deq cixdi."""
    md = "# Title\n\n## Section\nShe charges $4,000 a month.\n"
    assert pl.word_count(md) == 5
    assert pl.spoken_words(md) == 7          # She charges four thousand dollars a month.


def test_word_gate_uses_spoken_words(tmp_path, monkeypatch):
    seen = {}
    monkeypatch.setattr(pl, "words_to_add", lambda n, *a, **k: seen.setdefault("n", n) and 0)
    monkeypatch.setattr(pl, "words_to_cut", lambda n, *a, **k: 0)
    ctx = _ctx(tmp_path)
    open(ctx.p("script.md"), "w", encoding="utf-8").write("## A\nIt costs $4,000.\n")
    pl.word_gate(ctx, str(tmp_path), 0)
    assert seen["n"] == pl.spoken_words("## A\nIt costs $4,000.\n")


def test_deliver_fails_without_the_rpm_files(tmp_path):
    """Faza 4: midrolls.txt + upload_checklist.txt teslim paketinde mecburidir (fail-closed)."""
    import pytest
    ep = _finished_episode(tmp_path)
    (ep / "youtube" / "midrolls.txt").unlink()
    with pytest.raises(FileNotFoundError):
        pl.deliver(str(ep), "cash", str(tmp_path / "Hazir_Videolar"))


def test_pipeline_default_provider_follows_llm_default():
    """Istifadeci 2026-10-08: LLM merheleleri Gemini-de - pipeline 'openai'-ni sabit yazmamalidir."""
    import llm
    assert pl.parse_args(["Topic"]).provider == llm.DEFAULT_PROVIDER
