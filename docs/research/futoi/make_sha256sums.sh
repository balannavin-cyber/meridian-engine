#!/bin/sh
# Final deliverable: SHA256SUMS over docs/research/futoi/.
# Excludes SHA256SUMS itself (it cannot contain its own digest) and the logs
# directory, whose names carry run timestamps. Paths are recorded relative to
# docs/research/futoi/ so the manifest is checkable with:
#     cd docs/research/futoi && sha256sum -c SHA256SUMS
set -eu
cd "$(dirname "$0")"
find . -type f \
     ! -name SHA256SUMS \
     ! -path './logs/*' \
     ! -path './__pycache__/*' \
     ! -name '*.pyc' \
     ! -name '*.tmp' \
     ! -name '*.missing' \
  | LC_ALL=C sort \
  | xargs sha256sum > SHA256SUMS
echo "files hashed: $(wc -l < SHA256SUMS)"
echo "logs/ excluded: $(find ./logs -type f | wc -l) files (run-timestamped names)"
