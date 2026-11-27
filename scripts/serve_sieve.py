"""Sieve-31B-v4 from its open weights on Modal: sieve-serve at a pinned commit behind a bearer-key gate; see docs/running.md."""
import json
import socket
import subprocess
import time
import urllib.error
import urllib.request

import modal
from systemone_gate import refusal, require_key

REPO, REVISION = "sthanika-ai/Sieve-31B-v4", "464dc7f46e150407aec322634d321071ba4b433f"
SIEVE = "1e64657c930f91db7119b5638774c0f11a77e441"
APP = "decision-bench-sieve-31b-v4"
PORT = 8020

app = modal.App(APP)
cache = modal.Volume.from_name(f"{APP}-cache", create_if_missing=True)
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git")
    .run_commands(
        f"pip install -r https://raw.githubusercontent.com/sthanika-ai/Sieve/{SIEVE}/requirements.txt",
        f"pip install 'sieve-decisions[serve] @ git+https://github.com/sthanika-ai/Sieve@{SIEVE}'",
    )
    .env({"HF_HOME": "/hf", "HF_HUB_DISABLE_PROGRESS_BARS": "1", "PYTHONUNBUFFERED": "1"})
    .add_local_python_source("systemone_gate")
)
KEY = require_key("SIEVE_GATE_KEY")
secret = modal.Secret.from_dict({"SIEVE_GATE_KEY": KEY})
WEIGHTS = f"/hf/sieve-31b-v4-{REVISION[:8]}"


@app.function(image=image, volumes={"/hf": cache}, secrets=[secret], cpu=8, memory=16384, timeout=7200)
def download():
    from huggingface_hub import snapshot_download
    print(snapshot_download(REPO, revision=REVISION, local_dir=WEIGHTS))
    cache.commit()


@app.cls(image=image, gpu="H100", cpu=8, memory=(65536, 131072), volumes={"/hf": cache}, secrets=[secret],
         max_containers=1, scaledown_window=600, startup_timeout=1800, timeout=600)
@modal.concurrent(max_inputs=8)
class Sieve:
    @modal.enter()
    def start(self):
        started = time.time()
        self.proc = subprocess.Popen(["sieve-serve", "--model", WEIGHTS, "--port", str(PORT)])
        while True:
            if self.proc.poll() is not None:
                raise RuntimeError(f"sieve-serve exited with {self.proc.returncode}")
            try:
                socket.create_connection(("127.0.0.1", PORT), timeout=1).close()
                break
            except OSError:
                time.sleep(2)
        print(f"sieve-serve {SIEVE[:7]} serving {REPO}@{REVISION[:12]}, ready in {time.time() - started:.0f}s")

    @modal.asgi_app(label="sieve-31b-v4-api")
    def web(self):
        from fastapi import FastAPI, Header, HTTPException
        from fastapi.responses import JSONResponse
        api = FastAPI()

        @api.post("/v1/decide")
        def decide(body: dict, authorization: str = Header("")):
            if refused := refusal(authorization, body, KEY, REPO):
                raise HTTPException(*refused)
            request = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/decide", data=json.dumps(body).encode(),
                                             headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(request, timeout=300) as response:
                    return JSONResponse(json.load(response), response.status)
            except urllib.error.HTTPError as e:
                return JSONResponse({"error": e.read().decode(errors="replace")}, e.code)

        return api
