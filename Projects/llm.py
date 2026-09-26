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
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

ENV_FILE = r"C:\YouTubeAI\.env"
TIMEOUT_S = 180
MAX_RETRIES = 4


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
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
    last = ""
    for attempt in range(MAX_RETRIES):
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            last = f"HTTP {e.code}: {detail}"
            if e.code not in (408, 409, 429) and e.code < 500:
                raise LLMError(last) from e
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last = f"{type(e).__name__}: {e}"
        if attempt < MAX_RETRIES - 1:
            wait = 2 ** attempt
            print(f"  ... cehd {attempt + 1} ugursuz ({last}); {wait}s sonra tekrar")
            time.sleep(wait)
    raise LLMError(f"{MAX_RETRIES} cehdden sonra ugursuz - {last}")


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
