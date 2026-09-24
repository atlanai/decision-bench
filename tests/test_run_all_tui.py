"""The dashboard must reflect the current execution, including resumed rows."""
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout


SPEC = importlib.util.spec_from_file_location("run_all_tui", Path(__file__).resolve().parents[1] / "scripts/run_all.py")
run_all = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = run_all
SPEC.loader.exec_module(run_all)


class DashboardTest(unittest.TestCase):
    def test_reads_only_new_log_lines_and_resumed_progress(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(run_all, "ROOT", Path(tmp)):
            model = run_all.ModelRun({"id": "example"}, 5)
            log = Path(tmp) / "runs/example.log"
            log.parent.mkdir()
            log.write_text("[999/999] old: ok correct 0.01s\n")
            model.log_reader = log.open("r")
            model.log_reader.seek(0, os.SEEK_END)
            model.run_id = "example-bench-v4-1234"
            model.started_wall = time.time() - 1
            run_dir = Path(tmp) / "runs" / model.run_id
            run_dir.mkdir()
            (run_dir / "run.json").write_text(json.dumps({
                "config": {"selected_case_ids": ["a", "b", "c", "d", "e"]},
                "executions": [{"pending_rows": 2}],
            }))
            model.read_progress()
            self.assertEqual((model.done, model.total, model.errors), (3, 5, 0))
            with log.open("a") as writer:
                writer.write("[4/5] d: 400 wrong 0.25s\n")
            model.read_progress()
            self.assertEqual((model.done, model.total, model.errors), (4, 5, 1))
            with log.open("a") as writer:
                writer.write('{"run":"example-bench-v4-1234","rows":5,"errors":1}\n')
            model.read_progress()
            self.assertEqual((model.done, model.total, model.errors), (5, 5, 1))
            model.close()

    def test_ten_models_fit_in_a_standard_terminal(self):
        models = [run_all.ModelRun({"id": f"model-{i}"}, 1071) for i in range(10)]
        models[0].state = "running"
        dashboard = run_all.Dashboard(models, interactive=True, colored=False)
        with patch.object(shutil, "get_terminal_size", return_value=os.terminal_size((80, 24))):
            frame = dashboard.frame()
        self.assertLessEqual(len(frame.splitlines()), 24)
        self.assertIn("model-9", frame)
        self.assertTrue(any(spinner in frame for spinner in "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"))

    def test_child_receives_concurrency_and_pacing_flags(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(run_all, "ROOT", Path(tmp)):
            model = run_all.ModelRun({"id": "example"}, 5)
            args = SimpleNamespace(jobs=4, timeout=180, rpm=60, global_rpm=120, limit=5)
            with patch.object(run_all.subprocess, "Popen") as spawn:
                model.start(args)
            cmd = spawn.call_args.args[0]
            self.assertEqual(cmd[cmd.index("--jobs") + 1], "4")
            self.assertEqual(cmd[cmd.index("--rpm") + 1], "60")
            self.assertEqual(cmd[cmd.index("--global-rpm") + 1], "120")
            self.assertEqual(cmd[cmd.index("--limit") + 1], "5")
            model.close()

    def test_main_tracks_a_child_without_calling_a_provider(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(run_all, "ROOT", Path(tmp)):
            def fake_start(model, _args):
                model.log_path = Path(tmp) / "runs" / f"{model.name}.log"
                model.log_path.parent.mkdir(exist_ok=True)
                model.log_writer = model.log_path.open("a")
                model.log_reader = model.log_path.open("r")
                model.log_reader.seek(0, os.SEEK_END)
                model.started, model.started_wall = time.monotonic(), time.time()
                code = ('print("Run fake-run: fake (openai-compatible), 5 rows", flush=True);'
                        'print("[1/5] case-1: ok correct 0.01s", flush=True);'
                        'print("[5/5] case-5: 400 wrong 0.01s", flush=True);'
                        'print(\'{"run":"fake-run","rows":5,"errors":1}\', flush=True)')
                model.process = subprocess.Popen([sys.executable, "-c", code], cwd=tmp,
                                                 stdout=model.log_writer, stderr=subprocess.STDOUT)
                model.state = "running"

            output = io.StringIO()
            with patch.object(run_all.ModelRun, "start", fake_start), redirect_stdout(output):
                result = run_all.main(["--models", "gemini-3.5-flash", "--limit", "5", "--no-tui"])
            session_logs = list((Path(tmp) / "runs").glob("run-all-*.log"))
            self.assertEqual(len(session_logs), 1)
            self.assertIn("gemini-3.5-flash: 5/5 rows", session_logs[0].read_text())
        self.assertEqual(result, 1, output.getvalue())
        self.assertIn("5/5 rows · 1 errors", output.getvalue())
        self.assertIn("Smoke test complete", output.getvalue())

    def test_parallel_limit_starts_two_models_together(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(run_all, "ROOT", Path(tmp)):
            started = []
            active_at_start = []

            def fake_start(model, _args):
                model.log_path = Path(tmp) / "runs" / f"{model.name}.log"
                model.log_writer = model.log_path.open("a")
                model.log_reader = model.log_path.open("r")
                model.log_reader.seek(0, os.SEEK_END)
                model.started, model.started_wall = time.monotonic(), time.time()
                code = ('import time; time.sleep(.12);'
                        f'print("Run {model.name}-run: fake, 1 rows", flush=True);'
                        'print("[1/1] case-1: ok correct 0.01s", flush=True);'
                        f'print(\'{{"run":"{model.name}-run","rows":1,"errors":0}}\', flush=True)')
                model.process = subprocess.Popen([sys.executable, "-c", code], cwd=tmp,
                                                 stdout=model.log_writer, stderr=subprocess.STDOUT)
                model.state = "running"
                started.append(model.process)
                active_at_start.append(sum(p.poll() is None for p in started))

            model_ids = [model["id"] for model in run_all.config.load_models()
                         if model["provider"] in run_all.API][:3]
            with patch.object(run_all.ModelRun, "start", fake_start), redirect_stdout(io.StringIO()):
                result = run_all.main(["--models", ",".join(model_ids),
                                       "--parallel", "2", "--limit", "1", "--no-tui"])
        self.assertEqual(result, 0)
        self.assertEqual(len(started), 3)
        self.assertEqual(max(active_at_start), 2)


if __name__ == "__main__":
    unittest.main()
