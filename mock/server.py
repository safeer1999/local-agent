#!/usr/bin/env python3
"""Mock Ollama/OpenAI-compatible server for plumbing tests only (no model).
Serves /v1/models, /v1/chat/completions (incl. stream + trivial tool-call echo),
/api/tags, /api/pull, /api/embed. Embeddings are deterministic bag-of-words hashes
so RAG retrieval is meaningful. Stdlib only."""
import hashlib
import json
import math
import re
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DIM = 128
MODEL = os.environ.get("MODEL_NAME", "mock")


def embed(text):
    v = [0.0] * DIM
    for w in re.findall(r"\w+", text.lower()):
        v[int(hashlib.md5(w.encode()).hexdigest(), 16) % DIM] += 1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


class H(BaseHTTPRequestHandler):
    def _send(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path in ("/v1/models", "/api/tags", "/api/version"):
            self._send({"object": "list", "data": [{"id": MODEL, "object": "model"}],
                        "models": [{"name": MODEL, "model": MODEL}], "version": "mock"})
        else:
            self._send({"error": "not found"}, 404)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if self.path == "/api/embed":
            inp = body.get("input", [])
            inp = [inp] if isinstance(inp, str) else inp
            self._send({"model": body.get("model"), "embeddings": [embed(t) for t in inp]})
        elif self.path == "/api/pull":
            self._send({"status": "success"})
        elif self.path == "/v1/chat/completions":
            self._chat(body)
        else:
            self._send({"error": "not found"}, 404)

    def _chat(self, body):
        msgs = body.get("messages") or []
        model = body.get("model")
        last = msgs[-1] if msgs else {}
        text = last.get("content") if isinstance(last.get("content"), str) else json.dumps(last.get("content"))
        tools = {t["function"]["name"] for t in body.get("tools") or []}
        msg = {"role": "assistant"}
        # Scripted agent behaviour for plumbing tests: "MOCK_WRITE <path> <content>"
        m = re.search(r"MOCK_WRITE (\S+) (.+)", text or "")
        if last.get("role") == "user" and m and "write" in tools:
            msg["content"] = None
            msg["tool_calls"] = [{"id": "call_1", "type": "function", "function": {
                "name": "write", "arguments": json.dumps({"filePath": m.group(1), "content": m.group(2)})}}]
            finish = "tool_calls"
        else:
            msg["content"] = f"[mock:{model}] " + ("done" if last.get("role") == "tool" else f"You said: {text}")
            finish = "stop"
        if body.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            def ev(delta, fr=None):
                d = {"id": "mock-1", "object": "chat.completion.chunk", "model": model,
                     "choices": [{"index": 0, "delta": delta, "finish_reason": fr}]}
                self.wfile.write(f"data: {json.dumps(d)}\n\n".encode()); self.wfile.flush()
            d0 = {"role": "assistant"}
            if msg.get("tool_calls"):
                ev(d0); tc = dict(msg["tool_calls"][0]); tc["index"] = 0; ev({"tool_calls": [tc]})
            else:
                ev({**d0, "content": msg["content"]})
            ev({}, finish)
            self.wfile.write(b"data: [DONE]\n\n"); self.wfile.flush()
        else:
            self._send({"id": "mock-1", "object": "chat.completion", "model": model,
                        "choices": [{"index": 0, "finish_reason": finish, "message": msg}],
                        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 11434), H).serve_forever()
