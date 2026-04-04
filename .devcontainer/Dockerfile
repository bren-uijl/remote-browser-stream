FROM mcr.microsoft.com/devcontainers/base:ubuntu

ENV DEBIAN_FRONTEND=noninteractive

# Install desktop, VNC and stream dependencies
RUN apt-get update && apt-get install -y \
    xvfb \
    xfce4 \
    xfce4-terminal \
    xfce4-goodies \
    xterm \
    ffmpeg \
    xdotool \
    x11-utils \
    python3 \
    wget \
    curl \
    ca-certificates \
    fonts-liberation \
    libnss3 \
    libxss1 \
    libasound2t64 \
    libgbm1 \
    dbus-x11 \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome (also pulls in libatk and other deps automatically)
RUN wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y /tmp/chrome.deb \
    && rm /tmp/chrome.deb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN chmod +x start.sh

CMD ["/bin/bash", "start.sh"]
