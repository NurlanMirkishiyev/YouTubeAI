import io
import json
import urllib.error

import pytest

import llm


class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_send_retries_rate_limit_then_returns_json(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    calls = []

    def opener(req, timeout):
        calls.append(1)
        if len(calls) < 3:
            raise urllib.error.HTTPError(req.full_url, 429, "rate", {}, io.BytesIO(b"slow down"))
        return Resp(json.dumps({"ok": 1}).encode())
    assert llm.send("http://x", b"{}", "application/json", opener=opener, sleep=lambda s: None) == {"ok": 1}
    assert len(calls) == 3


def test_send_gives_up_on_bad_request(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")

    def opener(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 400, "bad", {}, io.BytesIO(b"moderation"))
    with pytest.raises(llm.LLMError):
        llm.send("http://x", b"{}", "application/json", opener=opener, sleep=lambda s: None)


def test_models_are_gpt_image_2_and_gpt_4o_mini():
    assert llm.IMAGE_MODEL == "gpt-image-2" and llm.TEXT_MODEL == "gpt-4o-mini"


@pytest.mark.parametrize("body", [b'{"error": {"code": "insufficient_quota"}}',
                                  b'{"error": {"code": "billing_hard_limit_reached"}}'])
def test_send_stops_on_any_empty_balance_error(monkeypatch, body):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    calls = []

    def opener(req, timeout):
        calls.append(1)
        raise urllib.error.HTTPError(req.full_url, 429, "quota", {}, io.BytesIO(body))
    with pytest.raises(llm.LLMError) as ei:
        llm.send("http://x", b"{}", "application/json", opener=opener, sleep=lambda s: None)
    assert llm.is_balance_error(ei.value) and len(calls) == 1


def test_balance_and_safety_errors_are_recognised():
    assert llm.is_balance_error(llm.LLMError("OpenAI balansi bitib: x"))
    assert not llm.is_balance_error(RuntimeError("OpenAI balansi bitib"))
    assert llm.is_safety_error(llm.LLMError('HTTP 400: {"code": "moderation_blocked"}'))
    assert llm.is_safety_error(llm.LLMError("HTTP 400: rejected by the safety system"))
    assert not llm.is_safety_error(llm.LLMError("HTTP 400: bad size"))


def test_chat_json_with_schema_requests_strict_structured_output(monkeypatch):
    sent = {}

    def fake_send(url, body, ctype):
        sent.update(json.loads(body))
        return {"choices": [{"message": {"content": '{"a": 1}'}}]}
    monkeypatch.setattr(llm, "send", fake_send)
    assert llm.chat_json("s", "u", schema={"type": "object"}) == {"a": 1}
    rf = sent["response_format"]
    assert rf["type"] == "json_schema" and rf["json_schema"]["strict"] is True
    assert rf["json_schema"]["schema"] == {"type": "object"}
