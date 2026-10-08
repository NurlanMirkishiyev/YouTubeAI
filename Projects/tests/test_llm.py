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


# Istifadeci 2026-10-08: sekil yaratmadan (gpt-image-2) basqa butun LLM merheleleri Gemini-ye. Koddaki model adlari
# rol kimi oxunur: "gpt-4o-mini"/None = yazan (Flash), "gpt-4o" = yoxlayan (Pro).
def _capture(monkeypatch, usage=None):
    sent = []
    monkeypatch.setattr(llm, "_api_key", lambda prov: "k")
    monkeypatch.setattr(llm, "_post", lambda url, key, payload: sent.append((url, payload)) or {
        "choices": [{"message": {"content": "ok"}}], "usage": usage or {}})
    return sent


def test_gemini_maps_the_writer_and_checker_roles(monkeypatch):
    sent = _capture(monkeypatch)
    llm.chat("s", "u", provider="gemini")
    llm.chat("s", "u", provider="gemini", model="gpt-4o-mini")
    llm.chat("s", "u", provider="gemini", model="gpt-4o")
    assert [p["model"] for _, p in sent] == [llm.GEMINI_WRITE, llm.GEMINI_WRITE, llm.GEMINI_CHECK]
    assert all("generativelanguage.googleapis.com" in u for u, _ in sent)
    assert llm.PROVIDERS["gemini"].key_env == "GEMINI_API_KEY"


def test_gemini_gets_room_for_thinking_tokens(monkeypatch):
    """Duşunme tokenleri max_tokens-i yeyib JSON-u kesmemelidir (research hakimi max_tokens=200 isledir)."""
    sent = _capture(monkeypatch)
    llm.chat("s", "u", provider="gemini", max_tokens=200)
    assert sent[0][1]["max_tokens"] >= 200 + llm.THINK_ROOM


def test_gemini_cost_counts_hidden_thinking_tokens(monkeypatch, capsys):
    """Real probe: prompt 45, completion 48, total 321 - ferq dusunme tokenleridir ve pullu cixisdir."""
    _capture(monkeypatch, usage={"prompt_tokens": 1_000_000, "completion_tokens": 0, "total_tokens": 2_000_000})
    llm.chat("s", "u", provider="gemini")
    price_in, price_out = llm.GEMINI_PRICES[llm.GEMINI_WRITE]
    assert f"~${price_in + price_out:.4f}" in capsys.readouterr().out


def test_default_provider_is_gemini_unless_env_says_otherwise():
    assert llm.default_provider({}) == "gemini"
    assert llm.default_provider({"LLM_PROVIDER": "openai"}) == "openai"
