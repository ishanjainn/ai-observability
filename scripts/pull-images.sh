#!/usr/bin/env bash
# Pull all third-party images used by the demo (for offline conference Wi‑Fi).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

IMAGES=(
  grafana/tempo:2.6.1
  prom/prometheus:v2.54.1
  otel/opentelemetry-collector-contrib:0.115.1
  grafana/grafana:11.4.0
  otel/ebpf-instrument:v0.9.0
)

for img in "$IMAGES"; do
  echo "Pulling $img"
  docker pull "$img"
done

echo "Building local agent images..."
docker compose build

echo "Done. Run scripts/export-images.sh to save tar archives."
