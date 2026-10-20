"""Run one model over the active corpus. Resumable: results and attempts are append-only JSONL ledgers.

runs/<run-id>/ is a local, git-ignored working area:
  run.json        frozen configuration, status and execution history
  results.jsonl   one record per finished row (a later record for the same row supersedes an earlier one)
  attempts.jsonl  a start and a finish receipt for every provider call, including retries and failures
  raw/            full provider output per attempt
"""
from __future__ import annotations

import concurrent.futures
import json
import math
import os
import platform
import re
import socket
import ssl
import statistics
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from . import __version__, adapters, config, corpus, kev, openai_compat, openrouter_decisions, sage, tev1
from .corpus import PROMPT_VERSION, canonical, digest, public_input
from .errors import CallError
from .metrics import billable
from .rate_limit import RequestPacer
from .scoring import normalize_answers, score

RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,120}")


def utc():
    return datetime.now(timezone.utc).isoformat()


def runs_dir():
    return corpus.ROOT / "runs"


def git_revision():
    def call(*args):
        try:
            p = subprocess.run(["git", *args], cwd=corpus.ROOT, text=True, capture_output=True)
        except OSError:
            return None
        return p.stdout.strip() if p.returncode == 0 else None
    status = call("status", "--porcelain")
    return {"commit": call("rev-parse", "HEAD"), "dirty": bool(status) if status is not None else None}


def read_jsonl(path, allow_partial=False):
    """Read a ledger. With allow_partial, an unterminated last line (a write in progress) is ignored."""
    path = Path(path)
    if not path.exists():
        return []
    out = []
    lines = path.read_text().splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                if allow_partial and index == len(lines) - 1 and not line.endswith("\n"):
                    break
                raise
    return out


