"""Bearer key and model checks shared by the Modal System One servers (serve_prism.py, serve_amos.py, serve_sieve.py)."""
import hmac
import os

MIN_KEY_LENGTH = 24


def require_key(name):
    """The bearer key in environment variable `name`; stops the deploy when it is shorter than MIN_KEY_LENGTH."""
    key = os.environ.get(name, "")
    if len(key) < MIN_KEY_LENGTH:
        raise SystemExit(f"{name} must be at least {MIN_KEY_LENGTH} characters, for example from `openssl rand -hex 24`")
    return key


def refusal(authorization, body, key, model):
    """(status, message) for a request the server must refuse, or None when it may answer."""
    if not hmac.compare_digest(authorization.encode(), f"Bearer {key}".encode()):
        return 401, "invalid bearer key"
    if body.get("model") != model:
        return 422, f"this endpoint serves {model}"
    return None
