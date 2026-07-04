#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")/.."
/usr/bin/python3 scripts/fetch_news.py --days 3 --limit-per-section 8
