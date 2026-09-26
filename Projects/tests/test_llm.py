import io
import json
import urllib.error

import pytest

import llm


def _http_error(code, body):
    return urllib.error.HTTPError("u", code, "x", {}, io.BytesIO(json.dumps(body).encode()))


# E2E ep4: "credit_balance_exhausted" 429 ile gelir - muveqqeti limit kimi 4x tekrarlanirdi,
# istifadeci uzun JSON gorurdu. Indi derhal aydin mesajla dayanir.
def test_exhausted_credits_stop_immediately_with_a_clear_message(monkeypatch):
    calls = []

    def urlopen(req, timeout):
        calls.append(1)
        raise _http_error(429, {"error": {"type": "insufficient_quota", "code": "credit_balance_exhausted"}})

    monkeypatch.setattr(llm.urllib.request, "urlopen", urlopen)
    with pytest.raises(llm.LLMError) as e:
        llm._post("https://x", "k", {})
    assert len(calls) == 1 and "balans" in str(e.value).lower()
