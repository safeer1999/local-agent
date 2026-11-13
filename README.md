# Local private LLM stack

Fully on-device LLM stack (FERPA / IP privacy): Ollama (OpenAI-compatible `/v1`), Open WebUI,
SearXNG (web search), Chroma + a local embedding model (RAG), and OpenCode agent profiles.
Models are US/EU origin only (no Qwen, DeepSeek, Kimi, GLM, MiniMax, Yi, InternLM). Check the
base model of any fine-tune before use.

Every service reads its model from `.env` (`OPENAI_BASE_URL`, `MODEL_NAME`, `MODEL_CODE`,
`MODEL_WRITE`, `MODEL_THINK`, `EMBED_MODEL`). Model names appear nowhere else in the repo; the
GPU-box values are listed as comments in `.env.example`.

## Layout
| File | Purpose |
|---|---|
| `docker-compose.yml` | CPU-capable base: ollama, model-pull, open-webui, searxng, chroma, rag |
| `docker-compose.gpu.yml` | NVIDIA reservation, 32k context, flash attention, 1 loaded model |
| `docker-compose.mock.yml` + `mock/server.py` | Plumbing-only overlay: stdlib mock of Ollama/OpenAI, for sandboxes that cannot pull models |
| `searxng/settings.yml` | SearXNG with JSON output, no limiter, no metrics |
| `rag/` | `rag.py` (index/query) and `mcp_server.py` (stdio MCP tool `rag_query`); sample docs in `rag/docs/` |
| `opencode.json` | Provider + agents `ai-code`, `ai-write`, `ai-think`; MCP: filesystem, git, searxng, rag |
| `aliases.sh` | `ai-code`, `ai-write`, `ai-think` (web on) and `*-private` variants (web off) in a sandboxed container |
| `scripts/verify.sh` | Smoke checks against the running stack |

## Quick start (CPU)
```bash
cp .env.example .env            # set SEARXNG_SECRET: openssl rand -hex 32
docker compose up -d
docker compose logs -f model-pull   # wait for models to download
scripts/verify.sh
source aliases.sh && cd ~/some/project && ai-code
```
UI: http://127.0.0.1:3000 (Open WebUI), http://127.0.0.1:8080 (SearXNG).

## Privacy
- All ports are published on `127.0.0.1` only.
- Telemetry off: `DO_NOT_TRACK`, `SCARF_NO_ANALYTICS`, `ANONYMIZED_TELEMETRY`; OpenCode autoupdate,
  share, models-catalog fetch and LSP downloads are disabled.
- The agent runs in a container with only the current directory mounted, `--cap-drop ALL`,
  `no-new-privileges`. Use the `*-private` aliases (no SearXNG, no webfetch) in FERPA and research folders.
- Web search queries leave the machine (SearXNG forwards them to public engines). Keep sensitive details out of them.
- The sandbox container uses `--network host` so it can reach the localhost-bound services;
  it can therefore also reach the internet. For stricter isolation, add an egress firewall.

## Cloud verification status (CPU sandbox, no GPU, no model registry access)
The cloud sandbox could run Docker, but its egress proxy blocked `registry.ollama.ai`,
`huggingface.co` and the Open WebUI image blob host, so no real model could be loaded and Open WebUI
could not be started. Results using the mock model server:

| Check | Result |
|---|---|
| `docker compose config` (base, +gpu, +mock) | PASS |
| ollama(mock), searxng, chroma, rag containers up, ports on 127.0.0.1 | PASS |
| Chat completion through `/v1/chat/completions` | PASS (mock) |
| RAG index + retrieval over `rag/docs` (mock embeddings), and via the stdio MCP server | PASS |
| SearXNG JSON API | PASS (API up; upstream engines unreachable from sandbox, 0 results) |
| OpenCode agent task on scratch dir (tool call wrote a file) | PASS (mock, scripted tool call) |
| Open WebUI start | SKIPPED (image not pullable) |
| Real model (CPU) chat, real embeddings, real tool-calling | SKIPPED (registry blocked) |
| `aliases.sh` syntax | PASS (`bash -n`); container build/run not exercised |
| Fixed during testing | SearXNG image binds IPv6 by default (`GRANIAN_HOST=::`), now forced to IPv4 |

## Deferred to the GPU machine (on-GPU finishing checklist)
1. `cp .env.example .env`; set `SEARXNG_SECRET`; put the GPU-box model names (see comments in `.env.example`) into `MODEL_*`.
2. NVIDIA Container Toolkit check: `docker run --rm --gpus all ubuntu nvidia-smi`.
3. `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d`; confirm the GPU is used (`docker compose exec ollama ollama ps` shows `100% GPU`).
4. VRAM and KV-cache fit at the chosen context length (`OLLAMA_CONTEXT_LENGTH_GPU`, default 32768); lower it or keep `OLLAMA_KV_CACHE_TYPE=q8_0` if the daily-driver model plus cache exceeds 24 GB.
5. MoE offload flags for the 120B-class model: tune experts-to-system-RAM offload (e.g. a Modelfile/`num_gpu` setting, or llama.cpp `--n-cpu-moe`) until it fits 24 GB VRAM and 125 GB RAM.
6. Load times and tokens per second per model; time a model swap (`MAX_LOADED_MODELS=1`).
7. Real tool-calling reliability in `ai-code`, `ai-write`, `ai-think`; tune permission profiles as needed.
8. Rerun `scripts/verify.sh`, plus: Open WebUI login/chat/web search/RAG upload, a SearXNG query returning real results, and an agent task on a scratch directory.
9. Build the agent sandbox image (`source aliases.sh && ai-code` once) and confirm MCP servers (filesystem, git, searxng, rag) start; the rag MCP server needs the `rag` service indexed first.
10. Confirm no outbound traffic besides SearXNG queries and model pulls.
