"""Amos 1 large from its open weights on Modal, behind a System One endpoint for the `laya` provider; see docs/running.md."""
import os
import time

import modal
from systemone_gate import refusal, require_key

REPO, REVISION = "mukaddamzaid/amos-1-large", "362f4dc8da538beda4157a882bfabc4bc6a4538a"
MODEL = "amos-1-large"
APP = "decision-bench-amos-1-large"
MAX_LEN = 131072
ROTATIONS = int(os.environ.get("AMOS_ROTATIONS", "4"))
if ROTATIONS < 1:
    raise SystemExit("AMOS_ROTATIONS must be 1 or more")

app = modal.App(APP)
cache = modal.Volume.from_name(f"{APP}-cache", create_if_missing=True)
image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install("torch==2.14.0", index_url="https://download.pytorch.org/whl/cu130")
    .uv_pip_install("transformers==5.17.0", "flash-linear-attention==0.5.2", "safetensors==0.8.0", "tokenizers==0.23.2",
                    "pillow==12.3.0", "huggingface-hub==1.33.0", "fastapi==0.116.1")
    .env({"HF_HOME": "/hf", "TRITON_CACHE_DIR": "/hf/triton-cache", "HF_HUB_DISABLE_PROGRESS_BARS": "1",
          "TOKENIZERS_PARALLELISM": "false", "PYTHONUNBUFFERED": "1", "AMOS_ROTATIONS": str(ROTATIONS)})
    .add_local_python_source("systemone_gate")
)
KEY = require_key("AMOS_API_KEY")
secret = modal.Secret.from_dict({"AMOS_API_KEY": KEY})


def snapshot():
    from huggingface_hub import snapshot_download
    return snapshot_download(REPO, revision=REVISION)


@app.function(image=image, volumes={"/hf": cache}, secrets=[secret], cpu=8, memory=16384, timeout=7200)
def download():
    print(snapshot())
    cache.commit()


@app.cls(image=image, gpu="H100", cpu=8, memory=(32768, 131072), volumes={"/hf": cache}, secrets=[secret],
         max_containers=1, scaledown_window=300, startup_timeout=1800, timeout=600)
class Amos:
    @modal.enter()
    def load(self):
        import sys
        import torch
        started = time.time()
        path = snapshot()
        sys.path.insert(0, f"{path}/serve")
        from amos.serve import BadRequest, load_engine
        self.bad_request = BadRequest
        self.engine = load_engine(path, "cuda", f"{REPO}@{REVISION}", MAX_LEN, ROTATIONS)
        cache.commit()
        print(f"serving {REPO}@{REVISION[:12]} on {torch.cuda.get_device_name(0)} with {ROTATIONS} rotations, "
              f"torch {torch.__version__}, ready in {time.time() - started:.0f}s")

    @modal.asgi_app(label="amos-1-large-api")
    def web(self):
        from fastapi import FastAPI, Header, HTTPException
        api = FastAPI()

        @api.post("/v1/systemone")
        def systemone(body: dict, authorization: str = Header("")):
            if refused := refusal(authorization, body, KEY, MODEL):
                raise HTTPException(*refused)
            try:
                return self.engine(body)
            except self.bad_request as e:
                raise HTTPException(422, str(e)) from e

        return api
