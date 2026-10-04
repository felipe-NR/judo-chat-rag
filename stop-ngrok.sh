#!/usr/bin/env bash
# Para a API e o túnel ngrok iniciados por start-ngrok.sh.
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT_DIR/.ngrok"

stop_pid_file() {
  local name="$1" file="$2"
  if [ -f "$file" ]; then
    local pid
    pid=$(cat "$file")
    if kill -0 "$pid" 2>/dev/null; then
      # uv run inicia o uvicorn como filho; derruba o grupo inteiro.
      pkill -P "$pid" 2>/dev/null
      kill "$pid" 2>/dev/null
      echo "$name parado (PID $pid)."
    else
      echo "$name já não estava rodando (PID $pid)."
    fi
    rm -f "$file"
  else
    echo "$name: nenhum PID registrado."
  fi
}

stop_pid_file "ngrok" "$RUN_DIR/ngrok.pid"
stop_pid_file "API" "$RUN_DIR/api.pid"

rm -f "$RUN_DIR/public_url"

# Espera a porta liberar para que um start logo em seguida não a encontre ocupada.
PORT="${JUDO_CHAT_PORT:-8010}"
for i in $(seq 1 15); do
  if ! curl -s -o /dev/null "http://localhost:$PORT/"; then break; fi
  sleep 1
done
