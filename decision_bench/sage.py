"""Levanto's native Choice API, adapted to the benchmark's categorical contract."""
import json
import math
import time
import urllib.error
import urllib.request

from . import openai_compat
from .config import env_value
from .corpus import JUDGMENT_POLICY, public_input
from .errors import CallError

URL = "https://sage.levanto.ai/decide"


def completion(model, case, timeout, api_model=None):
    if api_model is not None:
        raise CallError("Sage selects its hosted model; --api-model is unsupported", status="config_invalid")
    key = env_value("SAGE_API_KEY")
    if not key:
        raise CallError("SAGE_API_KEY is not set; see .env.example", status="auth_missing")
    data = public_input(case)
    if len(data["questions"]) != 1 or case.get("assets"):
        raise CallError("Sage adapter requires one text choice question", status="config_invalid")
    q = data["questions"][0]
    payload = {"content": json.dumps(data["state"], ensure_ascii=False), "reasoning": "auto",
               "question": {"id": q["id"], "kind": "choice",
                            "instructions": JUDGMENT_POLICY + q["instructions"],
                            "options": [{"option": k, "description": v} for k, v in q["options"].items()]}}
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(), headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json",
        "User-Agent": "DecisionBench (classification evaluation)"})

    def redact(value):
        return openai_compat.redact(value, extra_secrets=(key,), extra_endpoints=(URL,))

    started = time.perf_counter()
    try:
        with urllib.request.build_opener(openai_compat.NoRedirect).open(req, timeout=timeout) as response:
            text, status = response.read().decode(), response.status
    except urllib.error.HTTPError as e:
        try:
            body = redact(e.read().decode(errors="replace"))
        finally:
            e.close()
        raise CallError(f"HTTP {e.code}: {body[:500]}", raw={"status": e.code, "body": body},
                        retryable=e.code in openai_compat.RETRYABLE, status=e.code) from e
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        raise CallError(redact(str(e)), retryable=True, status="transport_error") from e
    try:
        raw = redact(json.loads(text))
        if raw["id"] != q["id"] or raw["kind"] != "choice":
            raise ValueError("Mismatched question")
        result, meta = raw["result"], raw.get("meta", {})
        entries = result["probabilities"]
        probs = {p["option"]: p["probability"] for p in entries}
        if len(probs) != len(entries) or set(probs) != set(q["options"]):
            raise ValueError("Mismatched options")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
               or not 0 <= v <= 1 for v in probs.values()) or sum(probs.values()) <= 0:
            raise ValueError("Invalid probabilities")
        total = sum(probs.values())
        answer = {"label": result["chosen"], "probabilities": {k: v / total for k, v in probs.items()}}
    except (ValueError, KeyError, TypeError, AttributeError):
        raise CallError("Sage returned an invalid Choice response", status="invalid_transport_output")
    return {"raw": raw, "response": {"answers": {q["id"]: answer}}, "source": "native-renormalized",
            "output_text": json.dumps(raw, ensure_ascii=False), "resolved_model": meta.get("model"),
            "http_status": status, "provider_duration_ms": meta.get("latency_ms"),
            "adapter_duration_ms": (time.perf_counter() - started) * 1000,
            "usage": {"input_tokens": (meta.get("usage") or {}).get("billed_input_tokens"), "output_tokens": None, "cached_input_tokens": None,
                      "reasoning_output_tokens": (meta.get("reasoning") or {}).get("tokens")},
            "cost_usd": None, "cost_basis": "unavailable", "payload": payload}
