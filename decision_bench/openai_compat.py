"""Any OpenAI-compatible chat completions endpoint (OpenAI, OpenRouter, LiteLLM, vLLM, ...). Standard library only.

The endpoint comes from DECISION_BENCH_BASE_URL and the key from DECISION_BENCH_API_KEY. Neither is ever written
to a run record: runs keep only an opaque endpoint id (a hash of the URL)."""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from .config import env_value
import base64

from .corpus import SYSTEM, image_assets, response_schema, user_message
from .errors import CallError

BASE_ENV = "DECISION_BENCH_BASE_URL"
KEY_ENV = "DECISION_BENCH_API_KEY"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
RETRYABLE = {408, 409, 425, 429, 500, 502, 503, 504}
# Only headers that carry cost or timing are kept. Routing, deployment and version headers describe the
# operator's infrastructure and are dropped.
KEPT_HEADERS = ("x-litellm-response-cost", "x-litellm-response-duration-ms", "x-litellm-attempted-retries",
                "x-litellm-attempted-fallbacks")
SENSITIVE_KEYS = {"api_key", "authorization", "access_token", "refresh_token", "x-api-key", "cookie", "set-cookie"}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the bearer credential to a redirect destination.
        return None


def base_url():
    """The configured base URL (the one /chat/completions is appended to), after safety checks."""
    base = (env_value(BASE_ENV) or "").strip().rstrip("/")
    if not base:
        raise CallError(f"{BASE_ENV} is not set; see .env.example", status="config_missing")
    parsed = urllib.parse.urlsplit(base)
    if (parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment):
        raise CallError(f"{BASE_ENV} must be a plain http(s) URL with no credentials, query or fragment",
                        status="config_invalid")
    if parsed.scheme == "http" and parsed.hostname not in LOCAL_HOSTS:
        raise CallError(f"A remote endpoint must use HTTPS ({BASE_ENV})", status="config_invalid")
    return base


def is_local(base):
    return urllib.parse.urlsplit(base).hostname in LOCAL_HOSTS


def api_key(base):
    key = env_value(KEY_ENV)
    if not key and not is_local(base):
        raise CallError(f"{KEY_ENV} is not set; see .env.example", status="auth_missing")
    return key


def endpoint_id(base):
    """An opaque, stable identifier for the endpoint. The URL itself is never recorded."""
    return "endpoint-" + hashlib.sha256(base.rstrip("/").encode()).hexdigest()[:12]


def redact(value):
    """Remove the key, the endpoint URL and its hostname from anything that may be written to disk."""
    secrets = [s for s in [env_value(KEY_ENV)] if s]
    try:
        base = base_url()
    except CallError:
        base = None
    hosts = []
    if base:
        hosts = [base]
        host = urllib.parse.urlsplit(base).hostname
        if host and host not in LOCAL_HOSTS:
            hosts.append(host)

    def clean(v):
        if isinstance(v, str):
            for s in secrets:
                v = v.replace(s, "[REDACTED]")
            for h in hosts:
                v = v.replace(h, "[ENDPOINT]")
            return v
        if isinstance(v, list):
            return [clean(x) for x in v]
        if isinstance(v, dict):
            return {k: "[REDACTED]" if str(k).lower() in SENSITIVE_KEYS else clean(x) for k, x in v.items()}
        return v
    return clean(value)


def request(url, payload=None, timeout=90):
    base = base_url()
    key = api_key(base)
    approved, target = urllib.parse.urlsplit(base), urllib.parse.urlsplit(url)
    if (target.scheme, target.netloc) != (approved.scheme, approved.netloc):
        raise CallError("Refusing to send the API key to a different origin", status="config_invalid")
    headers = {"Content-Type": "application/json", "User-Agent": "DecisionBench (classification evaluation)"}
    if key:
        headers["Authorization"] = "Bearer " + key
    data = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers)
    started = time.perf_counter()
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=timeout) as response:
            body = response.read().decode()
            response_headers = {k.lower(): v for k, v in response.headers.items()}
            status = response.status
    except urllib.error.HTTPError as exc:
        try:
            body = redact(exc.read().decode(errors="replace"))
        finally:
            exc.close()
        raise CallError(f"HTTP {exc.code}: {body[:1200]}", raw={"http_status": exc.code, "body": body},
                        status=exc.code, retryable=exc.code in RETRYABLE) from exc
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        raise CallError(redact(str(exc)), status="transport_error", retryable=True) from exc
    elapsed = (time.perf_counter() - started) * 1000
    try:
        raw = json.loads(body)
    except ValueError:
        raise CallError("Endpoint returned non-JSON content", raw={"body": redact(body[:8000])},
                        status="invalid_transport_output", retryable=True)
    return redact(raw), redact(response_headers), status, elapsed


def list_models(timeout=30):
    """Model ids the endpoint lists at GET /models. Printed only; nothing is saved."""
    raw, _, _, _ = request(base_url() + "/models", timeout=timeout)
    rows = raw.get("data", []) if isinstance(raw, dict) else raw
    return sorted(r["id"] for r in rows if isinstance(r, dict) and isinstance(r.get("id"), str))


