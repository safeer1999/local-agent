#!/usr/bin/env bash
# Smoke checks against a running stack (127.0.0.1). Works for mock, CPU and GPU.
# usage: scripts/verify.sh
set -u
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
pass=0; fail=0
ok(){ echo "PASS  $1"; pass=$((pass+1)); }
ko(){ echo "FAIL  $1"; fail=$((fail+1)); }

curl -fsS "http://127.0.0.1:${OLLAMA_PORT}/v1/models" >/dev/null && ok "models endpoint" || ko "models endpoint"
r=$(curl -fsS -m 300 "http://127.0.0.1:${OLLAMA_PORT}/v1/chat/completions" -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL_NAME\",\"messages\":[{\"role\":\"user\",\"content\":\"Say hi\"}]}") \
  && echo "$r" | grep -q '"content"' && ok "chat completion via /v1" || ko "chat completion via /v1"
curl -fsS -m 60 "http://127.0.0.1:${SEARXNG_PORT}/search?q=test&format=json" | grep -q '"results"' \
  && ok "searxng JSON API (engine results need internet)" || ko "searxng JSON API"
docker compose exec -T rag python rag.py query "when do backups run" -k 1 2>/dev/null | grep -q Tuesday \
  && ok "RAG retrieval" || ko "RAG retrieval"
curl -fsS "http://127.0.0.1:${WEBUI_PORT}/health" >/dev/null 2>&1 && ok "open-webui health" || ko "open-webui health (skip if not running)"
echo "passed=$pass failed=$fail"; [ "$fail" -eq 0 ]
