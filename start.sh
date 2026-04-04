#!/usr/bin/env bash
set -e

export DISPLAY=:99

# Find Chrome binary — don't fail if not found yet
CHROME_BIN="$(command -v google-chrome-stable || command -v google-chrome || echo "")"

echo "==> Cleaning up old processes..."
pkill -f "Xvfb :99" || true
pkill -f xfce4-session || true
pkill -f xfwm4 || true
pkill -f google-chrome || true
pkill -f server.py || true

sleep 1

echo "==> Starting virtual display..."
nohup Xvfb :99 -screen 0 1280x800x24 >/tmp/xvfb.log 2>&1 &
sleep 2

echo "==> Starting XFCE desktop..."
nohup startxfce4 >/tmp/xfce.log 2>&1 &
sleep 4

if [ -n "$CHROME_BIN" ]; then
    echo "==> Starting Google Chrome..."
    nohup "$CHROME_BIN" \
        --no-sandbox \
        --disable-dev-shm-usage \
        --disable-gpu \
        --window-size=1280,800 \
        --start-maximized \
        "https://example.com" \
        >/tmp/chrome.log 2>&1 &
    sleep 2
else
    echo "==> Warning: Chrome not found, skipping..."
fi

echo "==> Starting MJPEG stream server..."
python3 "$(dirname "$0")/server.py"
