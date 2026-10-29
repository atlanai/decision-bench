"""Celeris decision models: the native System One payload, with images in Celeris's `x_celeris.images` map."""
from .config import env_value
from .errors import CallError

# Every Celeris decision model is served at this one path; the payload's `model` field selects it.
URL = "https://inference.celeris.ai/celeris-1-decision/v1/systemone"


def api_key():
    key = env_value("CELERIS_API_KEY")
    if not key:
        raise CallError("CELERIS_API_KEY is not set; see .env.example", status="auth_missing")
    return key


def completion(model, case, timeout, api_model=None):
    if api_model is not None:
        # The model comes from its config entry, so a run record always names the model that answered.
        raise CallError("Celeris selects the model from its config entry; --api-model is unsupported",
                        status="config_invalid")
    from .adapters import stored_systemone_payload, systemone, systemone_payload
    payload = systemone_payload(model, case, api_model)
    images = payload.pop("images", None) or []
    if images:
        payload["x_celeris"] = {"images": {f"image_{i}": url for i, url in enumerate(images, 1)}}
    result = systemone(model, case, timeout, api_model, URL, api_key(), "Celeris", payload=payload)
    if images:
        # Run records keep each image's size, not its bytes, as for the other System One adapters.
        stored = stored_systemone_payload({"images": images})["images"]
        result["payload"] = {**payload, "x_celeris": {"images": dict(zip(payload["x_celeris"]["images"], stored))}}
    result["images_sent"] = len(images)
    return result
