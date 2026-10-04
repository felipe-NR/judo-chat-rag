#!/usr/bin/env bash
# Sobe a API (uvicorn, porta 8010) e expõe via ngrok para a página do GitHub Pages.
# Uso: ./start-ngrok.sh   Parar: ./stop-ngrok.sh
# Adaptado de paladare/delivery-platform/start-ngrok-dev.sh. A conta ngrok gratuita tem um
# domínio fixo e um túnel por vez: pare o túnel de outro projeto antes de subir este.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT_DIR/.ngrok"
PORT="${JUDO_CHAT_PORT:-8010}"

mkdir -p "$RUN_DIR"

for name in api ngrok; do
  if [ -f "$RUN_DIR/$name.pid" ] && kill -0 "$(cat "$RUN_DIR/$name.pid")" 2>/dev/null; then
    echo "$name já está rodando (PID $(cat "$RUN_DIR/$name.pid")). Rode ./stop-ngrok.sh primeiro." >&2
    exit 1
  fi
done
if pgrep -x ngrok >/dev/null 2>&1; then
  echo "Já existe um ngrok rodando nesta máquina (outro projeto?). Pare-o antes." >&2
  exit 1
fi

command -v ngrok >/dev/null 2>&1 || { echo "ngrok não encontrado no PATH." >&2; exit 1; }
if [ ! -f "$ROOT_DIR/.env" ] || ! grep -q '^ANTHROPIC_API_KEY=.\+' "$ROOT_DIR/.env"; then
  echo "Preencha ANTHROPIC_API_KEY em .env (veja .env.example)." >&2
  exit 1
fi

# Sem esta checagem, outro serviço na mesma porta responderia ao teste de prontidão abaixo
# e o túnel exporia esse serviço em vez da API.
if curl -s -o /dev/null "http://localhost:$PORT/"; then
  echo "A porta $PORT já está em uso por outro processo. Use JUDO_CHAT_PORT=<porta> ./start-ngrok.sh" >&2
  exit 1
fi

echo "Subindo a API na porta $PORT..."
cd "$ROOT_DIR"
set -a; source "$ROOT_DIR/.env"; set +a
nohup uv run uvicorn judo_chat.main:app --port "$PORT" > "$RUN_DIR/api.log" 2>&1 &
echo $! > "$RUN_DIR/api.pid"

for i in $(seq 1 60); do
  if curl -s -o /dev/null "http://localhost:$PORT/"; then break; fi
  sleep 1
done
if ! curl -s -o /dev/null "http://localhost:$PORT/"; then
  echo "A API não respondeu em $PORT a tempo. Veja $RUN_DIR/api.log" >&2
  exit 1
fi

echo "Subindo túnel ngrok..."
nohup ngrok http "$PORT" --log stdout > "$RUN_DIR/ngrok.log" 2>&1 &
echo $! > "$RUN_DIR/ngrok.pid"

PUBLIC_URL=""
for i in $(seq 1 30); do
  PUBLIC_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null \
    | grep -o '"public_url":"https://[^"]*"' | head -1 | cut -d'"' -f4) || true
  if [ -n "$PUBLIC_URL" ]; then break; fi
  sleep 1
done

if [ -z "$PUBLIC_URL" ]; then
  echo "ngrok não retornou URL pública a tempo. Veja $RUN_DIR/ngrok.log" >&2
  exit 1
fi

echo "$PUBLIC_URL" > "$RUN_DIR/public_url"
echo ""
echo "API pública em:        $PUBLIC_URL"
echo "Página (GitHub Pages): https://felipe-nr.github.io/judo-chat-rag/"
echo "Painel local do ngrok: http://localhost:4040"
echo "Logs: $RUN_DIR/api.log, $RUN_DIR/ngrok.log"
echo "Parar: ./stop-ngrok.sh"
