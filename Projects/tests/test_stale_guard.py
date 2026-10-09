"""Reyestr #125-#126 (istifadeci 2026-10-10: "pipeline-da kohne fon ve ya kohne kod kimi xetalarin qarsisini al").
#125: animasiyaya kecmis sehnenin kohne bg/scNN.png-si qalib yalanci tekrar verdi (#124) - kohne artefakt sinfi.
#126: kod duzelisi edilende hele isleyen merhele/retry kohne kodla davam edirdi - kohne kod sinfi."""
import json

import pytest

import code_watch as cw
import pipeline as pl
import stages as st


def _ctx(tmp_path):
    return st.Ctx(topic="T", slug="t", ep_dir=str(tmp_path), words=1, music=None,
                  min_seconds=1.0, max_seconds=2.0, provider="openai")


def _episode(tmp_path, scenes):
    (tmp_path / "scenes.json").write_text(json.dumps({"scenes": scenes}))
    for d in ("bg", "bg_hd", "owl", "audio"):
        (tmp_path / d).mkdir()


# --- #125 kohne artefakt ----------------------------------------------------------------------

def test_bg_of_an_animated_scene_is_stale(tmp_path):
    _episode(tmp_path, [{"bg_prompt": "a"}, {"bg_prompt": "b", "visual": {"kind": "compare"}}])
    for d in ("bg", "bg_hd"):
        for n in (1, 2):
            (tmp_path / d / f"sc{n:02d}.png").write_bytes(b"x")
    stale = sorted(p.replace(str(tmp_path), "").replace("\\", "/") for p in st.stale_files(_ctx(tmp_path)))
    assert stale == ["/bg/sc02.png", "/bg_hd/sc02.png"]


def test_numbered_files_beyond_the_scene_count_are_stale_but_cards_are_kept(tmp_path):
    _episode(tmp_path, [{"bg_prompt": "a"}])
    for name in ("owl/sc01.png", "owl/sc02.png", "owl/intro.png", "audio/sc01.wav", "audio/sc03.wav",
                 "audio/intro.wav", "bg/sc05.png"):
        (tmp_path / name).write_bytes(b"x")
    ctx = _ctx(tmp_path)
    st.prune_stale(ctx)
    left = sorted(str(p.relative_to(tmp_path)).replace("\\", "/") for p in tmp_path.rglob("*.*")
                  if p.name != "scenes.json")
    assert left == ["audio/intro.wav", "audio/sc01.wav", "owl/intro.png", "owl/sc01.png"]


def test_prune_without_scenes_json_does_nothing(tmp_path):
    (tmp_path / "bg").mkdir()
    (tmp_path / "bg" / "sc01.png").write_bytes(b"x")
    assert st.prune_stale(_ctx(tmp_path)) == []
    assert (tmp_path / "bg" / "sc01.png").exists()


def test_pipeline_prunes_stale_files_before_every_stage(tmp_path):
    seen = []
    stages = (st.Stage("a", lambda c, f: [], lambda c: False, lambda c: []),
              st.Stage("b", lambda c, f: [], lambda c: False, lambda c: []))
    rc = pl.run_pipeline(_ctx(tmp_path), str(tmp_path / "state.json"), stages=stages,
                         runner=lambda s, c, f, l: seen.append(s.name) or [], gates={},
                         prune=lambda c: seen.append("prune") or [])
    assert rc == 0 and seen == ["prune", "a", "prune", "b"]


# --- #126 kohne kod ---------------------------------------------------------------------------

class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_code_change_counts_only_after_it_is_stable():
    fps, clock = iter(["v1", "v2", "v3", "v3", "v3"]), Clock()
    w = cw.CodeWatch(fingerprint=lambda: next(fps), clock=clock, debounce=20)
    assert w.changed() is False            # v2: deyisiklik basladi
    clock.t = 30
    assert w.changed() is False            # v3: hele redakte olunur, sayac sifirlanir
    clock.t = 40
    assert w.changed() is False            # v3 10 s sabit
    clock.t = 55
    assert w.changed() is True             # v3 25 s sabit -> yeni kod hazirdir


