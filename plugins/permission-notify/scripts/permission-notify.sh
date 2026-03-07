#!/usr/bin/env bash
# Intelligent permission notification delay
# Usage: permission-notify.sh prompt | clear

STATE_DIR="$HOME/.claude/.perm-state"
WEBHOOK_URL=$(jq -r '.discord_webhooks.attention' "$HOME/.claude/tts-config.json" 2>/dev/null)
DEFAULT_DELAY=15
ACTIVE_DELAY=30
ACTIVE_WINDOW=60

if [[ -z "$WEBHOOK_URL" || "$WEBHOOK_URL" == "null" ]]; then
  echo "Error: Could not read attention webhook from ~/.claude/tts-config.json" >&2
  exit 1
fi

mkdir -p "$STATE_DIR"

kill_sleeper() {
  if [[ -f "$STATE_DIR/sleeper.pid" ]]; then
    local pid
    pid=$(<"$STATE_DIR/sleeper.pid")
    kill "$pid" 2>/dev/null
    rm -f "$STATE_DIR/sleeper.pid"
  fi
}

case "${1:-}" in
  prompt)
    # Kill any existing sleeper
    kill_sleeper

    # Determine delay based on recent activity
    delay=$DEFAULT_DELAY
    if [[ -f "$STATE_DIR/last-accept" ]]; then
      last=$(<"$STATE_DIR/last-accept")
      now=$(date +%s)
      elapsed=$(( now - last ))
      if (( elapsed < ACTIVE_WINDOW )); then
        delay=$ACTIVE_DELAY
      fi
    fi

    # Write marker with unique ID
    marker_id="$$-$(date +%s%N)"
    echo "$marker_id" > "$STATE_DIR/pending"

    # Fork background sleeper
    (
      sleep "$delay"
      # Check if our marker is still there
      if [[ -f "$STATE_DIR/pending" ]]; then
        current=$(<"$STATE_DIR/pending")
        if [[ "$current" == "$marker_id" ]]; then
          PROJECT=$(basename "$PWD")
          curl -s -H "Content-Type: application/json" \
            -d "{\"content\":\"Permission needed: $PROJECT\"}" \
            "$WEBHOOK_URL" >/dev/null 2>&1
          rm -f "$STATE_DIR/pending"
        fi
      fi
    ) &
    echo $! > "$STATE_DIR/sleeper.pid"
    ;;

  clear)
    # Remove pending marker
    rm -f "$STATE_DIR/pending"
    # Record acceptance timestamp
    date +%s > "$STATE_DIR/last-accept"
    # Kill pending sleeper
    kill_sleeper
    ;;

  *)
    echo "Usage: $0 {prompt|clear}" >&2
    exit 1
    ;;
esac
