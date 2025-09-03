FROM python:3.11-slim
ENV DEBIAN_FRONTEND=noninteractive

# Solo lo esencial. Quitamos freecad.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg imagemagick libvips-tools \
    libjpeg62-turbo libpng16-16 libwebp7 libheif1 \
    assimp-utils \
    aria2 curl ca-certificates \
 && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

# yt-dlp
RUN pip install --no-cache-dir yt-dlp

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
