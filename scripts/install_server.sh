#!/bin/zsh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.akvfx.ak-news-server"
PLIST_SOURCE="$PROJECT_ROOT/launchd/$LABEL.plist"
PLIST_TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$HOME/Library/LaunchAgents"
sed "s#__PROJECT_ROOT__#$PROJECT_ROOT#g" "$PLIST_SOURCE" > "$PLIST_TARGET"
chmod +x "$PROJECT_ROOT/scripts/run_server.sh"

launchctl unload "$PLIST_TARGET" 2>/dev/null || true
launchctl load "$PLIST_TARGET"

echo "Installed $LABEL"
echo "Serves Modern Community Topics at:"
echo "  http://localhost:8080/web/"
echo "On your Wi-Fi network, use your Mac IP address instead of localhost."
echo "Logs:"
echo "  $PROJECT_ROOT/data/server.out.log"
echo "  $PROJECT_ROOT/data/server.err.log"
