"""Self-hosted Bielik One, using the shared native System One transport and scoring."""
from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

from . import config
from .errors import CallError


def endpoint():
    value = config.env_value("BIELIK_ONE_BASE_URL")
    if not value:
        raise CallError("BIELIK_ONE_BASE_URL is not set", status="config_missing")
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        _ = parsed.port  # validate any explicit port
    except ValueError:
        raise CallError("Invalid BIELIK_ONE_BASE_URL", status="config_invalid") from None
    try:
        loopback = host == "localhost" or ipaddress.ip_address(host or "").is_loopback
    except ValueError:
        loopback = host == "localhost"
    if (not host or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment or parsed.path.rstrip("/") not in ("", "/v1")
            or parsed.scheme not in ("http", "https")
            or (parsed.scheme == "http" and not loopback)):
        raise CallError("BIELIK_ONE_BASE_URL must use HTTPS or loopback HTTP, without credentials or query", status="config_invalid")
    return value.rstrip("/") + ("/systemone" if parsed.path.rstrip("/") else "/v1/systemone")


def call(model, case, timeout, api_model=None):
    from .adapters import systemone

    if api_model is not None and api_model != model["model"]:
        raise CallError("Bielik One model overrides are not supported; configure a separate model entry", status="config_invalid")
    if model.get("vision"):
        raise CallError("The Bielik One adapter is text-only", status="config_invalid")
    return systemone(model, case, timeout, api_model, endpoint(),
                     config.env_value("BIELIK_ONE_API_KEY"), "Bielik One", extra=model.get("request"))
