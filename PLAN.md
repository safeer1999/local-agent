# Local private LLM stack: build in the cloud, finish on the GPU box

## Context
Goal: run LLMs fully on-device (FERPA and IP privacy) for language and coding work, with agentic abilities (file edits, RAG, web search). The target machine has an RTX 3090 (24 GB), 125 GB RAM, a Ryzen 9 5950X, 175 GB free disk, Docker and Python, and no Ollama yet. The model must not be China-developed (Texas rule on public machines), so Qwen, DeepSeek, Kimi, GLM, MiniMax, Yi and InternLM are excluded. Check the base model of any fine-tune before use. The user has no time for GPU tuning now, so the stack is built in a cloud Claude Code session with a placeholder LLM and finished on the machine later.

## Model choices (US/EU origin)
- Daily driver (coding, agentic, general): gpt-oss-20b (about 13 GB, Apache 2.0)
- Heavy tasks: gpt-oss-120b (about 60 GB, MoE experts offloaded to system RAM)
- Coding agent: Devstral Small (24B, Mistral, Apache 2.0)
- Writing and general language: Gemma 3 27B or Mistral Small 3.x 24B
- Embeddings for RAG: nomic-embed-text (small, stays resident)
- vLLM is not used: single user, and it lacks CPU offload for the 120B model. Revisit for multi-user or batch use.

## Approach
1. **Model as a swappable endpoint.** All services use `OPENAI_BASE_URL` and `MODEL_NAME` from `.env`. No hard-coded model names elsewhere.
2. **Placeholder LLM in the cloud.** Same serving stack (Ollama or llama.cpp) with a tiny US/EU model on CPU (Gemma 3 1B/4B, Llama 3.2 3B). Use gpt-oss-20b on CPU if the cloud RAM is 16 GB or more. A mock or LiteLLM server is acceptable for plumbing-only tests.
3. **Compose layout.**
   - `docker-compose.yml`: CPU-capable base with the model server, Open WebUI, SearXNG, and a vector store with a local embedding model.
   - `docker-compose.gpu.yml`: NVIDIA device reservation, `OLLAMA_CONTEXT_LENGTH` (32768 or higher), `OLLAMA_MAX_LOADED_MODELS=1`.
4. **Agent harness config.** OpenCode (or Aider) profiles: `ai-code` (Devstral Small), `ai-write` (Gemma 3 27B or Mistral Small), `ai-think` (gpt-oss-120b). Shell aliases launch each with its model and a web-on or web-off permission profile. Ollama swaps models on demand. Add MCP servers for filesystem, git, SearXNG and local RAG.
5. **Privacy hardening.** Bind to 127.0.0.1, disable telemetry (`DO_NOT_TRACK`, Open WebUI analytics off), run the agent in a sandboxed container with only the needed mounts, and keep a no-web profile for FERPA and research folders. Web search queries leave the machine, so keep sensitive details out of them.

## Files to create
- `docker-compose.yml`, `docker-compose.gpu.yml`, `.env.example`
- `searxng/settings.yml`
- `opencode.json` (or `.aider.conf.yml`) and `aliases.sh`
- `README.md` with the on-GPU finishing checklist

## Deferred to the GPU machine
NVIDIA Container Toolkit check, VRAM and KV-cache fit at the chosen context length, MoE offload flags for the 120B model, load times and tokens per second, and real tool-calling reliability.

## Verification
- In the cloud: `docker compose up` on CPU, a chat request through `/v1`, an agent task on a scratch directory, a SearXNG query, and a RAG query over sample docs.
- On the box: `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up`, pull gpt-oss-20b and Devstral Small, rerun the same checks, and time a model swap.
