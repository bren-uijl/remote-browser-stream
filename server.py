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

DISPLAY = os.environ.get("DISPLAY", ":99")
PORT = int(os.environ.get("PORT", 6080))
FPS = int(os.environ.get("FPS", 10))
QUALITY = int(os.environ.get("JPEG_QUALITY", 70))
RESOLUTION = os.environ.get("RESOLUTION", "1280x800")

clients = []
clients_lock = threading.Lock()
latest_frame = None
frame_lock = threading.Lock()

HTML = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Remote Browser 🦉</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { background: #111; display: flex; flex-direction: column; align-items: center; height: 100vh; }
    #toolbar {
      width: 100%; background: #222; padding: 8px 16px;
      display: flex; align-items: center; gap: 10px; color: #fff; font-family: sans-serif; font-size: 14px;
    }
    #toolbar input {
      flex: 1; padding: 5px 10px; border-radius: 4px; border: none;
      font-size: 14px; background: #333; color: #fff;
    }
    #toolbar button {
      padding: 5px 14px; border-radius: 4px; border: none;
      background: #4a90d9; color: #fff; cursor: pointer; font-size: 14px;
    }
    #screen { flex: 1; width: 100%; display: flex; justify-content: center; align-items: center; }
    #stream { max-width: 100%; max-height: 100%; cursor: crosshair; }
    #status { color: #888; font-size: 12px; font-family: sans-serif; }
  </style>
</head>
<body>
  <div id="toolbar">
    <span>🦉 Remote Browser</span>
    <input id="url" type="text" placeholder="Type a URL and press Enter..." onkeydown="navigate(event)">
    <button onclick="sendClick('refresh')">↻</button>
    <span id="status">streaming</span>
  </div>
  <div id="screen">
    <img id="stream" src="/stream" onclick="sendMouseClick(event)" alt="stream">
  </div>
  <script>
    function navigate(e) {
      if (e.key !== 'Enter') return;
      let url = document.getElementById('url').value;
      if (!url.startsWith('http')) url = 'https://' + url;
      fetch('/input?action=navigate&url=' + encodeURIComponent(url));
    }
    function sendMouseClick(e) {
      const img = document.getElementById('stream');
      const rect = img.getBoundingClientRect();
      const x = Math.round((e.clientX - rect.left) / rect.width * """ + RESOLUTION.split('x')[0] + """);
      const y = Math.round((e.clientY - rect.top) / rect.height * """ + RESOLUTION.split('x')[1] + """);
      fetch('/input?action=click&x=' + x + '&y=' + y);
    }
    function sendClick(action) {
      fetch('/input?action=' + action);
    }
    document.addEventListener('keydown', function(e) {
      fetch('/input?action=key&key=' + encodeURIComponent(e.key));
    });
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
    subprocess.run(["xdotool"] + args, env={"DISPLAY": DISPLAY}, timeout=3)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress access logs

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(HTML.encode())

        elif self.path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-cache")
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

        elif self.path.startswith("/input"):
            from urllib.parse import urlparse, parse_qs
            params = parse_qs(urlparse(self.path).query)
            action = params.get("action", [""])[0]

            try:
                if action == "click":
                    x = params.get("x", ["0"])[0]
                    y = params.get("y", ["0"])[0]
                    xdotool(["mousemove", "--sync", x, y, "click", "1"])
                elif action == "key":
                    key = params.get("key", [""])[0]
                    xdotool(["key", key])
                elif action == "navigate":
                    url = params.get("url", [""])[0]
                    xdotool(["key", "ctrl+l"])
                    time.sleep(0.2)
                    xdotool(["type", "--clearmodifiers", url])
                    time.sleep(0.1)
                    xdotool(["key", "Return"])
                elif action == "refresh":
                    xdotool(["key", "ctrl+r"])
            except Exception:
                pass

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    print(f"==> Starting frame capture at {FPS}fps...")
    t = threading.Thread(target=capture_frames, daemon=True)
    t.start()

    print(f"==> Starting HTTP server on port {PORT}...")
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"==> Vink🦉 — streaming on http://0.0.0.0:{PORT}")
    server.serve_forever()
