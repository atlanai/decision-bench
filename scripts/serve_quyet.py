"""Quyet 1.2 Large behind a serial System One endpoint; see docs/running.md."""
import argparse
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import ipaddress
import json
import os
import socket
import time
import traceback

REPO = "chinhnc/Quyet-1.2-Large"
REVISION = "ffad03b6f20aa548ba2e045410e9fcafe4ddf0d2"
MODEL = "Quyet-1.2-Large"


def require_key(host, key):
    try:
        local = ipaddress.ip_address(host).is_loopback
    except ValueError:
        local = host == "localhost"
    if not local and not key:
        raise ValueError("QUYET_API_KEY is required when binding outside loopback")


def handler(model, question_error, key, memory=lambda: {}):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # No client addresses or request bodies in logs.

        def send_json(self, status, body):
            data = json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            if self.path != "/v1/systemone":
                self.send_json(404, {"error": "not found"})
                return
            if key and not hmac.compare_digest(self.headers.get("Authorization", "").encode(),
                                               b"Bearer " + key.encode()):
                self.send_json(401, {"error": "invalid bearer key"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if size <= 0 or size > 4 * 1024 * 1024:
                    raise ValueError("body must be JSON of 1 to 4194304 bytes")
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict):
                    raise ValueError("body must be an object")
                if "images" in body:
                    raise ValueError("images are not supported; send the text rendering in state")
                if set(body) != {"model", "state", "questions"}:
                    raise ValueError("expected exactly model, state and questions")
                if body["model"] != MODEL:
                    raise ValueError(f"this endpoint serves {MODEL}")
            except (ValueError, UnicodeError) as exc:
                self.send_json(400, {"error": str(exc)})
                return
            started = time.perf_counter()
            try:
                response = model.predict(body["state"], body["questions"], strict=True)
            except question_error as exc:
                self.send_json(400, {"error": str(exc)})
                return
            except Exception:
                traceback.print_exc()
                self.send_json(500, {"error": "model inference failed; see server log"})
                return
            response = {**response, "latency_ms": (time.perf_counter() - started) * 1000}
            self.send_json(200, response)
            print(json.dumps({"event": "request", "latency_ms": response["latency_ms"],
                              **memory()}), flush=True)
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    key = os.environ.get("QUYET_API_KEY", "")
    require_key(args.host, key)
    import torch
    import transformers
    import quyet
    if quyet.__version__ != "1.2.0" or transformers.__version__ != "5.17.0":
        raise RuntimeError("Use quyet==1.2.0 and transformers==5.17.0")
    started = time.perf_counter()
    model = quyet.load(REPO, revision=REVISION, device="cuda", dtype=torch.bfloat16, prefix_cache=False)

    def memory():
        return {"peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                "peak_reserved_bytes": torch.cuda.max_memory_reserved()}

    print(json.dumps({"event": "loaded", "model": REPO, "revision": REVISION,
                      "load_seconds": time.perf_counter() - started, "torch": torch.__version__,
                      "transformers": transformers.__version__, "quyet": quyet.__version__,
                      "gpu": torch.cuda.get_device_name(0), **memory()}), flush=True)
    class Server(HTTPServer):
        address_family = socket.AF_INET6 if ":" in args.host else socket.AF_INET
    with Server((args.host, args.port), handler(model, quyet.QuestionError, key, memory)) as server:
        print("System One ready (one request at a time)", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
