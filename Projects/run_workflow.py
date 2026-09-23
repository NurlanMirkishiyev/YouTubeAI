"""ComfyUI API-ye workflow gonderir ve netice fayllarini gozleyir.
Istifade: python run_workflow.py <workflow.json> [--set KEY=VAL ...] [--wait]
  KEY placeholder: __POS__, __SEED__, __PREFIX__ ...
"""
import sys, json, time, uuid, urllib.request, argparse

API = "http://127.0.0.1:8188"

def submit(workflow: dict) -> str:
    body = json.dumps({"prompt": workflow, "client_id": str(uuid.uuid4())}).encode()
    req = urllib.request.Request(f"{API}/prompt", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.loads(r.read())
    if res.get("node_errors"):
        raise SystemExit("ComfyUI node errors: " + json.dumps(res["node_errors"], indent=1))
    return res["prompt_id"]

def wait(prompt_id: str, timeout_s: int = 600) -> list[str]:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        with urllib.request.urlopen(f"{API}/history/{prompt_id}", timeout=30) as r:
            hist = json.loads(r.read())
        if prompt_id in hist:
            entry = hist[prompt_id]
            if entry.get("status", {}).get("status_str") == "error":
                raise SystemExit("ComfyUI execution error: " + json.dumps(entry["status"].get("messages"), indent=1)[:2000])
            files = [img["filename"] for out in entry["outputs"].values() for img in out.get("images", [])]
            if files:
                return files
        time.sleep(1.5)
    raise SystemExit(f"timeout after {timeout_s}s")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workflow")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VAL")
    ap.add_argument("--wait", action="store_true")
    a = ap.parse_args()
    text = open(a.workflow, encoding="utf-8").read()
    for kv in a.set:
        k, v = kv.split("=", 1)
        text = text.replace(f"__{k}__", json.dumps(v)[1:-1] if not v.lstrip("-").isdigit() else v)
    wf = json.loads(text)
    pid = submit(wf)
    print("submitted", pid)
    if a.wait:
        t = time.time()
        files = wait(pid)
        print("done in %.1fs -> %s" % (time.time() - t, ", ".join(files)))

if __name__ == "__main__":
    main()
