"""OpenAI-uygun chat API klienti (DeepSeek / OpenAI / lokal Ollama) - yalniz stdlib.
Default provider: openai. Acar C:\\YouTubeAI\\.env faylindan oxunur:
    OPENAI_API_KEY=sk-proj-...
    DEEPSEEK_API_KEY=sk-...        (yalniz --provider deepseek ucun)
Istifade:
    from llm import chat, chat_json, add_provider_arg
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

ENV_FILE = r"C:\YouTubeAI\.env"
TIMEOUT_S = 180
MAX_RETRIES = 4
RATE_RETRIES = 8          # 429 (TPM) - API-nin dediyi muddet gozlenilir, daha cox cehd


@dataclass(frozen=True)
class Provider:
    base_url: str
    model: str
    key_env: str      # bos = acar teleb olunmur (Ollama)
    usd_in: float     # $ / 1M input token (teqribi, yalniz melumat ucun)
    usd_out: float


PROVIDERS: dict[str, Provider] = {
    "deepseek": Provider("https://api.deepseek.com/v1", "deepseek-chat", "DEEPSEEK_API_KEY", 0.28, 0.42),
    "openai":   Provider("https://api.openai.com/v1", "gpt-4o-mini", "OPENAI_API_KEY", 0.15, 0.60),
    "ollama":   Provider("http://127.0.0.1:11434/v1", "qwen2.5:7b-instruct", "", 0.0, 0.0),
}


DEFAULT_PROVIDER = "openai"


class LLMError(RuntimeError):
    """API cagirisinda duzelmez xeta."""


def load_env(path: str = ENV_FILE) -> None:
    """KEY=VAL setirlerini os.environ-a yukleyir (movcud deyerler uzerine yazilmir)."""
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def add_provider_arg(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--provider", choices=sorted(PROVIDERS), default=DEFAULT_PROVIDER)
    ap.add_argument("--model", help="provider defaultunu evez edir")
    ap.add_argument("--temperature", type=float, default=0.7)


def _api_key(prov: Provider) -> str:
    if not prov.key_env:
        return "ollama"
    load_env()
    key = os.environ.get(prov.key_env, "").strip()
    if not key:
        raise LLMError(
            f"{prov.key_env} tapilmadi. {ENV_FILE} faylina elave et:\n  {prov.key_env}=sk-..."
        )
    return key


def _post(url: str, key: str, payload: dict) -> dict:
    """Eksponensial backoff ile POST; 429 ve 5xx tekrarlanir, 4xx derhal atilir."""
    return _send(url, key, json.dumps(payload).encode("utf-8"), "application/json")


def _send(url: str, key: str, body: bytes, content_type: str) -> dict:
    headers = {"Content-Type": content_type, "Authorization": f"Bearer {key}"}
    last, limited = "", False
    for attempt in range(RATE_RETRIES):
        if attempt >= MAX_RETRIES and not limited:
            break
        limited = False
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            last = f"HTTP {e.code}: {detail}"
            if "insufficient_quota" in detail or "credit_balance_exhausted" in detail:
                # 429 ile gelir, amma muveqqeti deyil - tekrar hec ne vermir (ep4 publish 4x tekrarlandi)
                raise LLMError("OpenAI BALANSI BITIB - https://platform.openai.com/settings/organization/"
                               "billing -de kredit elave et, sonra: python run.py --resume <slug>") from e
            if e.code not in (408, 409, 429) and e.code < 500:
                raise LLMError(last) from e
            limited = e.code == 429
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last = f"{type(e).__name__}: {e}"
        if attempt < (RATE_RETRIES if limited else MAX_RETRIES) - 1:
            wait = max(2 ** min(attempt, 4), (retry_after(last) or 0) + 1) if limited else 2 ** attempt
            print(f"  ... cehd {attempt + 1} ugursuz ({last[:160]}); {wait:g}s sonra tekrar")
            time.sleep(wait)
    raise LLMError(f"{attempt + 1} cehdden sonra ugursuz - {last}")


def retry_after(message: str) -> float | None:
    """'Please try again in 2.272s' / '950ms' -> saniye (TPM limiti; 1-2-4 s backoff azdir)."""
    m = re.search(r"try again in (\d+(?:\.\d+)?)\s*(ms|s)\b", message)
    if not m:
        return None
    return float(m.group(1)) / (1000 if m.group(2) == "ms" else 1)


def chat(system: str, user: str | list, *, provider: str = DEFAULT_PROVIDER, model: str | None = None,
         temperature: float = 0.7, max_tokens: int = 8000, json_mode: bool = False) -> str:
    """Chat completion -> metn. json_mode=True ise cavab JSON obyekt olmalidir.
    user siyahi da ola biler (metn + image_url hisseleri) - check_bgs fonlari bele gosterir."""
    if provider not in PROVIDERS:
        raise LLMError("bilinmeyen provider: " + provider)
    prov = PROVIDERS[provider]
    payload: dict = {
        "model": model or prov.model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    t0 = time.time()
    res = _post(f"{prov.base_url}/chat/completions", _api_key(prov), payload)
    try:
        text = res["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise LLMError("gozlenilmeyen cavab formati: " + json.dumps(res)[:500]) from e
    usage = res.get("usage", {})
    cost = (usage.get("prompt_tokens", 0) * prov.usd_in
            + usage.get("completion_tokens", 0) * prov.usd_out) / 1_000_000
    print(f"  {provider}/{payload['model']}  {time.time() - t0:.1f}s  "
          f"in={usage.get('prompt_tokens', 0)} out={usage.get('completion_tokens', 0)}  ~${cost:.4f}")
    return text.strip()


def chat_json(system: str, user: str | list, **kw) -> dict:
    """chat() + JSON parse. Model kod blokuna sarsa da isleyir."""
    raw = chat(system, user, json_mode=True, **kw)
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1].removeprefix("json").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise LLMError(f"JSON parse alinmadi: {e}\n--- cavab ---\n{raw[:800]}") from e


def generate_image(prompt: str, *, model: str, size: str = "1536x1024", quality: str = "low") -> bytes:
    """OpenAI Images API -> PNG baytlari. 429/5xx _post-da tekrarlanir; 4xx (mes. moderation) LLMError."""
    import base64
    prov = PROVIDERS["openai"]
    t0 = time.time()
    res = _post(f"{prov.base_url}/images/generations", _api_key(prov),
                {"model": model, "prompt": prompt, "size": size, "quality": quality, "n": 1})
    try:
        data = base64.b64decode(res["data"][0]["b64_json"])
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError("gozlenilmeyen sekil cavabi: " + json.dumps(res)[:300]) from e
    out_tokens = res.get("usage", {}).get("output_tokens", 0)
    print(f"  image {model}/{quality}  {time.time() - t0:.1f}s  out={out_tokens}", flush=True)
    return data


def _multipart(fields: dict[str, str], files: dict[str, str]) -> tuple[bytes, str]:
    """stdlib multipart/form-data: fields {ad: deyer}, files {ad: fayl yolu} (PNG)."""
    import uuid
    boundary = uuid.uuid4().hex
    out = bytearray()
    crlf = "\r\n"
    for name, value in fields.items():
        out += (f'--{boundary}{crlf}Content-Disposition: form-data; name="{name}"{crlf}{crlf}'
                f'{value}{crlf}').encode("utf-8")
    for name, path in files.items():
        with open(path, "rb") as f:
            data = f.read()
        out += (f'--{boundary}{crlf}Content-Disposition: form-data; name="{name}"; '
                f'filename="{os.path.basename(path)}"{crlf}Content-Type: image/png{crlf}{crlf}').encode("utf-8")
        out += data + crlf.encode("ascii")
    out += f"--{boundary}--{crlf}".encode("utf-8")
    return bytes(out), f"multipart/form-data; boundary={boundary}"


def edit_image(prompt: str, ref_path: str, *, model: str, size: str = "1024x1536", quality: str = "low",
               background: str = "transparent") -> bytes:
    """OpenAI Images edits: referans sekil (personaj) + prompt -> PNG baytlari. Sehne bayqusu ucun -
    2026-09-27 probu: gpt-image-2 personaji (eynek, kostyum, qalstuk) eyni saxlayir, fon seffaf."""
    import base64
    prov = PROVIDERS["openai"]
    t0 = time.time()
    body, ctype = _multipart({"model": model, "prompt": prompt, "size": size, "quality": quality,
                              "background": background, "n": "1"}, {"image[]": ref_path})
    res = _send(f"{prov.base_url}/images/edits", _api_key(prov), body, ctype)
    try:
        data = base64.b64decode(res["data"][0]["b64_json"])
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError("gozlenilmeyen sekil cavabi: " + json.dumps(res)[:300]) from e
    print(f"  owl {model}/{quality}  {time.time() - t0:.1f}s", flush=True)
    return data
