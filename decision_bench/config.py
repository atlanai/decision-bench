"""config/models.json and environment settings. No hostnames or keys live in committed config."""
from __future__ import annotations

import json
import math
import os
import re

from . import corpus

PROVIDERS = {"openai-compatible", "typesafe", "laya", "claude-cli", "codex-cli"}
MODEL_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
REQUEST_KEYS = {
    "openai-compatible": {"response_format", "token_limit_field", "max_output_tokens", "reasoning_effort",
                          "temperature", "json_wrapper_policy"},
    "typesafe": set(),
    "laya": set(),
    "claude-cli": {"reasoning_effort"},
    "codex-cli": {"reasoning_effort"},
}
MODEL_KEYS = {"id", "label", "short_label", "vendor", "provider", "model", "color", "request", "pricing", "notes",
              "vision"}
PRICING_KEYS = {"input_per_mtok", "cached_input_per_mtok", "output_per_mtok", "source_url", "as_of", "note"}


class ConfigError(ValueError):
    pass


def env_value(name):
    """Read a setting from the process environment, then from the ignored local .env file."""
    if os.environ.get(name):
        return os.environ[name]
    path = corpus.ROOT / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == name and not key.strip().startswith("#"):
                return value.strip().strip("\"'") or None
    return None


def _check_model(m):
    where = f"config/models.json model {m.get('id')!r}"
    unknown = set(m) - MODEL_KEYS
    if unknown:
        raise ConfigError(f"{where}: unknown keys {sorted(unknown)}")
    if not isinstance(m.get("id"), str) or not MODEL_ID.fullmatch(m["id"]):
        raise ConfigError(f"{where}: id must match {MODEL_ID.pattern}")
    for key in ("label", "vendor", "model"):
        if not isinstance(m.get(key), str) or not m[key].strip():
            raise ConfigError(f"{where}: {key} is required")
    if m.get("provider") not in PROVIDERS:
        raise ConfigError(f"{where}: provider must be one of {sorted(PROVIDERS)}")
    if "://" in m["model"]:
        raise ConfigError(f"{where}: model is a model name, not a URL")
    request = m.get("request", {})
    if set(request) - REQUEST_KEYS[m["provider"]]:
        raise ConfigError(f"{where}: request options {sorted(set(request) - REQUEST_KEYS[m['provider']])} "
                          f"are not used by provider {m['provider']}")
    if request.get("response_format", "json_schema") not in ("json_schema", "json_object", "prompt"):
        raise ConfigError(f"{where}: response_format must be json_schema, json_object or prompt")
    if request.get("token_limit_field", "max_tokens") not in ("max_tokens", "max_completion_tokens"):
        raise ConfigError(f"{where}: token_limit_field must be max_tokens or max_completion_tokens")
    if request.get("json_wrapper_policy", "allow_single_code_fence") not in ("allow_single_code_fence", "strict"):
        raise ConfigError(f"{where}: json_wrapper_policy must be allow_single_code_fence or strict")
    if "vision" in m and not isinstance(m["vision"], bool):
        raise ConfigError(f"{where}: vision must be true or false")
    pricing = m.get("pricing")
    if pricing is not None:
        if set(pricing) - PRICING_KEYS:
            raise ConfigError(f"{where}: unknown pricing keys {sorted(set(pricing) - PRICING_KEYS)}")
        for key in ("input_per_mtok", "output_per_mtok"):
            value = pricing.get(key)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0 or not math.isfinite(value):
                raise ConfigError(f"{where}: pricing.{key} must be a non-negative number")
        if not str(pricing.get("source_url", "")).startswith("https://"):
            raise ConfigError(f"{where}: pricing.source_url must be an https URL")


def load_models():
    data = json.loads((corpus.ROOT / "config/models.json").read_text())
    models = data.get("models", [])
    ids = [m.get("id") for m in models]
    if len(ids) != len(set(ids)):
        raise ConfigError("config/models.json: duplicate model ids")
    for m in models:
        _check_model(m)
    return models


def get_model(model_id):
    for m in load_models():
        if m["id"] == model_id:
            return m
    raise ConfigError(f"Unknown model id {model_id!r}; see config/models.json or run `python3 -m decision_bench models`")


def display(m):
    """Presentation fields only. Changing these never invalidates a run."""
    return {"id": m["id"], "label": m["label"], "short_label": m.get("short_label") or m["label"],
            "vendor": m["vendor"], "provider": m["provider"], "color": m.get("color"),
            "vision": bool(m.get("vision"))}


def estimate_cost(pricing, usage):
    """Price-table estimate in USD, or None when a price or token count is unknown."""
    if not pricing or not usage:
        return None
    ins, out = usage.get("input_tokens"), usage.get("output_tokens")
    if ins is None or out is None:
        return None
    cached = min(usage.get("cached_input_tokens") or 0, ins)
    cached_rate = pricing.get("cached_input_per_mtok", pricing["input_per_mtok"])
    return ((ins - cached) * pricing["input_per_mtok"] + cached * cached_rate
            + out * pricing["output_per_mtok"]) / 1_000_000
