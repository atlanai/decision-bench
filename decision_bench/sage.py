"""Levanto's native Choice API, adapted to the benchmark's categorical contract."""
import base64
import json
import math
import time
import urllib.error
import urllib.request

from . import openai_compat
from .config import env_value
from .corpus import JUDGMENT_POLICY, image_assets, public_input
from .errors import CallError

URL = "https://sage.levanto.ai/decide"


def completion(model, case, timeout, api_model=None):
    if api_model is not None:
        raise CallError("Sage selects its hosted model; --api-model is unsupported", status="config_invalid")
    key = env_value("SAGE_API_KEY")
    if not key:
        raise CallError("SAGE_API_KEY is not set; see .env.example", status="auth_missing")
    data = public_input(case)
    if len(data["questions"]) != 1:
        raise CallError("Sage adapter requires one choice question", status="config_invalid")
    if case.get("assets") and not model.get("vision"):
        raise CallError("This Sage entry does not support images", status="config_invalid")
    images = image_assets(case) if model.get("vision") else []
    if len(images) > 1:
        raise CallError("Sage supports one image per benchmark row", status="config_invalid")
    q = data["questions"][0]
    content = json.dumps(data["state"], ensure_ascii=False)
    if images:
        mime, content_bytes = images[0]
        content = {"kind": "image", "media": f"data:{mime};base64,{base64.b64encode(content_bytes).decode()}",
                   "text": content}
    payload = {"content": content, "reasoning": "auto",
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
        current = meta.get("model") == "levanto-sage-v1.3"
        total = sum(probs.values())
        if current and abs(total - 1) > 0.02:
            raise ValueError("Categorical probabilities do not sum to one")
        answer = ({"choice": result["chosen"], "probabilities": probs} if current else
                  {"label": result["chosen"], "probabilities": {k: v / total for k, v in probs.items()}})
    except (ValueError, KeyError, TypeError, AttributeError):
        raise CallError("Sage returned an invalid Choice response", status="invalid_transport_output")
    usage = meta.get("usage") or {}
    text_tokens = usage.get("input_tokens", usage.get("billed_input_tokens"))
    image_tokens = usage.get("image_tokens", 0)
    # Sage reports text/reasoning input separately from image tokens; both are billed as input.
    total_input = text_tokens + image_tokens if text_tokens is not None and image_tokens is not None else None
    if meta.get("model") != model["model"]:
        raise CallError("Sage returned a different model version than the configured benchmark",
                        status="model_version_mismatch")
    return {"raw": raw, "response": {"answers": {q["id"]: answer}},
            "source": "native" if current else "native-renormalized", "images_sent": len(images),
            "output_text": json.dumps(raw, ensure_ascii=False), "resolved_model": meta.get("model"),
            "http_status": status, "provider_duration_ms": meta.get("latency_ms"),
            "adapter_duration_ms": (time.perf_counter() - started) * 1000,
            "usage": {"input_tokens": total_input, "output_tokens": usage.get("output_tokens"),
                      "image_input_tokens": image_tokens, "cached_input_tokens": None,
                      "reasoning_output_tokens": (meta.get("reasoning") or {}).get("tokens")},
            "cost_usd": None, "cost_basis": "unavailable", "payload": payload}
