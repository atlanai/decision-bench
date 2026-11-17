"""A self-hosted Sieve decision model (github.com/sthanika-ai/Sieve), served with `sieve-serve`."""
from urllib.parse import urlsplit

from .config import env_value
from .errors import CallError
from .openai_compat import LOCAL_HOSTS, number


def endpoint():
    base = (env_value("SIEVE_BASE_URL") or "").strip().rstrip("/")
    parsed = urlsplit(base)
    if (parsed.scheme not in ("https", "http") or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ("", "/v1")):
        raise CallError("SIEVE_BASE_URL must be an http(s) base URL, optionally ending in /v1, without credentials or query", status="config_invalid")
    if parsed.scheme == "http" and parsed.hostname not in LOCAL_HOSTS:
        raise CallError("A remote Sieve endpoint must use HTTPS", status="config_invalid")
    return base + ("" if parsed.path == "/v1" else "/v1") + "/decide"


def api_key(url):
    """`sieve-serve` has no authentication. A key is sent only if SIEVE_API_KEY is set (for a proxy in front of it)."""
    return env_value("SIEVE_API_KEY")


def completion(model, case, timeout, api_model=None):
    from .adapters import systemone
    url = endpoint()
    result = systemone(model, case, timeout, api_model, url, api_key(url), "Sieve")
    result.update(images_sent=0, provider_duration_ms=number(result["raw"].get("latency_ms")))
    return result
