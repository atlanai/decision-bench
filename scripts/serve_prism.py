"""Sarvam-Prism on Modal behind a System One endpoint for the `prism` provider; see docs/running.md."""
import hmac
import os
import threading
import time

import modal

REPO, REVISION = "sarvamai/prism", "417cf26c2eea27286a803dd721b4e78698bdb875"
APP = "decision-bench-sarvam-prism"

app = modal.App(APP)
cache = modal.Volume.from_name(f"{APP}-cache", create_if_missing=True)
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("build-essential")
    .uv_pip_install("torch==2.8.0", "triton==3.4.0", "transformers==4.52.1", "accelerate==1.10.1",
                    "safetensors==0.6.2", "huggingface_hub==0.35.3", "fastapi==0.116.1")
    .env({"HF_HOME": "/hf", "TRITON_CACHE_DIR": "/hf/triton-cache", "HF_HUB_DISABLE_PROGRESS_BARS": "1",
          "TOKENIZERS_PARALLELISM": "false", "PYTHONUNBUFFERED": "1"})
)
KEY = os.environ.get("PRISM_API_KEY", "")
if len(KEY) < 24:
    raise SystemExit("PRISM_API_KEY must be at least 24 characters, for example from `openssl rand -hex 24`")
secret = modal.Secret.from_dict({"PRISM_API_KEY": KEY})


def snapshot():
    from huggingface_hub import snapshot_download
    return snapshot_download(REPO, revision=REVISION)


@app.function(image=image, volumes={"/hf": cache}, secrets=[secret], cpu=8, memory=16384, timeout=3600)
def download():
    print(snapshot())
    cache.commit()


@app.cls(image=image, gpu=["B200", "H200"], cpu=8, memory=(32768, 131072), volumes={"/hf": cache}, secrets=[secret],
         max_containers=1, scaledown_window=600, startup_timeout=1800, timeout=600)
class Prism:
    @modal.enter()
    def load(self):
        import sys
        import torch
        started = time.time()
        path = snapshot()
        sys.path.insert(0, path)
        from prism import Prism
        self.model = Prism.from_pretrained(path)
        self.lock = threading.Lock()
        cache.commit()
        print(f"serving {REPO}@{REVISION[:12]} on {torch.cuda.get_device_name(0)}, ready in {time.time() - started:.0f}s")

    @modal.asgi_app(label="sarvam-prism-api")
    def web(self):
        from fastapi import FastAPI, Header, HTTPException
        api = FastAPI()
        key = KEY.encode()

        @api.post("/v1/systemone")
        def systemone(body: dict, authorization: str = Header("")):
            if not hmac.compare_digest(authorization.encode(), b"Bearer " + key):
                raise HTTPException(401, "invalid bearer key")
            if body.get("model") != REPO:
                raise HTTPException(422, f"this endpoint serves {REPO}")
            if not isinstance(body.get("questions"), dict) or not body["questions"]:
                raise HTTPException(422, "questions must be a non-empty object")
            started = time.perf_counter()
            try:
                with self.lock:
                    answers = self.model.decide(body.get("state"), body["questions"])
            except ValueError as e:
                raise HTTPException(422, str(e)) from e
            return {"model": f"{REPO}@{REVISION}", "answers": answers,
                    "latency_ms": (time.perf_counter() - started) * 1000}

        return api
