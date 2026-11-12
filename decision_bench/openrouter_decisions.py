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


def fit_image(mime, content, min_side, max_side):
    """Rescale an image whose shorter side is under min_side or longer side is over max_side, keeping its aspect
    ratio and format. Returns (mime, bytes, resized). Pillow is the one runtime dependency outside the standard
    library, and it is imported only for a model whose provider rejects some corpus images."""
    import io

    from PIL import Image

    with Image.open(io.BytesIO(content)) as image:
        width, height = image.size
        scale = max(1, min_side / min(width, height))
        scale = min(scale, max_side / max(width, height))
        if scale == 1:
            return mime, content, False
        size = (round(width * scale), round(height * scale))
        out = io.BytesIO()
        image.resize(size, Image.Resampling.LANCZOS).save(out, image.format, quality=95)
    return mime, out.getvalue(), True


def completion(model, case, timeout, api_model=None):
    from .adapters import systemone

    key = api_key()
    data = public_input(case)
    images = image_assets(case) if model.get("vision") else []
    request = model.get("request", {})
    resized = 0
    if images and ("image_min_side" in request or "image_max_side" in request):
        fitted = [fit_image(mime, content, request.get("image_min_side", 1), request.get("image_max_side", 10**6))
                  for mime, content in images]
        images = [(mime, content) for mime, content, _ in fitted]
        resized = sum(changed for _, _, changed in fitted)
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
    result.update(images_sent=len(images), images_resized=resized, cost_usd=cost,
                  cost_basis="provider_reported" if cost is not None else "unavailable")
    return result
