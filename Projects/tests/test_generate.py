import json

import pytest

import generate
import llm


def test_retry_returns_on_first_success():
    seen = []
    assert generate.with_retry(lambda p: seen.append(p) or "ok", "cat", rewrite=None, label="x") == "ok"
    assert seen == ["cat"]


def test_safety_rejection_rewrites_the_prompt_on_the_same_topic():
    seen = []

    def fn(p):
        seen.append(p)
        if p == "cat":
            raise llm.LLMError("HTTP 400: moderation_blocked")
        return "ok"
    assert generate.with_retry(fn, "cat", rewrite=lambda p: p + " safe", label="x") == "ok"
    assert seen == ["cat", "cat safe"]


def test_exhausted_attempts_raise_and_never_substitute():
    n = {"n": 0}

    def fn(p):
        n["n"] += 1
        raise RuntimeError("network")
    with pytest.raises(generate.GenerationFailed, match="x"):
        generate.with_retry(fn, "cat", rewrite=None, label="x", attempts=3)
    assert n["n"] == 3


def test_empty_balance_is_raised_at_once():
    n = {"n": 0}

    def fn(p):
        n["n"] += 1
        raise llm.LLMError("OpenAI balansi bitib: x")
    with pytest.raises(llm.LLMError):
        generate.with_retry(fn, "cat", rewrite=None, label="x")
    assert n["n"] == 1


def test_run_parallel_finishes_the_others_then_raises():
    done = []

    def fn(x):
        if x == 2:
            raise generate.GenerationFailed("two")
        done.append(x)
    with pytest.raises(generate.GenerationFailed):
        generate.run_parallel(fn, [1, 2, 3], workers=1)
    assert done == [1, 3]


def test_run_parallel_prefers_the_balance_error():
    def fn(x):
        raise llm.LLMError("OpenAI balansi bitib") if x == 2 else generate.GenerationFailed("x")
    with pytest.raises(llm.LLMError, match="balansi"):
        generate.run_parallel(fn, [1, 2], workers=1)


def test_atomic_writes_leave_no_tmp_and_replace(tmp_path):
    p = tmp_path / "a.json"
    generate.atomic_json(str(p), {"a": 1})
    generate.atomic_bytes(str(tmp_path / "b.png"), b"xy")
    assert json.loads(p.read_text()) == {"a": 1} and (tmp_path / "b.png").read_bytes() == b"xy"
    assert sorted(x.name for x in tmp_path.iterdir()) == ["a.json", "b.png"]
    assert generate.tmp_path(str(tmp_path / "v.mp4")).endswith("v.tmp.mp4")


def test_run_parallel_stops_queued_items_after_an_empty_balance():
    ran = []

    def fn(x):
        ran.append(x)
        if x == 2:
            raise llm.LLMError("OpenAI balansi bitib")
    with pytest.raises(llm.LLMError):
        generate.run_parallel(fn, [1, 2, 3, 4], workers=1)
    assert ran == [1, 2]


def test_last_attempt_does_not_waste_a_rewrite():
    rewrites = []

    def fn(p):
        raise llm.LLMError("HTTP 400: moderation_blocked")
    with pytest.raises(generate.GenerationFailed):
        generate.with_retry(fn, "cat", rewrite=lambda p: rewrites.append(p) or p, label="x", attempts=2)
    assert len(rewrites) == 1
