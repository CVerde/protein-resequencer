#!/bin/bash

cd /home/pi/protein-resequencer || exit 1

# Arrêter les anciennes instances
pkill -f "python3 app.py" 2>/dev/null
pkill -f "chromium.*localhost:5000" 2>/dev/null
pkill -f "scripts/roon_album_watcher.js" 2>/dev/null
pkill -f "scripts/roon_daily_report.js" 2>/dev/null
pkill -f "scripts/roon_recent_additions_probe.js" 2>/dev/null
pkill -f "scripts/roon_daily_additions.js" 2>/dev/null

sleep 1

# Serveur Flask
python3 app.py &
SERVER_PID=$!

# Journal des écoutes Roon et impression quotidienne à minuit (échec non bloquant)
node scripts/roon_daily_report.js >> /tmp/protein-resequencer-roon-report.log 2>&1 &
node scripts/roon_daily_additions.js >> /tmp/protein-resequencer-roon-additions.log 2>&1 &

sleep 2

# Chromium kiosque sous Wayland
XDG_RUNTIME_DIR=/run/user/1000 \
WAYLAND_DISPLAY=wayland-0 \
chromium \
  --ozone-platform=wayland \
  --password-store=basic \
  --kiosk \
  --start-fullscreen \
  --touch-events=enabled \
  --disable-pinch \
  --noerrdialogs \
  --disable-session-crashed-bubble \
  --disable-restore-session-state \
  http://localhost:5000 &

wait $SERVER_PID
