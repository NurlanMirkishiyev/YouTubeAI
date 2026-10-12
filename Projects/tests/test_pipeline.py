import os

import pytest

import llm
import pipeline


def test_done_stages_are_skipped_and_failures_retry_once(tmp_path):
    calls = []

    def ok(ep):
        calls.append("b")

    flaky = {"n": 0}

    def flaky_run(ep):
        flaky["n"] += 1
        if flaky["n"] == 1:
            raise RuntimeError("once")
        calls.append("c")
    stages = [pipeline.Stage("a", lambda ep: True, lambda ep: calls.append("a")),
              pipeline.Stage("b", lambda ep: False, ok),
              pipeline.Stage("c", lambda ep: False, flaky_run)]
    pipeline.run_stages(str(tmp_path), stages, log=lambda m: None)
    assert calls == ["b", "c"] and flaky["n"] == 2


def test_stage_order():
    assert [s.name for s in pipeline.STAGES] == ["script", "plan", "images", "owl", "voice", "captions", "music",
                                                 "render", "mix", "publish"]


def test_script_file_is_found_by_name_in_the_scripts_folder():
    p = pipeline.find_script("eli5_business_how_free_apps_make_billions_script")
    assert p.endswith("eli5_business_how_free_apps_make_billions_script.md")


def test_empty_openai_balance_stops_at_once_without_retry(tmp_path):
    n = {"n": 0}
    logs = []

    def broke(ep):
        n["n"] += 1
        raise llm.LLMError("OpenAI balansi bitib: insufficient_quota")
    stages = [pipeline.Stage("images", lambda ep: False, broke)]
    with pytest.raises(SystemExit) as ei:
        pipeline.run_stages(str(tmp_path), stages, log=logs.append)
    assert ei.value.code == 1 and n["n"] == 1
    text = "\n".join(logs)
    assert "OpenAI balansi bitib" in text and "--resume" in text


def test_second_failure_exits_with_code_1(tmp_path):
    stages = [pipeline.Stage("x", lambda ep: False, lambda ep: (_ for _ in ()).throw(RuntimeError("boom")))]
    with pytest.raises(SystemExit) as ei:
        pipeline.run_stages(str(tmp_path), stages, log=lambda m: None)
    assert ei.value.code == 1


def test_no_args_prints_usage_and_exits_2(capsys):
    with pytest.raises(SystemExit) as ei:
        pipeline.main([])
    assert ei.value.code == 2
    assert "run.py --resume <slug>" in capsys.readouterr().out


