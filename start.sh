#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"

DEFAULT_PYTHON="/Users/zhao/miniforge3/envs/blotguard-real/bin/python"
DEFAULT_NODE="/Users/zhao/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
BACKEND_PORT="${BLOTGUARD_PORT:-5001}"
FRONTEND_PORT="${BLOTGUARD_FRONTEND_PORT:-4200}"

validate_port() {
  local name="$1"
  local value="$2"
  if [[ ! "$value" =~ ^[0-9]+$ ]] || (( value < 1 || value > 65535 )); then
    echo "错误：$name 必须是 1 到 65535 之间的端口号。" >&2
    exit 1
  fi
}

validate_port "BLOTGUARD_PORT" "$BACKEND_PORT"
validate_port "BLOTGUARD_FRONTEND_PORT" "$FRONTEND_PORT"

if [[ -n "${BLOTGUARD_PYTHON:-}" ]]; then
  PYTHON_BIN="$BLOTGUARD_PYTHON"
elif [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
elif [[ -x "$DEFAULT_PYTHON" ]]; then
  PYTHON_BIN="$DEFAULT_PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
else
  echo "错误：未找到 Python，请先安装项目后端环境。" >&2
  exit 1
fi

if [[ -n "${BLOTGUARD_NODE:-}" ]]; then
  NODE_BIN="$BLOTGUARD_NODE"
elif command -v node >/dev/null 2>&1; then
  NODE_BIN="$(command -v node)"
elif [[ -x "$DEFAULT_NODE" ]]; then
  NODE_BIN="$DEFAULT_NODE"
else
  echo "错误：未找到 Node.js，请先安装 Node.js。" >&2
  exit 1
fi

ANGULAR_CLI="$FRONTEND_DIR/node_modules/@angular/cli/bin/ng.js"
if [[ ! -f "$ANGULAR_CLI" ]]; then
  echo "错误：前端依赖尚未安装。" >&2
  echo "请先进入 $FRONTEND_DIR 执行 npm ci。" >&2
  exit 1
fi

BACKEND_PID=""
FRONTEND_PID=""
PROXY_DIR=""
PROXY_CONFIG=""

stop_system() {
  trap - INT TERM EXIT
  echo
  echo "正在停止系统..."

  [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
  [[ -n "$BACKEND_PID" ]] && kill "$BACKEND_PID" 2>/dev/null || true

  [[ -n "$FRONTEND_PID" ]] && wait "$FRONTEND_PID" 2>/dev/null || true
  [[ -n "$BACKEND_PID" ]] && wait "$BACKEND_PID" 2>/dev/null || true
  [[ -n "$PROXY_CONFIG" ]] && rm -f "$PROXY_CONFIG"
  [[ -n "$PROXY_DIR" ]] && rmdir "$PROXY_DIR" 2>/dev/null || true
  echo "系统已停止。"
}

trap stop_system INT TERM EXIT

PROXY_DIR="$(mktemp -d "${TMPDIR:-/tmp}/blotguard-proxy.XXXXXX")"
PROXY_CONFIG="$PROXY_DIR/proxy.conf.json"
printf '{"/api":{"target":"http://127.0.0.1:%s","secure":false,"changeOrigin":true,"logLevel":"debug"}}\n' \
  "$BACKEND_PORT" > "$PROXY_CONFIG"

echo "正在启动 BlotGuard-AI..."
echo "后端：http://127.0.0.1:$BACKEND_PORT"
echo "前端：http://127.0.0.1:$FRONTEND_PORT"
echo "按 Control+C 可同时停止前后端。"
echo

(
  cd "$ROOT_DIR"
  BLOTGUARD_INFERENCE_MODE="${BLOTGUARD_INFERENCE_MODE:-real}" \
  BLOTGUARD_DEVICE="${BLOTGUARD_DEVICE:-auto}" \
  BLOTGUARD_PORT="$BACKEND_PORT" \
  PYTHONUNBUFFERED=1 \
    "$PYTHON_BIN" scripts/run_dev.py
) &
BACKEND_PID=$!

(
  cd "$FRONTEND_DIR"
  "$NODE_BIN" "$ANGULAR_CLI" serve \
    --host 127.0.0.1 \
    --port "$FRONTEND_PORT" \
    --proxy-config "$PROXY_CONFIG"
) &
FRONTEND_PID=$!

while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
  sleep 1
done

if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
  wait "$BACKEND_PID" || EXIT_CODE=$?
  echo "后端已退出（状态码 ${EXIT_CODE:-0}）。" >&2
else
  wait "$FRONTEND_PID" || EXIT_CODE=$?
  echo "前端已退出（状态码 ${EXIT_CODE:-0}）。" >&2
fi

exit "${EXIT_CODE:-1}"
