#!/usr/bin/env bash
# Import previously exported images from ./images/
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT}/images"

if [[ ! -d "$OUT_DIR" ]]; then
  echo "No images/ directory. Run scripts/export-images.sh first."
  exit 1
fi

for tar in "$OUT_DIR"/*.tar; do
  echo "Loading $tar"
  docker load -i "$tar"
done

echo "Import complete."
