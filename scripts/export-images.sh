#!/usr/bin/env bash
# Export demo images to ./images/ for offline import at KubeCon.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OUT_DIR="${ROOT}/images"
mkdir -p "$OUT_DIR"

IMAGES=(
  grafana/tempo:2.6.1
  prom/prometheus:v2.54.1
  otel/opentelemetry-collector-contrib:0.115.1
  grafana/grafana:11.4.0
  otel/ebpf-instrument:v0.9.0
  ai-observability/agent-ebpf-only:local
  ai-observability/agent-openlit:local
)

docker compose build

for img in "$IMAGES"; do
  safe_name="$(echo "$img" | tr '/:' '__')"
  tar_path="${OUT_DIR}/${safe_name}.tar"
  echo "Saving $img -> $tar_path"
  docker save "$img" -o "$tar_path"
done

echo "Exported to $OUT_DIR"
