#!/bin/zsh
# Starts the VoiceStudio backend headless (no app window) on 127.0.0.1:3900.
# Usage: scripts/voicestudio_server.sh [start|stop|status]
RUNTIME="$HOME/Library/Application Support/VoiceStudio/runtime/project"
PORT="${VOICESTUDIO_PORT:-3900}"
MLX_PORT="${MLX_TTS_PORT:-3901}"
HERE="$(cd "$(dirname "$0")" && pwd)"
LOG="${VOICESTUDIO_LOG:-$HOME/Library/Logs/voicestudio-headless.log}"

healthy() { curl -s -m 2 "http://127.0.0.1:$PORT/health" | grep -q '"status":"ok"'; }
mlx_healthy() { curl -s -m 2 "http://127.0.0.1:$MLX_PORT/health" | grep -q '"status":"ok"'; }

case "${1:-start}" in
  status) healthy && echo "up" || { echo "down"; exit 1; } ;;
  stop)
    pkill -f "uvicorn main:app --app-dir backend --host 127.0.0.1 --port $PORT"
    pkill -f "engines/voxcpm2_subprocess/main.py"
    pkill -f "scripts/mlx_tts_server.py"
    echo stopped ;;
  start)
    if ! mlx_healthy; then  # fast narration server (model stays loaded between lines)
      nohup "$RUNTIME/.venv/bin/python" "$HERE/mlx_tts_server.py" "$MLX_PORT" >>"$LOG" 2>&1 &
    fi
    healthy && { for i in $(seq 1 90); do mlx_healthy && { echo "already up"; exit 0; }; sleep 2; done; echo "mlx server did not start, see $LOG"; exit 1; }
    [ -x "$RUNTIME/.venv/bin/python" ] || { echo "VoiceStudio runtime missing: install with 'brew install --cask debpalash/tap/voicestudio' and open it once"; exit 2; }
    cd "$RUNTIME" || exit 2
    mkdir -p "$(dirname "$LOG")"
    nohup "$RUNTIME/.venv/bin/python" -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port "$PORT" >>"$LOG" 2>&1 &
    for i in $(seq 1 120); do healthy && mlx_healthy && { echo "up"; exit 0; }; sleep 2; done
    echo "backend did not become healthy, see $LOG"; exit 1 ;;
esac
