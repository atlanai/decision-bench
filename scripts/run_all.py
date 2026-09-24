#!/usr/bin/env python3
"""Run all configured API models, publish completed runs, and rebuild the site.

  python3 scripts/run_all.py --plan                  # preview selected models
  python3 scripts/run_all.py                         # run API models, three at a time
  python3 scripts/run_all.py --models a,b --jobs 4   # select models and request concurrency
  python3 scripts/run_all.py --limit 5               # smoke test; never publishes

Each model runs in its own resumable process. The dashboard reads only new
output from that process's log. CLI providers are opt-in.
"""
from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from decision_bench import config, corpus  # noqa: E402

API = {"openai-compatible", "typesafe", "djev", "laya"}
BLUE = (32, 38, 210)      # Atlan Blue 500
CYAN = (98, 225, 252)     # Atlan Cyan 500
PINK = (243, 77, 119)     # Atlan Pink 500
PIXELS = {
    "B": ("####.", "#...#", "####.", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "####.", "#....", "#####"),
    "H": ("#...#", "#...#", "#####", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "#####"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", ".###."),
    "S": (".####", "#....", ".###.", "....#", "####."),
}
ROW = re.compile(r"^\[(\d+)/(\d+)\] (.*?): (\S+) (correct|wrong) ([\d.]+)s$")
RUN = re.compile(r"^Run ([^:]+):")


def color(text: str, rgb: tuple[int, int, int], enabled: bool) -> str:
    if not enabled:
        return text
    return f"\033[38;2;{rgb[0]};{rgb[1]};{rgb[2]}m{text}\033[0m"


def pixel_word(word: str) -> list[str]:
    return [" ".join("".join("█" if cell == "#" else " " for cell in PIXELS[letter][row])
                     for letter in word) for row in range(5)]


def banner(width: int, colored: bool) -> list[str]:
    if width < 54:
        return [color("▦ DECISION BENCH", BLUE, colored), "  the bounded-decision benchmark"]
    lines = []
    for word in ("DECISION", "BENCH"):
        for pixels in pixel_word(word):
            if colored:
                # Approved Atlan pairing: white and cyan details on Blue 500.
                lines.append(f"\033[48;2;32;38;210m\033[37m  {pixels}  \033[0m")
            else:
                lines.append(f"  {pixels}")
        if word == "DECISION":
            lines.append(color("  ▪ ▪ ▪  bounded decisions · measured openly", CYAN, colored))
    return lines


def elapsed(seconds: float) -> str:
    minutes, sec = divmod(int(max(0, seconds)), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{sec:02d}" if hours else f"{minutes:02d}:{sec:02d}"


@dataclass
class ModelRun:
    model: dict
    total: int
    state: str = "queued"
    done: int = 0
    errors: int = 0
    run_id: str | None = None
    process: subprocess.Popen | None = None
    log_path: Path | None = None
    log_writer: object | None = None
    log_reader: object | None = None
    started: float | None = None
    started_wall: float | None = None
    ended: float | None = None
    code: int | None = None
    last_row: str = ""
    detail: str = ""
    resume_checked: bool = False

    @property
    def name(self) -> str:
        return self.model["id"]

    def start(self, args) -> None:
        cmd = [sys.executable, "-m", "decision_bench", "run", "--model", self.name,
               "--jobs", str(args.jobs), "--timeout", str(args.timeout),
               "--rpm", str(args.rpm), "--global-rpm", str(args.global_rpm)]
        if args.limit:
            cmd += ["--limit", str(args.limit)]
        self.log_path = ROOT / "runs" / f"{self.name}.log"
        self.log_path.parent.mkdir(exist_ok=True)
        self.log_writer = self.log_path.open("a", encoding="utf-8")
        self.log_reader = self.log_path.open("r", encoding="utf-8", errors="replace")
        self.log_reader.seek(0, os.SEEK_END)
        self.started, self.started_wall = time.monotonic(), time.time()
        try:
            self.process = subprocess.Popen(cmd, cwd=ROOT, stdout=self.log_writer, stderr=subprocess.STDOUT)
        except OSError:
            self.close()
            raise
        self.state = "running"

    def read_progress(self) -> None:
        if self.log_reader is None:
            return
        while True:
            position = self.log_reader.tell()
            line = self.log_reader.readline()
            if not line:
                break
            if not line.endswith("\n"):
                self.log_reader.seek(position)
                break
            line = line.strip()
            match = ROW.match(line)
            if match:
                self.done, self.total = int(match.group(1)), int(match.group(2))
                self.errors += match.group(4) != "ok"
                self.last_row = f"{match.group(3)} · {match.group(4)} · {match.group(5)} · {match.group(6)}s"
            elif match := RUN.match(line):
                self.run_id = match.group(1)
            elif line.startswith("{"):
                try:
                    summary = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(summary, dict) and "rows" in summary and "errors" in summary:
                    self.done = self.total = summary["rows"]
                    self.errors = summary["errors"]
                    self.run_id = summary.get("run", self.run_id)
            elif line.startswith("error:"):
                self.detail = line
        if self.run_id and not self.resume_checked:
            self.read_resume_count()

    def read_resume_count(self) -> None:
        path = ROOT / "runs" / self.run_id / "run.json"
        try:
            if path.stat().st_mtime < self.started_wall:
                return  # A previous execution's metadata; the child has not updated it yet.
            meta = json.loads(path.read_text())
            pending = meta["executions"][-1]["pending_rows"]
            self.total = len(meta["config"]["selected_case_ids"])
            self.done = max(self.done, self.total - pending)
            self.errors = max(self.errors, meta.get("cases_with_errors", 0))
            self.resume_checked = True
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            pass

    def finish(self) -> None:
        self.read_progress()
        self.code = self.process.poll()
        self.ended = time.monotonic()
        self.state = "failed" if self.code else ("issues" if self.errors else "done")
        self.close()

    def close(self) -> None:
        for handle in (self.log_reader, self.log_writer):
            if handle:
                handle.close()
        self.log_reader = self.log_writer = None


@dataclass
class Dashboard:
    models: list[ModelRun]
    interactive: bool
    colored: bool
    limits: str = ""
    session_log: Path | None = None
    phase: str = "RUN"
    publish_done: int = 0
    publish_total: int = 0
    events: deque = field(default_factory=lambda: deque(maxlen=4))
    started: float = field(default_factory=time.monotonic)
    last_milestone: dict = field(default_factory=dict)

    def event(self, message: str) -> None:
        self.events.append(message)
        if self.session_log:
            with self.session_log.open("a", encoding="utf-8") as log:
                log.write(f"{datetime.now().astimezone().isoformat(timespec='seconds')}  {message}\n")
        if not self.interactive:
            print(message, flush=True)

    def frame(self) -> str:
        terminal = shutil.get_terminal_size((100, 30))
        width = max(40, terminal.columns)
        # Keep every model visible on ordinary 24–30 line terminals. The full
        # pixel title appears as a splash before this compact dashboard.
        lines = (banner(width, self.colored) if terminal.lines >= len(self.models) + 29
                 else [color("  ▦ DECISION BENCH", BLUE, self.colored)])
        heading = "  BENCH COMPLETE" if self.phase == "DONE" else "  BENCH RUN"
        lines += ["", color(heading, BLUE, self.colored)
                  + f"   {sum(m.done for m in self.models):,}/{sum(m.total for m in self.models):,} rows"
                  + f"   {elapsed(time.monotonic() - self.started)} elapsed",
                  "  " + self.limits,
                  "  " + "─" * min(width - 4, 86)]
        compact = width < 83
        for model in self.models:
            icon = ("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"[int(time.monotonic() * 5) % 10] if model.state == "running"
                    else {"queued": "○", "done": "✓", "issues": "!", "failed": "×"}.get(model.state, "·"))
            icon = color(icon, CYAN if model.state == "running" else BLUE, self.colored)
            label = model.name[:23].ljust(23)
            ratio = model.done / model.total if model.total else 0
            if compact:
                line = f"  {icon} {label} {model.state.upper():<7} {model.done:>4}/{model.total:<4}  {model.errors} err"
            else:
                blocks = min(20, max(0, round(ratio * 20)))
                bar = color("█" * blocks, CYAN, self.colored) + "░" * (20 - blocks)
                line = f"  {icon} {label} {bar} {model.done:>4}/{model.total:<4}  {model.state.upper():<7}"
                if model.errors:
                    line += color(f" {model.errors} err", PINK, self.colored)
                if model.started:
                    line += f"  {elapsed((model.ended or time.monotonic()) - model.started)}"
            lines.append(line)
        lines += ["  " + "─" * min(width - 4, 86),
                  f"  {self._phase('RUN')}  →  {self._phase('PUBLISH')}  →  "
                  f"{self._phase('LEADERBOARD')}  →  {self._phase('SITE')}"]
        if self.publish_total:
            lines.append(f"  Publish attempts {self.publish_done}/{self.publish_total}")
        active = next((model for model in reversed(self.models) if model.state == "running" and model.last_row), None)
        if active:
            lines.append(f"  Latest: {active.name} · {active.last_row}"[:width - 1])
        event_slots = max(0, terminal.lines - len(lines) - 5)
        if self.events and event_slots:
            lines += ["", color("  ACTIVITY", BLUE, self.colored)]
            lines += ["  " + event[:max(10, width - 4)] for event in list(self.events)[-event_slots:]]
        footer = "  Model output: runs/<model-id>.log"
        if self.phase == "RUN":
            footer += "  ·  Ctrl-C stops active models"
        lines += ["", footer]
        if self.session_log and terminal.lines > len(lines):
            lines.append("  Session log: " + str(self.session_log.relative_to(ROOT)))
        return "\n".join(lines) + "\n"

    def _phase(self, name: str) -> str:
        return color(f"● {name}", BLUE, self.colored) if self.phase == name else name

    def render(self) -> None:
        if self.interactive:
            sys.stdout.write("\033[H\033[J" + self.frame())
            sys.stdout.flush()


def pipeline_step(cmd: list[str], dashboard: Dashboard, label: str) -> bool:
    """Keep the dashboard responsive while a publish or build command runs."""
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as output:
        process = subprocess.Popen(cmd, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
        try:
            while process.poll() is None:
                dashboard.render()
                time.sleep(0.2)
        except KeyboardInterrupt:
            process.terminate()
            process.wait()
            raise
        output.seek(0)
        lines = output.read().strip().splitlines()
    if process.returncode:
        dashboard.event(f"{label} failed: {(lines[-1] if lines else 'exit ' + str(process.returncode))}")
        return False
    dashboard.event(f"{label} complete")
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", help="comma-separated model ids (default: every API model)")
    parser.add_argument("--parallel", type=int, default=3, help="models run at the same time (default 3)")
    parser.add_argument("--jobs", type=int, default=4, help="concurrent requests per model (default 4)")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--rpm", type=float, default=60, help="maximum request starts per minute per model (default 60)")
    parser.add_argument("--global-rpm", type=float, default=120,
                        help="maximum request starts per minute across this checkout (default 120)")
    parser.add_argument("--limit", type=int, help="rows per model, for a smoke test")
    parser.add_argument("--include-cli", action="store_true")
    parser.add_argument("--no-publish", action="store_true", help="run only; do not publish or rebuild the site")
    parser.add_argument("--no-tui", action="store_true", help="print progress as lines, even in a terminal")
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args(argv)

    interactive = sys.stdout.isatty() and not args.no_tui and os.environ.get("TERM") != "dumb"
    colored = interactive and "NO_COLOR" not in os.environ
    if not interactive:
        print("\n".join(banner(shutil.get_terminal_size((100, 30)).columns, False)), flush=True)
    for name in ("parallel", "jobs", "timeout", "limit", "rpm", "global_rpm"):
        value = getattr(args, name)
        if value is not None and (not math.isfinite(value) or value <= 0):
            parser.error(f"--{name.replace('_', '-')} must be positive")
    models = config.load_models()
    wanted = set(args.models.split(",")) if args.models else None
    chosen = [m for m in models if (wanted is None or m["id"] in wanted)
              and (m["provider"] in API or args.include_cli)]
    if wanted:
        missing = wanted - {m["id"] for m in chosen}
        if missing:
            parser.error(f"unknown or skipped models: {sorted(missing)}")
    if args.plan:
        if interactive:
            print("\n".join(banner(shutil.get_terminal_size((100, 30)).columns, colored)))
        print(f"\n  {len(chosen)} models selected · {args.parallel} models at once · {args.jobs} requests each")
        print(f"  Pacing: {args.rpm:g} rpm per model · {args.global_rpm:g} rpm across all models\n")
        for model in chosen:
            print(f"  {model['id']:<28} {model['provider']:<18} vision={bool(model.get('vision'))}")
        return 0
    if not chosen:
        print("No models selected.")
        return 0

    total = len(corpus.load_cases())
    selected = min(args.limit, total) if args.limit else total
    session_log = ROOT / "runs" / f"run-all-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{os.getpid()}.log"
    session_log.parent.mkdir(exist_ok=True)
    limits = f"{args.parallel} models × {args.jobs} jobs  ·  {args.rpm:g} rpm/model  ·  {args.global_rpm:g} rpm total"
    dashboard = Dashboard([ModelRun(model, selected) for model in chosen], interactive, colored,
                          limits=limits, session_log=session_log)
    dashboard.event(f"Session started · {len(chosen)} models · {limits}")
    dashboard.event(f"Session log: {session_log.relative_to(ROOT)}")
    if interactive:
        sys.stdout.write("\033[?25l\033[H\033[J" + "\n".join(
            banner(shutil.get_terminal_size((100, 30)).columns, colored)) + "\n")
        sys.stdout.flush()
        time.sleep(0.55)
    try:
        dashboard.render()
        next_model = 0
        running: list[ModelRun] = []
        while next_model < len(dashboard.models) or running:
            while next_model < len(dashboard.models) and len(running) < args.parallel:
                model = dashboard.models[next_model]
                try:
                    model.start(args)
                except OSError as exc:
                    model.state, model.code = "failed", 1
                    dashboard.event(f"Could not start {model.name}: {exc}")
                else:
                    running.append(model)
                    dashboard.event(f"Started {model.name} · {model.model['provider']}")
                next_model += 1
            for model in running[:]:
                model.read_progress()
                if model.total and model.done:
                    bucket = model.done * 10 // model.total
                    if bucket > dashboard.last_milestone.get(model.name, -1):
                        dashboard.last_milestone[model.name] = bucket
                        dashboard.event(f"{model.name}: {model.done}/{model.total} rows · {model.errors} errors")
                if model.process.poll() is not None:
                    model.finish()
                    running.remove(model)
                    dashboard.event(f"{model.name}: {model.state} · {model.done}/{model.total} rows · "
                                    f"{model.errors} errors · {elapsed(model.ended - model.started)} · "
                                    f"{model.log_path.relative_to(ROOT)}")
                    if model.detail:
                        dashboard.event(f"{model.name}: {model.detail}")
            dashboard.render()
            if running:
                time.sleep(0.2)

        run_ok = all(model.code == 0 and model.errors == 0 for model in dashboard.models)
        if args.no_publish or args.limit:
            dashboard.phase = "DONE"
            dashboard.event(("Smoke test complete" if args.limit else "Runs complete")
                            + f" · {sum(model.errors for model in dashboard.models)} row errors")
            dashboard.render()
            return 0 if run_ok else 1

        # Publish matching full runs, including ones resumed earlier.
        paths = []
        selected_ids = {model.name for model in dashboard.models}
        for path in sorted((ROOT / "runs").glob("*/run.json")):
            try:
                meta = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if (meta.get("config", {}).get("model_id") in selected_ids
                    and str(meta.get("status", "")).startswith("completed")
                    and not path.parent.name.endswith("-subset")):
                paths.append(path)
        dashboard.phase = "PUBLISH"
        dashboard.publish_total = len(paths)
        dashboard.render()
        publish_ok = True
        for path in paths:
            ok = pipeline_step([sys.executable, "-m", "decision_bench", "publish", path.parent.name],
                               dashboard, f"Publish {path.parent.name}")
            publish_ok &= ok
            dashboard.publish_done += 1
            dashboard.render()
        dashboard.phase = "LEADERBOARD"
        leaderboard_ok = pipeline_step([sys.executable, "-m", "decision_bench", "leaderboard"],
                                       dashboard, "Leaderboard")
        dashboard.phase = "SITE"
        site_ok = pipeline_step([sys.executable, "-m", "decision_bench", "report"], dashboard, "Site report")
        dashboard.phase = "DONE"
        dashboard.event("Finished · " + ("all steps passed" if all((run_ok, publish_ok, leaderboard_ok, site_ok))
                                         else "some steps failed; see activity and model logs"))
        dashboard.render()
        return 0 if all((run_ok, publish_ok, leaderboard_ok, site_ok)) else 1
    except KeyboardInterrupt:
        dashboard.event("Interrupted; stopping active models")
        for model in dashboard.models:
            if model.process and model.process.poll() is None:
                model.process.terminate()
        for model in dashboard.models:
            if model.process:
                model.process.wait()
                model.close()
        dashboard.render()
        return 130
    finally:
        for model in dashboard.models:
            if model.process and model.process.poll() is None:
                model.process.terminate()
                model.process.wait()
            model.close()
        if interactive:
            sys.stdout.write("\033[?25h\033[0m\n")
            sys.stdout.flush()


if __name__ == "__main__":
    sys.exit(main())
