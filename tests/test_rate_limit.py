"""Request starts are paced across models and independent runner instances."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import unittest

from decision_bench.rate_limit import RequestPacer


class Clock:
    def __init__(self):
        self.now = 1000.0

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class PacingTest(unittest.TestCase):
    def test_global_and_model_limits_share_reservations(self):
        with tempfile.TemporaryDirectory() as tmp:
            clock = Clock()
            a = RequestPacer(Path(tmp), "model-a", 60, 120, clock.time, clock.sleep)
            b = RequestPacer(Path(tmp), "model-b", 60, 120, clock.time, clock.sleep)
            self.assertEqual([a.wait(), b.wait(), a.wait(), b.wait()], [0, .5, .5, .5])
            state = json.loads((Path(tmp) / ".request-pacing.json").read_text())
            self.assertEqual(state["models"], {"model-a": 1002.0, "model-b": 1002.5})

    def test_simultaneous_workers_receive_distinct_slots(self):
        with tempfile.TemporaryDirectory() as tmp:
            pacer = RequestPacer(Path(tmp), "model-a", 60, 120,
                                 clock=lambda: 1000.0, sleeper=lambda _seconds: None)
            with ThreadPoolExecutor(max_workers=8) as pool:
                waits = list(pool.map(lambda _: pacer.wait(), range(8)))
            self.assertEqual(sorted(waits), [float(i) for i in range(8)])

    def test_unlimited_makes_no_state_file_and_stale_state_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            clock = Clock()
            pacer = RequestPacer(Path(tmp), "model-a", None, None, clock.time, clock.sleep)
            self.assertEqual(pacer.wait(), 0)
            path = Path(tmp) / ".request-pacing.json"
            self.assertFalse(path.exists())
            path.write_text(json.dumps({"global": 999999, "models": {"model-a": 999999}}))
            pacer = RequestPacer(Path(tmp), "model-a", 60, 120, clock.time, clock.sleep)
            self.assertEqual(pacer.wait(), 0)


if __name__ == "__main__":
    unittest.main()
