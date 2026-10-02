#!/usr/bin/env bash
# h3_serve.sh start|stop|status — lifecycle of the MiniMax-H3 sglang server (fl2va, also serves t2va).
# Rule: start right before an H3 batch, stop as soon as the batch is done (the GPUs are shared).
# Env: H3_MODEL (weights dir), H3_ENV (conda env with sglang, default minimax-h3), H3_GPUS (default 0,1,2,3), H3_PORT (30010).
set -u
MODEL=${H3_MODEL:?set H3_MODEL to the MiniMax-H3 weights dir}; ENVN=${H3_ENV:-minimax-h3}; GPUS=${H3_GPUS:-0,1,2,3}; PORT=${H3_PORT:-30010}
RUN=${H3_RUN:-$HOME/.h3_serve}; mkdir -p "$RUN"; PIDF=$RUN/pid; LOG=$RUN/serve.log
alive(){ [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; }
healthy(){ curl -s -m 3 "localhost:$PORT/health" | grep -q ok; }
case "${1:-status}" in
start)
  if healthy; then echo "already healthy on :$PORT"; exit 0; fi
  n=$(echo "$GPUS" | tr ',' '\n' | wc -l)
  for g in ${GPUS//,/ }; do u=$(nvidia-smi -i "$g" --query-gpu=memory.used --format=csv,noheader,nounits); [ "$u" -lt 2000 ] || { echo "GPU $g busy (${u} MiB) — pick free GPUs via H3_GPUS"; exit 1; }; done
  source "$(conda info --base)/etc/profile.d/conda.sh" && conda activate "$ENVN"
  CUDA_VISIBLE_DEVICES=$GPUS PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True setsid nohup \
    sglang serve --model-path "$MODEL" --model-variant fl2va --num-gpus "$n" --ulysses-degree "$n" \
    --performance-mode speed --host 0.0.0.0 --port "$PORT" --text-encoder-cpu-offload --vae-tiling \
    </dev/null >"$LOG" 2>&1 &
  echo $! >"$PIDF"; echo "started pid $(cat "$PIDF"), waiting for health (weights load ~12 min)…"
  for i in $(seq 1 120); do healthy && { echo "healthy after $((i*10))s"; exit 0; }; alive || { echo "server died; tail:"; tail -20 "$LOG"; exit 1; }; sleep 10; done
  echo "not healthy after 20 min; see $LOG"; exit 1 ;;
stop)
  pid=$( [ -f "$PIDF" ] && cat "$PIDF" ); [ -n "$pid" ] || pid=$(pgrep -u "$USER" -f '^[^ ]*python[^ ]* [^ ]*/sglang serve' | head -1)
  [ -n "$pid" ] || { echo "no H3 server running"; exit 0; }
  kill -TERM "$pid"; for i in $(seq 1 30); do kill -0 "$pid" 2>/dev/null || break; sleep 2; done
  kill -0 "$pid" 2>/dev/null && { echo "pid $pid still alive after 60 s — check before escalating (never kill -9 CUDA procs blindly)"; exit 1; }
  rm -f "$PIDF"; sleep 5; nvidia-smi --query-gpu=index,memory.used --format=csv,noheader; echo stopped ;;
status) healthy && echo "healthy on :$PORT" || echo "not running/healthy"; alive && echo "pid $(cat "$PIDF")" ;;
esac
