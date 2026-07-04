#!/bin/zsh
set -euo pipefail

LABEL="com.akvfx.ak-news-briefing"
PLIST_TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl unload "$PLIST_TARGET" 2>/dev/null || true
rm -f "$PLIST_TARGET"

echo "Uninstalled $LABEL"
