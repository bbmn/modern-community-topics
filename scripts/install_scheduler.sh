#!/bin/zsh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.akvfx.ak-news-briefing"
PLIST_SOURCE="$PROJECT_ROOT/launchd/$LABEL.plist"
PLIST_TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$HOME/Library/LaunchAgents"
sed "s#__PROJECT_ROOT__#$PROJECT_ROOT#g" "$PLIST_SOURCE" > "$PLIST_TARGET"
chmod +x "$PROJECT_ROOT/scripts/run_briefing.sh"

launchctl unload "$PLIST_TARGET" 2>/dev/null || true
launchctl load "$PLIST_TARGET"

echo "Installed $LABEL"
echo "Runs at 8:00 AM and 5:00 PM while you are logged in."
echo "Logs:"
echo "  $PROJECT_ROOT/data/scheduler.out.log"
echo "  $PROJECT_ROOT/data/scheduler.err.log"
