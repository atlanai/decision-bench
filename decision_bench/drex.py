"""Nace Drex native System One endpoint."""
from urllib.parse import urlsplit

from .config import env_value
from .errors import CallError
from .openai_compat import LOCAL_HOSTS


def endpoint():
    base = (env_value("DREX_BASE_URL") or "").strip().rstrip("/")
    if not base:
        raise CallError("DREX_BASE_URL is not set; see .env.example", status="config_missing")
    parsed = urlsplit(base)
    if (parsed.scheme not in ("https", "http") or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path != "/v1"):
        raise CallError("DREX_BASE_URL must be an http(s) base URL ending in /v1, without credentials or query",
                        status="config_invalid")
    if parsed.scheme == "http" and parsed.hostname not in LOCAL_HOSTS:
        raise CallError("A remote Drex endpoint must use HTTPS", status="config_invalid")
    return base + "/systemone"


def api_key():
    key = env_value("NACE_API_KEY")
    if not key:
        raise CallError("NACE_API_KEY is not set; see .env.example", status="auth_missing")
    return key


def completion(model, case, timeout, api_model=None):
    from .adapters import systemone
    return systemone(model, case, timeout, api_model, endpoint(), api_key(), "Drex")
