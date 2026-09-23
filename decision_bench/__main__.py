"""Command line: python3 -m decision_bench <command>. Run with --help for details."""
import argparse
import json
import sys

from .config import ConfigError
from .errors import CallError


def cmd_validate(args):
    from . import config, corpus, results
    cases, manifest = corpus.load_cases(), corpus.load_manifest()
    corpus.validate_against_manifest(cases, manifest)
    models = config.load_models()
    problems = results.check_published(cases, manifest)
    out = {"suite": manifest.get("suite"), "version": manifest.get("version"), "sha256": manifest["sha256"],
           "rows": len(cases), "tasks": len({c["task"] for c in cases}),
           "categories": len({c["category"] for c in cases}), "models_configured": len(models),
           "published_results": len(results.load_published(manifest.get("suite"))), "problems": problems}
    print(json.dumps(out, indent=2))
    return 1 if problems else 0


def cmd_models(args):
    from . import config, openai_compat
    if args.remote:
        # Print-only: list what the configured endpoint serves. Nothing about the endpoint is saved.
        for ident in openai_compat.list_models():
            print(ident)
        return 0
    for m in config.load_models():
        print(f"{m['id']:<26} {m['provider']:<18} {m['model']:<32} {m['label']}")
    return 0


def cmd_run(args):
    from .runner import run
    ids = [m for m in args.model.split(",") if m]
    if len(ids) > 1 and args.run_id:
        raise ValueError("--run-id can only be used with a single --model")
    for ident in ids:
        args.model = ident
        run(args)
    return 0


def cmd_publish(args):
    from .results import publish
    print(json.dumps(publish(args.run_id, force=args.force), indent=2))
    return 0


def cmd_leaderboard(args):
    from . import corpus
    from .results import write_leaderboard
    board = write_leaderboard(corpus.load_manifest()["suite"])
    print(json.dumps({"models": len(board["models"])}))
    return 0


def cmd_report(args):
    from .report import build
    build(include_runs=args.include_runs)
    return 0


def cmd_serve(args):
    import functools
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    from .corpus import ROOT
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(ROOT / "site"))
    if not (ROOT / "site" / "index.html").exists():
        print("The viewer is not built yet: run `npm ci --prefix web && npm run build --prefix web`.", flush=True)
    print(f"Decision Bench: http://127.0.0.1:{args.port} (serving site/ only)", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), handler).serve_forever()


def parser():
    p = argparse.ArgumentParser(prog="decision_bench", description="Decision Bench: run, publish and view results.")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="Check the corpus, config/models.json and results/").set_defaults(fn=cmd_validate)
    m = sub.add_parser("models", help="List configured models")
    m.add_argument("--remote", action="store_true", help="Print the model ids the configured endpoint lists")
    m.set_defaults(fn=cmd_models)
    r = sub.add_parser("run", help="Run a model on the active corpus (repeat the command to resume)")
    r.add_argument("--model", required=True, help="Model id from config/models.json (comma-separate for several)")
    r.add_argument("--run-id", help="Default: <model-id>-<suite>-<config hash>, so the same command resumes")
    r.add_argument("--api-model", help="Override the model name sent to the provider (recorded in the run)")
    r.add_argument("--jobs", type=int, default=3, help="Concurrent requests (default 3)")
    r.add_argument("--timeout", type=int, default=180, help="Seconds per request (default 180)")
    r.add_argument("--rpm", type=float, help="Maximum request starts per minute for this model")
    r.add_argument("--global-rpm", type=float, help="Maximum request starts per minute across runs in this checkout")
    r.add_argument("--max-attempts", type=int, default=2, help="Attempts per row for retryable errors (default 2)")
    r.add_argument("--limit", type=int, help="Only the first N rows (a smoke test; makes a separate run)")
    r.add_argument("--ids", help="Comma-separated row ids (makes a separate run)")
    r.add_argument("--retry-errors", action="store_true", help="Re-run rows whose latest result is an error")
    r.set_defaults(fn=cmd_run)
    pub = sub.add_parser("publish", help="Copy a finished run into results/<suite>/<model-id>/")
    pub.add_argument("run_id")
    pub.add_argument("--force", action="store_true", help="Publish an incomplete or partial run anyway")
    pub.set_defaults(fn=cmd_publish)
    sub.add_parser("leaderboard", help="Rebuild results/<suite>/leaderboard.*").set_defaults(fn=cmd_leaderboard)
    rep = sub.add_parser("report", help="Build site/ data from results/")
    rep.add_argument("--include-runs", action="store_true", help="Also show local runs/ (preview in-progress runs)")
    rep.set_defaults(fn=cmd_report)
    s = sub.add_parser("serve", help="Serve site/ on localhost")
    s.add_argument("--port", type=int, default=8765)
    s.set_defaults(fn=cmd_serve)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        return args.fn(args) or 0
    except (ConfigError, CallError, ValueError, RuntimeError, AssertionError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
