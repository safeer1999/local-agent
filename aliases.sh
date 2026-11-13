# source this file:  source /path/to/local-agent/aliases.sh
# Launches OpenCode in a sandboxed container with only the current directory
# mounted at /workspace. Models come from .env (no names hard-coded here).
LOCAL_AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
LOCAL_AGENT_IMAGE="${LOCAL_AGENT_IMAGE:-local-agent-opencode:latest}"

_la_build() {
  docker image inspect "$LOCAL_AGENT_IMAGE" >/dev/null 2>&1 && return 0
  docker build -q -t "$LOCAL_AGENT_IMAGE" -f - "$LOCAL_AGENT_DIR" <<'EOF'
FROM node:22-slim
RUN apt-get update && apt-get install -y --no-install-recommends git python3 python3-pip pipx ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && pip3 install --break-system-packages chromadb-client requests \
 && npm i -g opencode-ai
ENV PATH="/root/.local/bin:${PATH}" OPENCODE_DISABLE_AUTOUPDATE=1 DO_NOT_TRACK=1
RUN pipx install mcp-server-git
EOF
}

# usage: _la_run <agent> <web:on|off>
_la_run() {
  local agent="$1" web="$2"; shift 2
  _la_build || return 1
  local envfile="$LOCAL_AGENT_DIR/.env"
  [ -f "$envfile" ] || envfile="$LOCAL_AGENT_DIR/.env.example"
  local overlay='{}'
  if [ "$web" = off ]; then
    overlay='{"permission":{"webfetch":"deny"},"mcp":{"searxng":{"enabled":false}}}'
  fi
  # --network host: the stack's ports are bound to 127.0.0.1 on the host.
  docker run --rm -it --network host \
    --env-file "$envfile" \
    -e OPENCODE_CONFIG=/opt/local-agent/opencode.json \
    -e OPENCODE_DISABLE_MODELS_FETCH=1 -e OPENCODE_DISABLE_LSP_DOWNLOAD=1 \
    -e OPENCODE_CONFIG_CONTENT="$overlay" \
    -v "$LOCAL_AGENT_DIR:/opt/local-agent:ro" \
    -v "$PWD:/workspace" -w /workspace \
    --cap-drop ALL --security-opt no-new-privileges \
    "$LOCAL_AGENT_IMAGE" opencode --agent "$agent" "$@"
}

alias ai-code='_la_run ai-code on'
alias ai-write='_la_run ai-write on'
alias ai-think='_la_run ai-think on'
# FERPA / research folders: no web search, no web fetch.
alias ai-code-private='_la_run ai-code off'
alias ai-write-private='_la_run ai-write off'
alias ai-think-private='_la_run ai-think off'
