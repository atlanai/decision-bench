"""Native OpenRouter Decisions API, preserving categorical probabilities and image evidence."""
from __future__ import annotations

import base64
import json

from .config import env_value
from .corpus import JUDGMENT_POLICY, image_assets, public_input
from .errors import CallError
from .openai_compat import number

URL = "https://openrouter.ai/api/alpha/decisions"


def api_key():
    key = env_value("OPENROUTER_API_KEY")
    if not key:
        raise CallError("OPENROUTER_API_KEY is not set; see .env.example", status="auth_missing")
    return key


def completion(model, case, timeout, api_model=None):
    from .adapters import systemone

    key = api_key()
    data = public_input(case)
    images = image_assets(case) if model.get("vision") else []
    state = data["state"]
    if images:
        state = [json.dumps(state, ensure_ascii=False)] + [
            {"type": "image_url", "image_url": {
                "url": f"data:{mime};base64,{base64.b64encode(content).decode()}"}}
            for mime, content in images]
    payload = {"model": api_model or model["model"], "state": state,
               "questions": {q["id"]: {"type": q["type"],
                   "instructions": JUDGMENT_POLICY + q["instructions"], "criteria": q["options"]}
                   for q in data["questions"]}}
    result = systemone(model, case, timeout, api_model, URL, key, "OpenRouter Decisions", payload=payload)
    cost = number((result["raw"].get("usage") or {}).get("cost"))
    result["output_text"] = json.dumps({"answers": result["response"].get("answers", {})}, ensure_ascii=False)
    result.update(images_sent=len(images), cost_usd=cost,
                  cost_basis="provider_reported" if cost is not None else "unavailable")
    return result
