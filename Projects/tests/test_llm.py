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


# math audit (2026-10-02): gpt-4o TPM limiti - 1+2+4 s backoff azdir, 4 defe 3-cu cehde catdi.
# Indi API-nin dediyi muddet ("try again in 2.272s") + ehtiyat gozlenilir ve TPM-de daha cox cehd edilir.
def test_rate_limit_waits_as_long_as_the_api_says(monkeypatch):
    calls, waits = [], []

    def urlopen(req, timeout):
        calls.append(1)
        if len(calls) < 6:
            raise _http_error(429, {"error": {"message": "Rate limit reached for gpt-4o on tokens per min "
                                                         "(TPM). Please try again in 7.5s.", "code": "rate_limit_exceeded"}})
        return io.BytesIO(b'{"ok": 1}')

    monkeypatch.setattr(llm.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(llm.time, "sleep", waits.append)
    assert llm._post("https://x", "k", {}) == {"ok": 1}
    assert len(calls) == 6 and all(w >= 7.5 for w in waits)


def test_retry_after_parses_milliseconds():
    assert llm.retry_after("Please try again in 950ms.") == pytest.approx(0.95)
    assert llm.retry_after("Please try again in 2.272s.") == pytest.approx(2.272)
    assert llm.retry_after("other") is None


def test_chat_null_content_is_an_llm_error_not_a_crash(monkeypatch):
    """#66: model sekli redd edende content=null gelir - check_bgs AttributeError ile cokurdu."""
    monkeypatch.setattr(llm, "_api_key", lambda prov: "k")
    monkeypatch.setattr(llm, "_post", lambda url, key, payload: {
        "choices": [{"message": {"content": None, "refusal": "I can't help with that."}}], "usage": {}})
    with pytest.raises(llm.LLMError, match="bos cavab"):
        llm.chat("s", "u", provider="openai")


def test_gemini_provider_is_removed():
    """Istifadeci 2026-10-10: "gemini hissesini cixart" -> kod tam silindi; yalniz OpenAI (+ deepseek/ollama)."""
    assert "gemini" not in llm.PROVIDERS
    assert not any(n.startswith("GEMINI") or n == "THINK_ROOM" for n in dir(llm))


def test_default_provider_is_openai_unless_env_says_otherwise():
    """Istifadeci 2026-10-08 (gec): sekilden basqa modeller GPT (yazan gpt-4o-mini, yoxlayan gpt-4o);
    2026-10-10: Gemini kodu silindi - kohne .env LLM_PROVIDER=gemini openai-ye dusur."""
    assert llm.default_provider({}) == "openai"
    assert llm.default_provider({"LLM_PROVIDER": "deepseek"}) == "deepseek"
    assert llm.default_provider({"LLM_PROVIDER": "gemini"}) == "openai"


def test_a_truncated_answer_is_an_error_not_silent_text(monkeypatch):
    """#104 real probe: model bolme yazanda ~8000 token dusundu, out=9384 = limit -> metn cumlenin ortasinda
    kesildi ('which begins the moment you'), redaktor 'ends abruptly' dedi. Kesilmis cavab LLMError-dur."""
    monkeypatch.setattr(llm, "_api_key", lambda prov: "k")
    monkeypatch.setattr(llm, "_post", lambda url, key, payload: {
        "choices": [{"message": {"content": "which begins the moment you"}, "finish_reason": "length"}]})
    with pytest.raises(llm.LLMError, match="kesildi"):
        llm.chat("s", "u", provider="openai")