def write_json(path, value):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(openai_compat.redact(value), indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


FIXED_ENDPOINTS = {"typesafe": adapters.TYPESAFE_URL, "djev": adapters.DJEV_URL, "sage": sage.URL, "tev1": tev1.URL,
                   "openrouter-decisions": openrouter_decisions.URL}


def endpoint_url(model):
    """The URL an HTTP provider calls, or None for a CLI provider."""
    provider = model["provider"]
    if provider == "openai-compatible":
        return openai_compat.base_url()
    if provider == "kev":
        return kev.endpoint()
    if provider == "laya":
        return adapters.laya_endpoint()
    return FIXED_ENDPOINTS.get(provider)


def frozen_config(model, cases, all_cases, manifest, api_model=None):
    """Everything that defines the measurement. Resuming requires an identical frozen configuration."""
    cfg = {"suite": manifest.get("suite"), "corpus_version": manifest.get("version"),
           "corpus_sha256": digest(all_cases), "prompt_version": PROMPT_VERSION,
           "model_id": model["id"], "provider": model["provider"], "api_model": api_model or model["model"],
           "request": model.get("request", {}), "vision": bool(model.get("vision")),
           "selected_case_ids": [c["id"] for c in cases]}
    if model["provider"] in ("openai-compatible", "kev", "laya", "openrouter-decisions"):
        cfg["endpoint_id"] = openai_compat.endpoint_id(endpoint_url(model))
    return cfg


def default_run_id(cfg, subset):
    return f"{cfg['model_id']}-{cfg['suite']}-{digest(cfg)[:8]}" + ("-subset" if subset else "")


def select(all_cases, ids=None, limit=None):
    cases = all_cases
    if ids:
        wanted = set(ids.split(","))
        cases = [c for c in cases if c["id"] in wanted]
        if wanted != {c["id"] for c in cases}:
            raise ValueError("Unknown row ids: " + ", ".join(sorted(wanted - {c["id"] for c in cases})))
    if limit:
        cases = cases[:limit]
    if not cases:
        raise ValueError("No rows selected")
    return cases


def add_estimated_cost(target, model):
    """Fill cost from config/models.json pricing when the provider reported none."""
    if target.get("cost_usd") is None:
        estimate = config.estimate_cost(model.get("pricing"), target.get("usage"))
        if estimate is not None:
            target.update(cost_usd=estimate, cost_basis="price_table_estimate",
                          cost_source=model["pricing"]["source_url"])
    return target


def preflight(model):
    """Fail before creating a run when credentials or a CLI are missing, instead of recording an error per row."""
    provider = model["provider"]
    if provider == "openai-compatible":
        openai_compat.api_key(openai_compat.base_url())
    elif provider == "openrouter-decisions":
        from .openrouter_decisions import api_key
        api_key()
    elif provider == "typesafe" and not config.env_value("TYPESAFE_API_KEY"):
        raise CallError("TYPESAFE_API_KEY is not set; see .env.example", status="auth_missing")
    elif provider == "djev" and not config.env_value("DJEV_API_KEY"):
        raise CallError("DJEV_API_KEY is not set; see .env.example", status="auth_missing")
    elif provider == "tev1" and not config.env_value("TOGETHER_API_KEY"):
        raise CallError("TOGETHER_API_KEY is not set", status="auth_missing")
    elif provider == "sage" and not config.env_value("SAGE_API_KEY"):
        raise CallError("SAGE_API_KEY is not set; see .env.example", status="auth_missing")
    elif provider == "kev":
        from .kev import endpoint, api_key
        api_key(endpoint())
    elif provider == "laya":
        adapters.laya_key(adapters.laya_endpoint())
    elif provider in ("claude-cli", "codex-cli"):
        adapters.executable("claude" if provider == "claude-cli" else "codex")


PROBES = 5


def connect_timings(host, port, tls, timeout=5):
    """(DNS, TCP connect, TLS handshake or None) in ms for one fresh connection, opened the way urllib opens one
    for every request: resolve, try each address in turn, then a default-context TLS handshake."""
    started = time.perf_counter()
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    resolved = time.perf_counter()
    for family, kind, proto, _, address in addresses:
        sock = socket.socket(family, kind, proto)
        sock.settimeout(timeout)
        try:
            sock.connect(address)
            break
        except OSError:
            sock.close()
    else:
        raise OSError("No address of the provider host accepted a connection")
    with sock:
        connected = time.perf_counter()
        handshake = None
        if tls:
            with ssl.create_default_context().wrap_socket(sock, server_hostname=host):
                handshake = (time.perf_counter() - connected) * 1000
    return (resolved - started) * 1000, (connected - resolved) * 1000, handshake


def network_baseline(model):
    """Median DNS, TCP connect and TLS handshake times over fresh connections to the host the adapter calls, so
    the tester's network can be told apart from the endpoint's latency. Only the numbers are kept, never the host.
    None for a CLI provider, when a proxy carries the requests (the probe cannot see that path), or when any probe
    fails: a network failure never fails a run."""
    url = endpoint_url(model)
    if url is None:
        return None
    parts = urllib.parse.urlsplit(url)
    if parts.scheme in urllib.request.getproxies() and not urllib.request.proxy_bypass(parts.hostname):
        return None
    tls = parts.scheme == "https"
    print(f"Measuring the network to the provider host ({PROBES} connections)", flush=True)
    try:
        port = parts.port or (443 if tls else 80)
        samples = [connect_timings(parts.hostname, port, tls) for _ in range(PROBES)]
    except (OSError, ValueError):
        return None
    dns, tcp, handshake = zip(*samples)
    return {"probes": PROBES, "dns_ms": statistics.median(dns), "tcp_connect_ms": statistics.median(tcp),
            "tls_handshake_ms": statistics.median(handshake) if tls else None}


def prepare(args):
    """Resolve the model, selection, frozen configuration and run id without making any call."""
    for name in ("jobs", "max_attempts", "timeout"):
        if getattr(args, name) < 1:
            raise ValueError(f"--{name.replace('_', '-')} must be positive")
    for name in ("rpm", "global_rpm"):
        value = getattr(args, name, None)
        if value is not None and (not math.isfinite(value) or value <= 0):
            raise ValueError(f"--{name.replace('_', '-')} must be positive")
    model = config.get_model(args.model)
    all_cases = corpus.load_cases()
    manifest = corpus.load_manifest()
    cases = select(all_cases, args.ids, args.limit)
    preflight(model)
    cfg = frozen_config(model, cases, all_cases, manifest, args.api_model)
    run_id = args.run_id or default_run_id(cfg, len(cases) != len(all_cases))
    if not RUN_ID.fullmatch(run_id):
        raise ValueError("run id must be a simple name, not a path")
    return model, cases, cfg, run_id


def _run(args, model, cases, cfg, run_id, folder):
    raw_dir = folder / "raw"
    raw_dir.mkdir(exist_ok=True)
    run_path = folder / "run.json"
    if run_path.exists():
        meta = json.loads(run_path.read_text())
        if meta["config"] != cfg:
            changed = sorted(k for k in set(meta["config"]) | set(cfg) if meta["config"].get(k) != cfg.get(k))
            raise ValueError(f"Run {run_id} was started with a different configuration ({', '.join(changed)}); "
                             "use a new --run-id")
    else:
        meta = {"id": run_id, "created_at": utc(), "config": cfg, "status": "running", "executions": [],
                "harness_version": __version__,
                "platform": {"os": platform.system(), "python": platform.python_version()},
                "measurement": "Wall clock per row includes retries and client overhead (HTTP round trip or a "
                               "fresh CLI process); it is not pure inference latency."}
    # Presentation fields and prices may change between executions without changing the measurement.
    meta["model"] = config.display(model)
    meta["pricing"] = model.get("pricing")
    previous = {r["case_id"]: r for r in read_jsonl(folder / "results.jsonl")}
    pending = [c for c in cases if c["id"] not in previous or (args.retry_errors and previous[c["id"]]["status"] != "ok")]
    meta.update(status="running", last_started_at=utc())
    meta["executions"].append({"started_at": meta["last_started_at"], "git": git_revision(), "jobs": args.jobs,
                               "timeout_seconds": args.timeout, "max_attempts": args.max_attempts,
                               "retry_errors": args.retry_errors, "pending_rows": len(pending),
                               "rpm": getattr(args, "rpm", None), "global_rpm": getattr(args, "global_rpm", None),
                               "network_baseline": network_baseline(model) if pending else None})
    write_json(run_path, meta)
    lock = threading.Lock()
    done = len(cases) - len(pending)
    pacer = RequestPacer(runs_dir(), model["id"], getattr(args, "rpm", None),
                         getattr(args, "global_rpm", None))
    if pacer.rpm or pacer.global_rpm:
        print(f"Pacing: {pacer.rpm or 'unlimited'} rpm for {model['id']}, "
              f"{pacer.global_rpm or 'unlimited'} rpm across models", flush=True)

    def append(name, value):
        with lock:
            with (folder / name).open("a") as f:
                f.write(canonical(openai_compat.redact(value)) + "\n")
                f.flush()

    def one(case):
        nonlocal done
        began = time.perf_counter()
        rate_wait = 0.0
        retry_rate_wait = 0.0
        record = {"run_id": run_id, "case_id": case["id"], "started_at": utc(),
                  "input_hash": digest(public_input(case)), "answers": {}, "attempts": [], "usage": {},
                  "cost_usd": None, "cost_basis": "unavailable", "resolved_model": None, "output_text": None}
        for attempt in range(1, args.max_attempts + 1):
            waited = pacer.wait()
            rate_wait += waited
            if attempt == 1:
                # Queue time is pacing, not model latency.
                began = time.perf_counter()
                record["started_at"] = utc()
            else:
                retry_rate_wait += waited
            aid = f"{case['id']}-{time.time_ns()}-{attempt}"
            a = {"attempt_id": aid, "case_id": case["id"], "number": attempt, "started_at": utc()}
            append("attempts.jsonl", {**a, "event": "started"})
            t = time.perf_counter()
            result, retry = None, False
            try:
                result = adapters.call(model, case, args.timeout, args.api_model)
                add_estimated_cost(result, model)
                # Keep paid usage even if the output then fails its contract.
                a.update(usage=result["usage"], cost_usd=result["cost_usd"], cost_basis=result["cost_basis"],
                         resolved_model=result.get("resolved_model"),
                         provider_duration_ms=result.get("provider_duration_ms"))
                record.update({k: result.get(k) for k in ("usage", "cost_usd", "cost_basis", "resolved_model",
                               "output_text", "provider_duration_ms", "finish_reason", "output_validation_error",
                               "output_wrapper_normalization", "command", "images_sent") if k in result})
                record["raw_response"] = result["response"]
                record["inference_input"] = result["payload"]
                record["answers"] = normalize_answers(result["response"], case, result["source"])
                record["status"] = a["status"] = "ok"
                record.pop("error", None)
            except CallError as e:
                add_estimated_cost(e.metadata, model)
                a.update(e.metadata)
                record.update(e.metadata)
                a.update(status=str(e.status or "call_error"), error=str(e))
                record.update(status=a["status"], error=str(e))
                if e.raw is not None:
                    write_json(raw_dir / f"{aid}.json", e.raw)
                retry = e.retryable
            except (ValueError, KeyError, TypeError) as e:
                a.update(status="invalid_output", error=str(e))
                record.update(status="invalid_output", error=str(e))
            except Exception as e:  # keep the run going; the failure is recorded
                a.update(status="runner_error", error=f"{type(e).__name__}: {e}")
                record.update(status="runner_error", error=a["error"])
            if result:
                write_json(raw_dir / f"{aid}.json", result["raw"])
            a.update(ended_at=utc(), duration_ms=(time.perf_counter() - t) * 1000, raw_path=f"raw/{aid}.json",
                     event="finished")
            record["attempts"].append(a)
            append("attempts.jsonl", a)
            if record["status"] == "ok" or not retry or attempt == args.max_attempts:
                break
            time.sleep(min(2 ** attempt, 8))
        record["scores"] = score(case, record["answers"])
        record["ended_at"] = utc()
        record["duration_ms"] = max(0.0, time.perf_counter() - began - retry_rate_wait) * 1000
        record["rate_wait_ms"] = rate_wait * 1000
        known = [x["cost_usd"] for x in record["attempts"] if x.get("cost_usd") is not None]
        record["known_attempt_cost_usd"] = sum(known) if known else None
        charged = billable(record["attempts"])
        record["cost_coverage"] = len(known) / len(charged) if charged else 1
        append("results.jsonl", record)
        with lock:
            done += 1
            ok = "correct" if record["scores"][0]["correct"] else "wrong"
            print(f"[{done}/{len(cases)}] {case['id']}: {record['status']} {ok} {record['duration_ms'] / 1000:.2f}s",
                  flush=True)
        return record

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        list(pool.map(one, pending))
    latest = {r["case_id"]: r for r in read_jsonl(folder / "results.jsonl")}
    selected = [latest[c["id"]] for c in cases if c["id"] in latest]
    errors = sum(r["status"] != "ok" for r in selected)
    meta.update(status="completed" if errors == 0 else "completed_with_errors", completed_at=utc(),
                cases_completed=len(selected), cases_with_errors=errors,
                question_correct=sum(s["correct"] for r in selected for s in r["scores"]),
                question_total=sum(len(r["scores"]) for r in selected))
    write_json(run_path, meta)
    print(json.dumps({"run": run_id, "status": meta["status"], "rows": len(selected), "errors": errors,
                      "correct": meta["question_correct"], "total": meta["question_total"]}), flush=True)
    return meta


def run(args):
    """One writer per run id. Different runs may execute concurrently."""
    import fcntl  # POSIX only; imported here so reporting and validation work everywhere
    model, cases, cfg, run_id = prepare(args)
    folder = runs_dir() / run_id
    folder.mkdir(parents=True, exist_ok=True)
    print(f"Run {run_id}: {model['id']} ({model['provider']}), {len(cases)} rows", flush=True)
    with (folder / ".run.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"Run {run_id} already has a live writer") from exc
        lock.write(str(os.getpid()))
        lock.flush()
        return _run(args, model, cases, cfg, run_id, folder)
