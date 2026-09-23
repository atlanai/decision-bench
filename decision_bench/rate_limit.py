"""Coordinate request start times across concurrent benchmark processes.

The file contains only timing reservations and model ids. A short POSIX file
lock makes reservations atomic; processes sleep outside the lock so other
models can reserve their own slots.
"""
from __future__ import annotations

import json
from pathlib import Path
import time


class RequestPacer:
    def __init__(self, runs: Path, model_id: str, rpm: float | None, global_rpm: float | None,
                 clock=None, sleeper=None):
        self.path = Path(runs) / ".request-pacing.json"
        self.model_id = model_id
        self.rpm = rpm
        self.global_rpm = global_rpm
        self.clock = clock or time.time
        self.sleeper = sleeper or time.sleep

    def wait(self) -> float:
        """Reserve the next permitted start and return seconds spent pacing."""
        if not (self.rpm or self.global_rpm):
            return 0.0
        import fcntl  # POSIX only; importing the module remains safe for read-only commands.
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                handle.seek(0)
                try:
                    state = json.load(handle)
                except (ValueError, TypeError):
                    state = {}
                now = self.clock()
                # A clock adjustment or an old file must not delay a new run indefinitely.
                def next_slot(value):
                    return value if isinstance(value, (int, float)) and now - 3600 < value < now + 3600 else now

                models = state.get("models") if isinstance(state.get("models"), dict) else {}
                ready = now
                if self.rpm:
                    ready = max(ready, next_slot(models.get(self.model_id)))
                if self.global_rpm:
                    ready = max(ready, next_slot(state.get("global")))
                if self.rpm:
                    models[self.model_id] = ready + 60 / self.rpm
                if self.global_rpm:
                    state["global"] = ready + 60 / self.global_rpm
                state["models"] = models
                handle.seek(0)
                handle.truncate()
                json.dump(state, handle)
                handle.flush()
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)
        delay = max(0.0, ready - self.clock())
        if delay:
            self.sleeper(delay)
        return delay