def _write(path, text="x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _scenes_json(ep, scenes, slug="s"):
    import json
    _write(ep / "scenes.json", json.dumps({"title": "T", "slug": slug, "scenes": scenes}))


def _fake_build(monkeypatch, tmp_path, text):
    monkeypatch.setattr(pipeline, "ROOT", str(tmp_path))
    monkeypatch.setattr(pipeline, "find_script", lambda n: n)
    monkeypatch.setattr(pipeline.script, "build", lambda p: {
        "title": "T", "slug": "s", "scenes": [{"n": 1, "section": "A", "text": text, "type": None}]})


def test_edited_script_resets_derived_files_but_keeps_run_log(tmp_path, monkeypatch):
    _fake_build(monkeypatch, tmp_path, "new text")
    ep = tmp_path / "Episodes" / "s"
    _scenes_json(ep, [{"n": 1, "section": "A", "text": "old text", "type": "photo"}])
    for rel in ("img/sc01.png", "owl/sc01.png", "voice/sc01.wav", "narration.wav", "captions.json", "a.srt",
                "music.wav", "music.skip", "music_parts/p.wav", "public/f.txt", "props.json", "video_raw.mp4",
                "s.mp4", "thumbnail.png", "youtube.txt", "run.log"):
        _write(ep / rel)
    logs = []
    pipeline.start("x", log=logs.append)
    assert sorted(p.name for p in ep.iterdir()) == ["run.log", "scenes.json"]
    assert "new text" in (ep / "scenes.json").read_text(encoding="utf-8")
    assert any("ssenari deyisib" in m for m in logs)


def test_same_script_keeps_everything_for_resume(tmp_path, monkeypatch):
    _fake_build(monkeypatch, tmp_path, "same")
    ep = tmp_path / "Episodes" / "s"
    _scenes_json(ep, [{"n": 1, "section": "A", "text": "same", "type": "photo"}])
    _write(ep / "narration.wav")
    pipeline.start("x", log=lambda m: None)
    assert (ep / "narration.wav").exists()
    assert '"photo"' in (ep / "scenes.json").read_text(encoding="utf-8")


def test_resume_of_unknown_episode_exits_2_without_creating_dir(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(pipeline, "ROOT", str(tmp_path))
    with pytest.raises(SystemExit) as ei:
        pipeline.main(["--resume", "nope"])
    assert ei.value.code == 2
    assert "epizod tapilmadi: nope" in capsys.readouterr().out
    assert not (tmp_path / "Episodes" / "nope").exists()


def test_voice_done_requires_every_duration(tmp_path):
    _write(tmp_path / "narration.wav")
    _scenes_json(tmp_path, [{"n": 1, "duration": 2.0}, {"n": 2}])
    assert not pipeline._voiced(str(tmp_path))
    _scenes_json(tmp_path, [{"n": 1, "duration": 2.0}, {"n": 2, "duration": 1.0}])
    assert pipeline._voiced(str(tmp_path))
    (tmp_path / "narration.wav").unlink()
    assert not pipeline._voiced(str(tmp_path))


def test_images_done_only_needs_photo_scenes(tmp_path):
    done = pipeline._all("img", "png", photo_only=True)
    assert not done(str(tmp_path))
    _scenes_json(tmp_path, [{"n": 1, "type": "photo"}, {"n": 2, "type": "photo"}])
    _write(tmp_path / "img" / "sc01.png")
    assert not done(str(tmp_path))
    _scenes_json(tmp_path, [{"n": 1, "type": "photo"}, {"n": 2, "type": "anim"}])   # photo -> anim conversion
    assert done(str(tmp_path))


def test_planned_requires_every_scene_typed(tmp_path):
    assert not pipeline._planned(str(tmp_path))
    _scenes_json(tmp_path, [{"n": 1, "type": "photo"}, {"n": 2, "type": None}])
    assert not pipeline._planned(str(tmp_path))
    _scenes_json(tmp_path, [{"n": 1, "type": "photo"}, {"n": 2, "type": "anim"}])
    assert pipeline._planned(str(tmp_path))


def test_published_is_the_episode_marker_not_the_output_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "ROOT", str(tmp_path))
    ep = tmp_path / "Episodes" / "s"
    _scenes_json(ep, [{"n": 1, "type": "photo"}], slug="s")
    _write(tmp_path / "Hazir_Videolar" / "s" / "youtube.txt")
    assert not pipeline._published(str(ep))
    _write(ep / "published")
    assert pipeline._published(str(ep))
    assert "published" in pipeline.DERIVED_FILES


def test_music_failure_raises_and_never_skips_music(tmp_path, monkeypatch):
    def fail(*a, **k):
        raise RuntimeError("gpu")
    monkeypatch.setattr(pipeline.subprocess, "run", fail)
    with pytest.raises(RuntimeError):
        pipeline._music(str(tmp_path))
    assert not (tmp_path / "music.skip").exists()
    music = next(s for s in pipeline.STAGES if s.name == "music")
    _write(tmp_path / "music.skip")
    assert not music.done(str(tmp_path))


def test_corrupt_scenes_json_resets_the_episode(tmp_path, monkeypatch):
    _fake_build(monkeypatch, tmp_path, "text")
    ep = tmp_path / "Episodes" / "s"
    _write(ep / "scenes.json", '{"title": "T", "sl')
    _write(ep / "narration.wav")
    logs = []
    pipeline.start("x", log=logs.append)
    assert not (ep / "narration.wav").exists()
    assert '"text"' in (ep / "scenes.json").read_text(encoding="utf-8")


def test_resume_accepts_a_path_and_uses_only_the_slug(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "ROOT", str(tmp_path))
    ran = []
    monkeypatch.setattr(pipeline, "run_stages", lambda ep, st, log: ran.append(ep))
    _scenes_json(tmp_path / "Episodes" / "s", [{"n": 1}])
    pipeline.main(["--resume", "Episodes\\s\\\\"])
    assert ran == [os.path.join(str(tmp_path), "Episodes", "s")]
    with pytest.raises(SystemExit) as ei:
        pipeline.main(["--resume", ".."])
    assert ei.value.code == 2


def test_images_done_also_needs_intro_and_outro_backgrounds(tmp_path):
    done = pipeline._all("img", "png", photo_only=True)
    _scenes_json(tmp_path, [{"n": 0, "type": "intro"}, {"n": 1, "type": "photo"}, {"n": 2, "type": "outro"}])
    _write(tmp_path / "img" / "sc01.png")
    assert not done(str(tmp_path))
    _write(tmp_path / "img" / "sc00.png")
    _write(tmp_path / "img" / "sc02.png")
    assert done(str(tmp_path))


def test_bookends_do_not_count_as_a_script_change(tmp_path, monkeypatch):
    _fake_build(monkeypatch, tmp_path, "same")
    ep = tmp_path / "Episodes" / "s"
    _scenes_json(ep, [{"n": 0, "type": "intro", "section": "", "text": "Hi!"},
                      {"n": 1, "section": "A", "text": "same", "type": "photo"},
                      {"n": 2, "type": "outro", "section": "", "text": "Bye, subscribe!"}])
    _write(ep / "narration.wav")
    logs = []
    pipeline.start("x", log=logs.append)
    assert (ep / "narration.wav").exists() and not any("deyisib" in m for m in logs)
