#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/jonog/ai_orchestrator"
UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"
cp "$ROOT/scripts/user-backup.service" "$UNIT_DIR/"
cp "$ROOT/scripts/user-backup.timer" "$UNIT_DIR/"

systemctl --user daemon-reload
systemctl --user enable --now user-backup.timer

echo "Installed user systemd timer. Current status:" 
systemctl --user list-timers --all | grep user-backup.timer || true