def number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return n if math.isfinite(n) and n >= 0 else None


def payload_for(case, api_model, options, vision=False):
    """Chat payload. A vision model gets the row's images as data URIs after the text; text-only models get the
    text rendering that every image row carries in its state."""
    schema = response_schema(case)
    content = user_message(case)
    images = image_assets(case) if vision else []
    if images:
        content = [{"type": "text", "text": content}] + [
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(data).decode()}"}}
            for mime, data in images]
    payload = {"model": api_model, "stream": False,
               "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}]}
    mode = options.get("response_format", "json_schema")
    if mode == "json_schema":
        payload["response_format"] = {"type": "json_schema",
                                      "json_schema": {"name": "decision_bench", "strict": True, "schema": schema}}
    elif mode == "json_object":
        payload["response_format"] = {"type": "json_object"}
    field = options.get("token_limit_field", "max_tokens")
    payload[field] = options.get("max_output_tokens", 4096)
    if options.get("reasoning_effort") is not None:
        payload["reasoning_effort"] = options["reasoning_effort"]
    if options.get("temperature") is not None:
        payload["temperature"] = options["temperature"]
    return payload


def stored_payload(payload):
    """The payload as kept in run records: image bytes are replaced by their size, so records stay small."""
    out = json.loads(json.dumps(payload))
    for m in out.get("messages", []):
        if isinstance(m.get("content"), list):
            for part in m["content"]:
                if part.get("type") == "image_url":
                    url = part["image_url"]["url"]
                    part["image_url"] = {"url": f"[{url.split(';', 1)[0].removeprefix('data:')} image, {len(url)} characters of base64 omitted]"}
    return out


def parse_output(text, options):
    """Strict JSON, optionally inside one complete ```json fence. No prose extraction or label repair."""
    parsed_text, wrapper = text.strip(), "none"
    fenced = re.fullmatch(r"```(?:json)?\s*\n([\s\S]*?)\n```", parsed_text, re.IGNORECASE)
    if fenced and options.get("json_wrapper_policy", "allow_single_code_fence") == "allow_single_code_fence":
        parsed_text, wrapper = fenced.group(1), "single_markdown_code_fence"
    try:
        result = json.loads(parsed_text)
        if not isinstance(result, dict):
            raise ValueError("response JSON is not an object")
        return result, wrapper, None
    except ValueError as exc:
        return {"answers": {}}, wrapper, "Invalid response JSON: " + str(exc)


def completion(model, case, timeout, api_model=None):
    options = model.get("request", {})
    base = base_url()
    payload = payload_for(case, api_model or model["model"], options, vision=bool(model.get("vision")))
    images_sent = sum(1 for part in payload["messages"][1]["content"] if isinstance(part, dict)
                      and part.get("type") == "image_url") if isinstance(payload["messages"][1]["content"], list) else 0
    raw, headers, status, elapsed = request(base + "/chat/completions", payload, timeout)
    usage = raw.get("usage") or {}
    prompt_details = usage.get("prompt_tokens_details") or {}
    completion_details = usage.get("completion_tokens_details") or {}
    # Cost reported by the endpoint itself: LiteLLM's response header or OpenRouter's usage.cost.
    cost = number(headers.get("x-litellm-response-cost"))
    if cost is None:
        cost = number(usage.get("cost"))
    choices = raw.get("choices") or []
    choice = choices[0] if choices else {}
    message = choice.get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        content = "".join(x.get("text", "") for x in content if isinstance(x, dict))
    text = content if isinstance(content, str) else ""
    result, wrapper, error = parse_output(text, options)
    if message.get("tool_calls") or message.get("function_call"):
        result, error = {"answers": {}}, "Unexpected tool call in a closed-book classification response"
    if choice.get("finish_reason") == "length":
        result, error = {"answers": {}}, "Output token limit reached"
    kept = {k: v for k, v in headers.items() if k in KEPT_HEADERS}
    return {"raw": {"response": raw, "headers": kept}, "response": result, "source": "verbalized",
            "output_text": text, "resolved_model": raw.get("model"), "http_status": status,
            "provider_duration_ms": number(headers.get("x-litellm-response-duration-ms")),
            "adapter_duration_ms": elapsed,
            "usage": {"input_tokens": usage.get("prompt_tokens"), "output_tokens": usage.get("completion_tokens"),
                      "cached_input_tokens": prompt_details.get("cached_tokens"),
                      "reasoning_output_tokens": completion_details.get("reasoning_tokens"),
                      "cache_creation_input_tokens": prompt_details.get("cache_creation_tokens")},
            "cost_usd": cost, "cost_basis": "provider_reported" if cost is not None else "unavailable",
            "cost_source": "endpoint response" if cost is not None else None,
            "payload": stored_payload(payload), "images_sent": images_sent, "output_wrapper_normalization": wrapper,
            "finish_reason": choice.get("finish_reason"), "output_validation_error": error,
            "endpoint_id": endpoint_id(base)}
