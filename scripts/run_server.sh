#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")/.."

if /usr/sbin/lsof -nP -iTCP:8080 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Modern Community Topics server already running on port 8080."
  exit 0
fi

/usr/bin/python3 -m http.server 8080 --bind 0.0.0.0
