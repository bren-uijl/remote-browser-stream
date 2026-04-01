# 🦉 Remote Browser Stream

A full **Ubuntu XFCE desktop** with Google Chrome — streamed to your browser via **MJPEG over plain HTTP**. No WebSockets needed, works behind school firewalls and restrictive proxies.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/bren-uijl/remote-browser-stream)

---

## 🚀 Quick start

1. Click the button above — **Open in GitHub Codespaces**
2. Wait for the container to build (~3 minutes the first time)
3. Go to the **Ports** tab and click port **6080**
4. The desktop streams directly in your browser — no plugins needed

> 💡 Works on school networks too — no WebSockets required!

---

## 🧩 What's included?

| Component | Purpose |
|-----------|---------|
| `Xvfb` | Virtual display |
| `XFCE4` | Full Ubuntu desktop |
| `Google Chrome` | The browser you control |
| `ffmpeg` | Captures screen frames |
| `xdotool` | Handles mouse clicks and keyboard input |
| `server.py` | Serves the MJPEG stream over HTTP |

---

## ⚙️ Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `6080` | HTTP port to listen on |
| `FPS` | `10` | Frames per second |
| `JPEG_QUALITY` | `70` | JPEG quality (1-100) |
| `RESOLUTION` | `1280x800` | Screen resolution |

---

## 🛠️ Restart manually

```bash
./start.sh
```

---

## 🪲 Troubleshooting

| Problem | Solution |
|---------|----------|
| Black screen | Wait 5 seconds and refresh |
| Slow/laggy | Lower `FPS` or `JPEG_QUALITY` env var |
| Chrome won't start | Check `/tmp/chrome.log` |

---

*Built by **Vink🦉***
