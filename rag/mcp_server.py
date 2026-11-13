#!/usr/bin/env python3
"""Minimal stdio MCP server exposing rag_query to the agent harness.
Runs on the host (needs: pip install chromadb-client requests). Reads
OLLAMA_URL, CHROMA_URL and EMBED_MODEL from the environment (see aliases.sh)."""
import contextlib
import io
import json
import sys

import rag


def reply(i, res):
    print(json.dumps({"jsonrpc": "2.0", "id": i, "result": res}), flush=True)


for line in sys.stdin:
    m = json.loads(line)
    i, meth = m.get("id"), m.get("method")
    if meth == "initialize":
        reply(i, {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                  "serverInfo": {"name": "local-rag", "version": "0.1"}})
    elif meth == "tools/list":
        reply(i, {"tools": [{"name": "rag_query", "description": "Search local indexed documents",
                             "inputSchema": {"type": "object",
                                             "properties": {"query": {"type": "string"}},
                                             "required": ["query"]}}]})
    elif meth == "tools/call":
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rag.query(m["params"]["arguments"]["query"])
        reply(i, {"content": [{"type": "text", "text": buf.getvalue()}]})
