"""Provider adapters. Each returns the same result shape; see `call`."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import openai_compat
from .config import env_value
from .corpus import JUDGMENT_POLICY, SYSTEM, prompt, public_input, response_schema
from .errors import CallError

TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"
# Credentials the harness itself uses are never passed to a CLI child process.
HARNESS_SECRETS = ["DECISION_BENCH_API_KEY", "DECISION_BENCH_BASE_URL", "TYPESAFE_API_KEY",
                   "ANTHROPIC_MODEL", "CLAUDE_CODE_SUBAGENT_MODEL", "CLAUDECODE"]


def call(model, case, timeout, api_model=None):
    """Run one row. Returns a dict with: response (parsed JSON), source, output_text, usage, cost_usd,
    cost_basis, resolved_model, provider_duration_ms, adapter_duration_ms, payload (what was sent), raw."""
    provider = model["provider"]
    if provider == "openai-compatible":
        return openai_compat.completion(model, case, timeout, api_model)
    if provider == "typesafe":
        return typesafe(model, case, timeout, api_model)
    if provider in ("claude-cli", "codex-cli"):
        return cli(model, case, timeout, api_model)
    raise ValueError(f"Unknown provider {provider}")


def typesafe(model, case, timeout, api_model=None):
    key = env_value("TYPESAFE_API_KEY")
    if not key:
        raise CallError("TYPESAFE_API_KEY is not set; see .env.example", status="auth_missing")
    data = public_input(case)
    questions = {q["id"]: {"type": q["type"], "instructions": JUDGMENT_POLICY + q["instructions"],
                           "criteria": q["options"]} for q in data["questions"]}
    payload = {"model": api_model or model["model"], "state": data["state"], "questions": questions}
    req = urllib.request.Request(TYPESAFE_URL, data=json.dumps(payload).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                                          "User-Agent": "DecisionBench (classification evaluation)"})
    started = time.perf_counter()
    try:
        with urllib.request.build_opener(openai_compat.NoRedirect).open(req, timeout=timeout) as response:
            text = response.read().decode()
            status = response.status
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace").replace(key, "[REDACTED]")
        raise CallError(f"HTTP {e.code}: {body[:500]}", raw={"status": e.code, "body": body},
                        retryable=e.code in openai_compat.RETRYABLE, status=e.code) from e
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        raise CallError(str(e), retryable=True, status="transport_error") from e
    try:
        raw = json.loads(text)
    except ValueError:
        raise CallError("TypeSafe returned non-JSON content", raw={"body": text[:8000]}, status="invalid_transport_output")
    usage = raw.get("usage", {})
    return {"raw": raw, "response": raw, "source": "native", "output_text": text,
            "resolved_model": raw.get("model"), "http_status": status, "provider_duration_ms": None,
            "adapter_duration_ms": (time.perf_counter() - started) * 1000,
            "usage": {"input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
                      "cached_input_tokens": usage.get("cached_input_tokens"), "reasoning_output_tokens": None},
            "cost_usd": None, "cost_basis": "unavailable", "payload": payload}


def claude_usage(event):
    usage = event.get("usage") or {}
    ins = usage.get("input_tokens")
    cached = usage.get("cache_read_input_tokens", 0)
    creation = usage.get("cache_creation_input_tokens", 0)
    return {"input_tokens": ins + cached + creation if ins is not None else None, "cached_input_tokens": cached,
            "cache_creation_input_tokens": creation, "output_tokens": usage.get("output_tokens"),
            "reasoning_output_tokens": (usage.get("output_tokens_details") or {}).get("thinking_tokens")}


def claude_failure_metadata(event):
    models = list((event.get("modelUsage") or {}).keys())
    cost = event.get("total_cost_usd")
    return {"usage": claude_usage(event), "cost_usd": cost,
            "cost_basis": "provider_reported" if cost is not None else "unavailable",
            "provider_duration_ms": event.get("duration_api_ms"),
            "resolved_model": models[0] if len(models) == 1 else models or None}


def executable(name):
    path = shutil.which(name)
    if not path:
        raise CallError(f"`{name}` is not on PATH; install and sign in to it to use this provider",
                        status="config_missing")
    return path


def cli(model, case, timeout, api_model=None):
    """Claude Code or Codex CLI, closed book: an empty temporary working directory, no tools, no user config."""
    provider, name = model["provider"], api_model or model["model"]
    effort = model.get("request", {}).get("reasoning_effort")
    with tempfile.TemporaryDirectory(prefix="decision-bench-") as tmp:
        work = Path(tmp)
        schema = response_schema(case)
        schema_path = work / "response.schema.json"
        schema_path.write_text(json.dumps(schema))
        env = {k: v for k, v in os.environ.items() if k not in HARNESS_SECRETS}
        if provider == "codex-cli":
            cmd = [executable("codex"), "exec", "--ignore-user-config", "--ephemeral", "--skip-git-repo-check",
                   "--sandbox", "read-only", "--model", name, "--json", "--color", "never",
                   "--output-schema", str(schema_path), "-c", "features.shell_tool=false",
                   "-c", "features.apply_patch_freeform=false"]
            if effort:
                cmd += ["-c", f'model_reasoning_effort="{effort}"']
            cmd += ["-"]
            stdin = prompt(case)
        else:
            cmd = [executable("claude"), "--print", "--model", name, "--output-format", "json", "--tools", "",
                   "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', "--safe-mode",
                   "--no-session-persistence", "--no-chrome", "--disable-slash-commands",
                   "--system-prompt", SYSTEM, "--json-schema", json.dumps(schema)]
            if effort:
                cmd += ["--effort", effort]
            stdin = json.dumps(public_input(case), ensure_ascii=False)
        started = time.perf_counter()
        try:
            proc = subprocess.run(cmd, input=stdin, text=True, capture_output=True, cwd=work, env=env, timeout=timeout)
        except subprocess.TimeoutExpired as e:
            raise CallError(f"CLI timed out after {timeout}s", raw={"stdout": str(e.stdout or ""),
                            "stderr": str(e.stderr or "")}, status="timeout") from e
        duration = (time.perf_counter() - started) * 1000
        raw = {"stdout": proc.stdout, "stderr": proc.stderr, "returncode": proc.returncode}
        recorded_cmd = [x.replace(str(work), "<isolated-workdir>") for x in cmd]
        recorded_cmd[0] = Path(recorded_cmd[0]).name  # never record a local install path
        if proc.returncode:
            if provider == "claude-cli":
                # Claude emits structured error JSON even when the process exits 1.
                try:
                    failure = json.loads(proc.stdout)
                except (ValueError, TypeError):
                    failure = None
                if isinstance(failure, dict) and failure.get("is_error"):
                    message = str(failure.get("result", "Claude request failed"))
                    state = "auth_missing" if "not logged in" in message.lower() else "model_error"
                    raise CallError(message, raw=raw, status=state, metadata=claude_failure_metadata(failure))
            raise CallError(f"CLI exited {proc.returncode}: {proc.stderr[-800:] or proc.stdout[-800:]}",
                            raw=raw, status="cli_error")
        if provider == "codex-cli":
            events = []
            for line in proc.stdout.splitlines():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
            raw["events"] = events
            tool_items = [e for e in events if e.get("type") == "item.completed"
                          and e.get("item", {}).get("type") not in ("agent_message", "reasoning")]
            if tool_items:
                raise CallError("Tool use invalidates this closed-book run", raw=raw, status="protocol_violation")
            completions = [e for e in events if e.get("type") == "turn.completed"]
            messages = [e["item"]["text"] for e in events if e.get("type") == "item.completed"
                        and e.get("item", {}).get("type") == "agent_message"]
            if not completions or not messages:
                raise CallError("No completed Codex turn and final response", raw=raw, status="incomplete")
            usage = completions[-1].get("usage", {})
            text = messages[-1]
            result = json.loads(text)
            normalized = {"input_tokens": usage.get("input_tokens"), "cached_input_tokens": usage.get("cached_input_tokens"),
                          "output_tokens": usage.get("output_tokens"),
                          "reasoning_output_tokens": usage.get("reasoning_output_tokens")}
            # Codex reports only the configured model; cost comes from config/models.json pricing.
            cost, basis, resolved, api_ms = None, "unavailable", None, None
        else:
            event = json.loads(proc.stdout)
            raw["result_event"] = event
            if event.get("is_error"):
                raise CallError(str(event.get("result", "Claude error")), raw=raw, status="model_error",
                                metadata=claude_failure_metadata(event))
            result = event.get("structured_output")
            text = json.dumps(result, ensure_ascii=False) if result is not None else str(event.get("result", ""))
            if result is None:
                body = text.strip()
                if body.startswith("```"):
                    body = "\n".join(body.splitlines()[1:-1])
                try:
                    result = json.loads(body)
                except ValueError:
                    result = {"answers": {}}
            normalized = claude_usage(event)
            cost = event.get("total_cost_usd")
            basis = "provider_reported" if cost is not None else "unavailable"
            models = list(event.get("modelUsage", {}))
            resolved = models[0] if len(models) == 1 else models or name
            api_ms = event.get("duration_api_ms")
        return {"raw": raw, "response": result, "source": "verbalized", "output_text": text,
                "resolved_model": resolved, "usage": normalized, "adapter_duration_ms": duration,
                "provider_duration_ms": api_ms, "cost_usd": cost, "cost_basis": basis,
                "command": recorded_cmd, "payload": public_input(case)}
