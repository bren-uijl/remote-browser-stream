#!/usr/bin/env python3
"""
MJPEG stream server — streams the virtual display over plain HTTP.
No WebSockets needed. Works behind restrictive firewalls/proxies.
"""

import subprocess
import threading
import time
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

DISPLAY = os.environ.get("DISPLAY", ":99")
PORT = int(os.environ.get("PORT", 6080))
FPS = int(os.environ.get("FPS", 10))
QUALITY = int(os.environ.get("JPEG_QUALITY", 70))
RESOLUTION = os.environ.get("RESOLUTION", "1280x800")
RES_W, RES_H = RESOLUTION.split("x")

latest_frame = None
frame_lock = threading.Lock()

HTML = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Remote Browser 🦉</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ background: #111; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }}
    #toolbar {{
      width: 100%; background: #222; padding: 8px 16px;
      display: flex; align-items: center; gap: 10px; color: #fff; font-family: sans-serif; font-size: 14px;
      flex-shrink: 0;
    }}
    #toolbar input {{
      flex: 1; padding: 5px 10px; border-radius: 4px; border: none;
      font-size: 14px; background: #333; color: #fff;
    }}
    #toolbar button {{
      padding: 5px 14px; border-radius: 4px; border: none;
      background: #4a90d9; color: #fff; cursor: pointer; font-size: 14px;
    }}
    #screen {{ flex: 1; display: flex; justify-content: center; align-items: center; overflow: hidden; }}
    #stream {{ max-width: 100%; max-height: 100%; cursor: crosshair; display: block; }}
    #status {{ color: #888; font-size: 12px; white-space: nowrap; }}
  </style>
</head>
<body>
  <div id="toolbar">
    <span>🦉</span>
    <input id="url" type="text" placeholder="Type a URL and press Enter...">
    <button id="gobtn">Go</button>
    <button onclick="sendAction('refresh')">↻</button>
    <span id="status">connecting...</span>
  </div>
  <div id="screen">
    <img id="stream" src="/stream" alt="stream">
  </div>
  <script>
    const img = document.getElementById('stream');
    const status = document.getElementById('status');
    const urlInput = document.getElementById('url');

    img.onload = () => status.textContent = 'streaming';
    img.onerror = () => {{ status.textContent = 'reconnecting...'; setTimeout(() => img.src = '/stream?' + Date.now(), 2000); }};

    function sendAction(action, params) {{
      const q = new URLSearchParams({{ action, ...params }});
      fetch('/input?' + q);
    }}

    urlInput.addEventListener('keydown', e => {{
      if (e.key !== 'Enter') return;
      let url = urlInput.value;
      if (!url.startsWith('http')) url = 'https://' + url;
      sendAction('navigate', {{ url }});
    }});

    document.getElementById('gobtn').onclick = () => urlInput.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter' }}));

    img.addEventListener('click', e => {{
      const rect = img.getBoundingClientRect();
      const x = Math.round((e.clientX - rect.left) / rect.width * {RES_W});
      const y = Math.round((e.clientY - rect.top) / rect.height * {RES_H});
      sendAction('click', {{ x, y }});
      img.focus();
    }});

    // Keyboard: type printable chars, use key for special keys
    document.addEventListener('keydown', e => {{
      if (document.activeElement === urlInput) return;
      if (e.key.length === 1) {{
        sendAction('type', {{ char: e.key }});
      }} else {{
        sendAction('key', {{ key: e.key }});
      }}
    }});
  </script>
</body>
</html>"""


def capture_frames():
    global latest_frame
    interval = 1.0 / FPS
    while True:
        try:
            result = subprocess.run([
                "ffmpeg", "-y",
                "-f", "x11grab",
                "-video_size", RESOLUTION,
                "-i", DISPLAY,
                "-vframes", "1",
                "-f", "image2",
                "-vcodec", "mjpeg",
                "-q:v", str(max(1, min(31, 32 - QUALITY // 3))),
                "pipe:1"
            ], capture_output=True, timeout=2)
            if result.returncode == 0 and result.stdout:
                with frame_lock:
                    latest_frame = result.stdout
        except Exception:
            pass
        time.sleep(interval)


def xdotool(args):
    env = {**os.environ, "DISPLAY": DISPLAY}
    subprocess.run(["xdotool"] + args, env=env, timeout=3, capture_output=True)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress access logs

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/" or path == "":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode())

        elif path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")

        elif path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()
            try:
                while True:
                    with frame_lock:
                        frame = latest_frame
                    if frame:
                        self.wfile.write(b"--frame\r\n")
                        self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                        self.wfile.write(frame)
                        self.wfile.write(b"\r\n")
                    time.sleep(1.0 / FPS)
            except Exception:
                pass

        elif path == "/input":
            params = parse_qs(urlparse(self.path).query)
            action = params.get("action", [""])[0]

            try:
                if action == "click":
                    x = params.get("x", ["0"])[0]
                    y = params.get("y", ["0"])[0]
                    xdotool(["mousemove", "--sync", x, y, "click", "1"])
                elif action == "type":
                    # Single printable character
                    char = params.get("char", [""])[0]
                    if char:
                        xdotool(["type", "--clearmodifiers", char])
                elif action == "key":
                    # Special key (Enter, Backspace, ctrl+l, etc.)
                    key = params.get("key", [""])[0]
                    key_map = {
                        "Enter": "Return",
                        "Backspace": "BackSpace",
                        "ArrowLeft": "Left",
                        "ArrowRight": "Right",
                        "ArrowUp": "Up",
                        "ArrowDown": "Down",
                        "Escape": "Escape",
                        "Tab": "Tab",
                        "Delete": "Delete",
                    }
                    xdotool_key = key_map.get(key, key)
                    xdotool(["key", xdotool_key])
                elif action == "navigate":
                    url = params.get("url", [""])[0]
                    xdotool(["key", "ctrl+l"])
                    time.sleep(0.3)
                    xdotool(["type", "--clearmodifiers", url])
                    time.sleep(0.1)
                    xdotool(["key", "Return"])
                elif action == "refresh":
                    xdotool(["key", "ctrl+r"])
            except Exception:
                pass

            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")

        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    print(f"==> Starting frame capture at {FPS}fps ({RESOLUTION})...")
    t = threading.Thread(target=capture_frames, daemon=True)
    t.start()

    print(f"==> Starting HTTP server on port {PORT}...")
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"==> Vinkbot🦉 — streaming on http://0.0.0.0:{PORT}")
    server.serve_forever()
