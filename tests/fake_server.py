"""A local OpenAI-compatible endpoint for tests. It never calls a real model."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeEndpoint:
    """Answers every chat completion with the first allowed label. `fail_first` makes the first N calls 429."""

    def __init__(self, fail_first=0, cost_header="0.0005", content=None):
        self.requests, self.fail_first, self.cost_header, self.content = [], fail_first, cost_header, content
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, code, body, headers=()):
                data = json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("x-litellm-model-id", "internal-deployment-should-be-dropped")
                for k, v in headers:
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                owner.requests.append({"path": self.path, "headers": dict(self.headers)})
                self._send(200, {"data": [{"id": "fake/model-1"}, {"id": "fake/model-2"}]})

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                owner.requests.append({"path": self.path, "headers": dict(self.headers), "body": body})
                if len(owner.requests) <= owner.fail_first:
                    return self._send(429, {"error": "slow down"})
                fmt = body.get("response_format") or {}
                schema = (fmt["json_schema"]["schema"] if fmt.get("type") == "json_schema" else
                          json.loads(body["messages"][-1]["content"].split("Required response JSON schema:\n", 1)[1]))
                qid, spec = next(iter(schema["properties"]["answers"]["properties"].items()))
                labels = spec["properties"]["label"]["enum"]
                probs = {label: (0.8 if i == 0 else 0.2 / (len(labels) - 1)) for i, label in enumerate(labels)}
                text = owner.content if owner.content is not None else json.dumps(
                    {"answers": {qid: {"label": labels[0], "probabilities": probs}}})
                headers = [("x-litellm-response-cost", owner.cost_header)] if owner.cost_header else []
                self._send(200, {"id": "chatcmpl-1", "model": body["model"],
                                 "choices": [{"message": {"content": text}, "finish_reason": "stop"}],
                                 "usage": {"prompt_tokens": 100, "completion_tokens": 20}}, headers)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/v1"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()
