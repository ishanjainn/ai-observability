#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Create .env from .env.example and set OPENAI_API_KEY"
  exit 1
fi

# Startup order is handled by compose depends_on:
#   collector (healthy) -> agents (healthy) -> obi
# OBI starts last so it attaches to the live agent process immediately.
docker compose up -d --build

# Confirm OBI actually attached to the ebpf-only agent (GenAI spans depend on it).
echo "Waiting for OBI to attach to agent-ebpf-only..."
attached=false
for _ in $(seq 1 18); do
  if docker compose logs obi 2>&1 | grep -q 'instrumenting process.*service=agent-ebpf-only'; then
    attached=true
    break
  fi
  sleep 5
done

if [[ "$attached" == true ]]; then
  echo "OBI attached to agent-ebpf-only."
  # eBPF TLS capture can miss the very first request on a freshly-attached process.
  # Fire a couple of throwaway prompts so the presenter's first real prompt is captured.
  if [[ -n "${OPENAI_API_KEY:-}" ]] || grep -q '^OPENAI_API_KEY=' .env 2>/dev/null; then
    echo "Warming up OBI GenAI capture..."
    for _ in 1 2; do
      curl -s -X POST http://localhost:8080/api/chat \
        -H 'Content-Type: application/json' \
        -d '{"message":"warmup","history":[]}' >/dev/null 2>&1 || true
      sleep 1
    done
  fi
else
  echo "WARNING: OBI has not attached to agent-ebpf-only yet. Check:"
  echo "  docker compose logs obi | grep instrumenting"
fi

echo ""
echo "Demo is up. Endpoints:"
echo "  Grafana:           http://localhost:3000  (admin / admin)"
echo "  Agent (OBI/eBPF):  http://localhost:8080"
echo "  Agent (OpenLIT):   http://localhost:8081"
echo "  Prometheus:        http://localhost:9090"
echo "  Tempo:             http://localhost:3200"
