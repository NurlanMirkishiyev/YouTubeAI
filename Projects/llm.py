"""OpenAI cagirislari: chat_json (gpt-4o-mini), generate_image / edit_image (gpt-image-2). Acar .env-den."""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
import uuid

BASE = "https://api.openai.com/v1"
TEXT_MODEL = "gpt-4o-mini"
IMAGE_MODEL = "gpt-image-2"
RETRIES = 6
TIMEOUT_S = 300
ENV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")


BALANCE_MARK = "balansi bitib"
BALANCE_CODES = ("insufficient_quota", "billing_hard_limit_reached", "billing")
SAFETY_CODES = ("moderation_blocked", "safety system", "content_policy")
REWRITE_SYSTEM = ("This image prompt was rejected by the safety system. Rewrite it so it passes, keeping the SAME "
                  "topic, scene and meaning; remove only what could be unsafe (weapons, violence, real brands, "
                  "real people, minors). Answer ONLY JSON: {\"prompt\": \"...\"}")


class LLMError(Exception):
    pass


def is_balance_error(e: BaseException) -> bool:
    return isinstance(e, LLMError) and BALANCE_MARK in str(e)


def is_safety_error(e: BaseException) -> bool:
    return isinstance(e, LLMError) and any(c in str(e).lower() for c in SAFETY_CODES)


def api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key and os.path.isfile(ENV):
        for line in open(ENV, encoding="utf-8"):
            if line.strip().startswith("OPENAI_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"')
    if not key:
        raise LLMError("OPENAI_API_KEY yoxdur (.env)")
    return key


def send(url: str, body: bytes, content_type: str, *, opener=urllib.request.urlopen, sleep=time.sleep) -> dict:
    headers = {"Content-Type": content_type, "Authorization": f"Bearer {api_key()}"}
    last = ""
    for attempt in range(RETRIES):
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with opener(req, timeout=TIMEOUT_S) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}"
            if any(c in last for c in BALANCE_CODES):
                raise LLMError(f"OpenAI {BALANCE_MARK}: " + last) from e
            if e.code not in (408, 409, 429) and e.code < 500:
                raise LLMError(last) from e
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last = f"{type(e).__name__}: {e}"
        sleep(min(2 ** attempt, 30))
    raise LLMError(f"{RETRIES} cehdden sonra ugursuz - {last}")


def chat_json(system: str, user: str, *, model: str = TEXT_MODEL, max_tokens: int = 4000,
              schema: dict | None = None) -> dict:
    """schema verilse strict structured output (cavab sxemden kenara cixa bilmir), yoxsa json_object."""
    fmt = ({"type": "json_schema", "json_schema": {"name": "answer", "strict": True, "schema": schema}}
           if schema else {"type": "json_object"})
    payload = {"model": model, "temperature": 0.4, "max_tokens": max_tokens,
               "response_format": fmt,
               "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    res = send(f"{BASE}/chat/completions", json.dumps(payload).encode("utf-8"), "application/json")
    try:
        return json.loads(res["choices"][0]["message"]["content"])
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise LLMError("gozlenilmeyen chat cavabi") from e


def rewrite_safe(prompt: str) -> str:
    """Tehlukesizlik reddinden sonra eyni movzuda yeni prompt."""
    return str(chat_json(REWRITE_SYSTEM, prompt, max_tokens=400).get("prompt") or prompt)


def _image(res: dict) -> bytes:
    try:
        return base64.b64decode(res["data"][0]["b64_json"])
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError("gozlenilmeyen sekil cavabi") from e


def generate_image(prompt: str, *, size: str = "1536x1024", quality: str = "medium") -> bytes:
    payload = {"model": IMAGE_MODEL, "prompt": prompt, "size": size, "quality": quality, "n": 1}
    return _image(send(f"{BASE}/images/generations", json.dumps(payload).encode("utf-8"), "application/json"))


def _multipart(fields: dict[str, str], files: dict[str, str]) -> tuple[bytes, str]:
    b = uuid.uuid4().hex
    out = bytearray()
    for k, v in fields.items():
        out += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode("utf-8")
    for k, path in files.items():
        out += (f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{os.path.basename(path)}"\r\n'
                "Content-Type: image/png\r\n\r\n").encode("utf-8")
        out += open(path, "rb").read() + b"\r\n"
    out += f"--{b}--\r\n".encode("utf-8")
    return bytes(out), f"multipart/form-data; boundary={b}"


def edit_image(prompt: str, ref_path: str, *, size: str = "1024x1536", quality: str = "low") -> bytes:
    body, ctype = _multipart({"model": IMAGE_MODEL, "prompt": prompt, "size": size, "quality": quality,
                              "background": "opaque", "n": "1"}, {"image[]": ref_path})
    return _image(send(f"{BASE}/images/edits", body, ctype))
