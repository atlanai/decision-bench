"""Authenticated self-hosted Kev System One endpoint."""
from urllib.parse import urlsplit

from .config import env_value
from .errors import CallError
from .openai_compat import LOCAL_HOSTS, number


def endpoint():
    base = (env_value("KEV_BASE_URL") or "").strip().rstrip("/")
    parsed = urlsplit(base)
    if (parsed.scheme not in ("https", "http") or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ("", "/v1")):
        raise CallError("KEV_BASE_URL must be an http(s) base URL, optionally ending in /v1, without credentials or query", status="config_invalid")
    if parsed.scheme == "http" and parsed.hostname not in LOCAL_HOSTS:
        raise CallError("A remote Kev endpoint must use HTTPS", status="config_invalid")
    return base + ("" if parsed.path == "/v1" else "/v1") + "/systemone"


def api_key(url):
    key = env_value("KEV_API_KEY")
    if not key and urlsplit(url).hostname not in LOCAL_HOSTS:
        raise CallError("KEV_API_KEY is not set", status="auth_missing")
    return key


def completion(model, case, timeout, api_model=None):
    from .adapters import systemone
    url = endpoint()
    result = systemone(model, case, timeout, api_model, url, api_key(url), "Kev")
    result.update(images_sent=0, provider_duration_ms=number(result["raw"].get("latency_ms")))
    return result