def test_fingerprint_ignores_tests_and_sees_code(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "a.py").write_text("x = 1")
    (tmp_path / "tests" / "test_a.py").write_text("y = 1")
    before = cw.fingerprint([str(tmp_path)])
    (tmp_path / "tests" / "test_a.py").write_text("y = 2")
    assert cw.fingerprint([str(tmp_path)]) == before
    (tmp_path / "a.py").write_text("x = 2")
    assert cw.fingerprint([str(tmp_path)]) != before


class FakeProc:
    def __init__(self, waits_before_exit):
        self.left, self.pid, self.killed = waits_before_exit, 7, False

    def wait(self, timeout=None):
        if self.left <= 0 or self.killed:
            return -1 if self.killed else 0
        self.left -= 1
        raise cw.subprocess.TimeoutExpired("x", timeout)


def test_running_stage_is_stopped_when_code_changes():
    proc, answers = FakeProc(10), iter([False, False, True])
    rc = cw.wait_or_stop(proc, lambda: next(answers), poll=0, kill=lambda p: setattr(p, "killed", True))
    assert rc == cw.CODE_CHANGED and proc.killed


def test_stage_that_finishes_returns_its_own_exit_code():
    rc = cw.wait_or_stop(FakeProc(2), lambda: False, poll=0, kill=lambda p: None)
    assert rc == 0


def test_code_change_during_a_stage_relaunches_from_that_stage_without_using_a_retry(tmp_path):
    calls = []
    stages = (st.Stage("a", lambda c, f: [], lambda c: False, lambda c: []),
              st.Stage("b", lambda c, f: [], lambda c: False, lambda c: []))

    def runner(s, c, f, l):
        calls.append(s.name)
        return [cw.CODE_CHANGED_MSG] if s.name == "b" else []
    with pytest.raises(cw.Relaunch) as e:
        pl.run_pipeline(_ctx(tmp_path), str(tmp_path / "state.json"), stages=stages, runner=runner,
                        gates={}, sleep=lambda s: None, prune=lambda c: [])
    assert calls == ["a", "b"] and e.value.from_stage is None


def test_code_change_between_stages_relaunches_before_the_next_stage(tmp_path):
    calls, answers = [], iter([False, True])
    stages = (st.Stage("a", lambda c, f: [], lambda c: False, lambda c: []),
              st.Stage("b", lambda c, f: [], lambda c: False, lambda c: []))
    with pytest.raises(cw.Relaunch):
        pl.run_pipeline(_ctx(tmp_path), str(tmp_path / "state.json"), stages=stages,
                        runner=lambda s, c, f, l: calls.append(s.name) or [], gates={},
                        prune=lambda c: [], watch=lambda: next(answers))
    assert calls == ["a"]


def test_relaunch_keeps_a_forced_rerun(tmp_path):
    stages = tuple(st.Stage(n, lambda c, f: [], lambda c: True, lambda c: []) for n in "abc")
    with pytest.raises(cw.Relaunch) as e:
        pl.run_pipeline(_ctx(tmp_path), str(tmp_path / "state.json"), stages=stages, from_idx=1,
                        runner=lambda s, c, f, l: [cw.CODE_CHANGED_MSG], gates={},
                        sleep=lambda s: None, prune=lambda c: [])
    assert e.value.from_stage == "b"      # --from b qorunur, yoxsa c "hazirdir" deye kohne qalardi


def test_relaunch_command_resumes_the_same_episode():
    cmd = cw.relaunch_cmd("run.py", "slug-x", "b")
    assert cmd[-4:] == ["--resume", "slug-x", "--from", "b"]
    assert cw.relaunch_cmd("run.py", "slug-x", None)[-2:] == ["--resume", "slug-x"]


def test_scene_moved_to_animation_inside_check_bgs_loses_its_photo_at_once(tmp_path):
    # #125: check_bgs oz daxilinde de tekrar kadr yoxlayir - merheleler arasi prune-u gozlemir
    import check_bgs as cb
    _episode(tmp_path, [{"bg_prompt": "a"}, {"bg_prompt": "b"}])
    for d in ("bg", "bg_hd"):
        (tmp_path / d / "sc02.png").write_bytes(b"x")
    (tmp_path / "bg" / "sc01.png").write_bytes(b"x")
    cb.apply_visuals(str(tmp_path / "scenes.json"), {2: {"kind": "compare"}})
    assert not (tmp_path / "bg" / "sc02.png").exists() and not (tmp_path / "bg_hd" / "sc02.png").exists()
    assert (tmp_path / "bg" / "sc01.png").exists()
