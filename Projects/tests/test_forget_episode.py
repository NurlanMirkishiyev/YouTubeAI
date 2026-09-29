"""Istifadeci 2026-09-29: video hazir olub tesdiqlenende pipeline o video barede hec ne saxlamir."""
import os

import pytest

import forget_episode as fe


def _episode(root, slug, log_name=None):
    ep = root / "Episodes" / slug
    (ep / "bg").mkdir(parents=True)
    (ep / "bg" / "sc01.png").write_bytes(b"x")
    (ep / f"{slug}.mp4").write_bytes(b"v")
    name = log_name or f"_run_{slug}.log"
    (root / "Episodes" / name).write_text(f"FAZA F: 'T' -> {ep}\n[1/11] script_gen ...\n", encoding="utf-8")
    (root / "Episodes" / (name + ".err")).write_text("", encoding="utf-8")
    return ep


def test_removes_episode_dir_and_its_run_logs_even_with_short_log_names(tmp_path):
    ep = _episode(tmp_path, "why-9-99-feels-cheaper", log_name="_run_why-9-99-resume2.log")
    (tmp_path / "Episodes" / "_run_why-9-99-feels-cheaper.log").write_text(f"FAZA F: 'T' -> {ep}\n", encoding="utf-8")

    fe.forget("why-9-99-feels-cheaper", str(tmp_path / "Episodes"))

    assert sorted(os.listdir(tmp_path / "Episodes")) == []


def test_other_episodes_and_delivered_video_stay(tmp_path):
    _episode(tmp_path, "what-is-cash-flow")
    _episode(tmp_path, "what-is-cash-flow-2")        # prefiks oxsarligi basqa epizodu silmemelidir
    out = tmp_path / "Hazir_Videolar" / "what-is-cash-flow"
    out.mkdir(parents=True)
    (out / "what-is-cash-flow.mp4").write_bytes(b"v")

    fe.forget("what-is-cash-flow", str(tmp_path / "Episodes"))

    assert sorted(os.listdir(tmp_path / "Episodes")) == [
        "_run_what-is-cash-flow-2.log", "_run_what-is-cash-flow-2.log.err", "what-is-cash-flow-2"]
    assert (out / "what-is-cash-flow.mp4").read_bytes() == b"v"


@pytest.mark.parametrize("bad", ["", ".", "..", "../x", r"a\b", "a/b", "C:x"])
def test_rejects_unsafe_slug(tmp_path, bad):
    (tmp_path / "Episodes").mkdir()
    with pytest.raises(ValueError):
        fe.forget(bad, str(tmp_path / "Episodes"))


def test_missing_episode_is_error(tmp_path):
    (tmp_path / "Episodes").mkdir()
    with pytest.raises(FileNotFoundError):
        fe.forget("nope", str(tmp_path / "Episodes"))
