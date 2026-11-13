# Instructions for the Claude Code session

Read `PLAN.md` fully, then build everything under "Files to create" in this repo.

Rules:
- You are in a cloud sandbox without a GPU. Use the CPU placeholder model approach from PLAN.md (tiny US/EU model, never Qwen/DeepSeek/Kimi/GLM/MiniMax/Yi/InternLM).
- If Docker is unavailable in the sandbox, say so, validate with `docker compose config` or equivalent where possible, and test plumbing with a mock OpenAI-compatible server.
- No hard-coded model names outside `.env.example`.
- Bind all ports to 127.0.0.1 and disable telemetry.
- `README.md` must end with the on-GPU finishing checklist (the "Deferred to the GPU machine" section).
- Report honestly which verification steps passed, failed, or were skipped.
- Commit your work on a branch and push when finished.
