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


# Sehne bayqusu: referans sekil + prompt multipart ile /images/edits-e gedir, fon seffaf
def test_edit_image_sends_reference_as_multipart(monkeypatch, tmp_path):
    import base64
    ref = tmp_path / "ref.png"
    ref.write_bytes(b"PNGDATA")
    sent = {}

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"data": [{"b64_json": base64.b64encode(b"OUT").decode()}]}).encode()

    def urlopen(req, timeout):
        sent["url"], sent["body"], sent["ctype"] = req.full_url, req.data, req.headers["Content-type"]
        return Resp()

    monkeypatch.setattr(llm.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(llm, "_api_key", lambda prov: "k")
    out = llm.edit_image("owl waving", str(ref), model="gpt-image-2", size="1024x1536", background="transparent")
    assert out == b"OUT"
    assert sent["url"].endswith("/images/edits")
    assert sent["ctype"].startswith("multipart/form-data; boundary=")
    for part in (b'name="image[]"; filename="ref.png"', b"PNGDATA", b'name="background"', b"transparent",
                 b'name="model"', b"gpt-image-2", b"owl waving"):
        assert part in sent["body"]
