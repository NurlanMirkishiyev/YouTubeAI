from types import SimpleNamespace

import comfy
import state


def test_new_state_and_with_stage_is_immutable():
    s0 = state.new_state("T", "t", ["a", "b"])
    assert s0["stages"]["a"]["status"] == "pending"
    s1 = state.with_stage(s0, "a", status="done")
    assert s1["stages"]["a"]["status"] == "done"
    assert s0["stages"]["a"]["status"] == "pending"


def test_write_read_roundtrip(tmp_path):
    p = str(tmp_path / "state.json")
    assert state.read_state(p) is None
    s = state.new_state("T", "t", ["a"])
    state.write_state(p, s)
    assert state.read_state(p) == s
    assert not (tmp_path / "state.json.tmp").exists()


def test_wait_up_polls_until_ready():
    answers = iter([False, False, True])
    slept = []
    assert comfy.wait_up(timeout_s=10, poll_s=1, probe=lambda: next(answers), sleep=slept.append)
    assert slept == [1, 1]


def test_wait_up_times_out():
    assert not comfy.wait_up(timeout_s=3, poll_s=1, probe=lambda: False, sleep=lambda s: None)


class FakeProc:
    def __init__(self):
        self.terminated = False

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        return 0


def test_guard_starts_only_when_needed_and_stops_after():
    up = {"v": False}
    started = []

    def launcher(log):
        started.append(log)
        up["v"] = True
        return FakeProc()

    g = comfy.ComfyGuard("log.txt", probe=lambda: up["v"], launcher=launcher)
    need, no = SimpleNamespace(needs_comfy=True), SimpleNamespace(needs_comfy=False)
    assert g.before([no, need]) is None and started == []
    assert g.before([need, no]) is None and started == ["log.txt"]
    proc = g.proc
    assert g.before([no]) is None and proc.terminated and g.proc is None


def test_guard_leaves_external_comfy_alone():
    g = comfy.ComfyGuard("log.txt", probe=lambda: True, launcher=lambda log: 1 / 0)
    assert g.before([SimpleNamespace(needs_comfy=True)]) is None and g.proc is None
