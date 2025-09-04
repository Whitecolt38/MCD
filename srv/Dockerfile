FROM python:3.11-slim
ENV DEBIAN_FRONTEND=noninteractive

# Base: FFmpeg + ImageMagick + delegates principales
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        imagemagick \
        libvips-tools \
        libopenjp2-7 \
        libheif1 \
        libde265-0 \
        libaom3 \
        librsvg2-2 \
        librsvg2-bin \
        libjpeg62-turbo \
        libpng16-16 \
        libtiff6 \
        aria2 \
        curl \
        ca-certificates \
        git \
        yt-dlp && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Intento opcional de instalar plugins HEIF/AVIF para escritura en ImageMagick.
# Si no existen en tu repo, no pasa nada: seguirá adelante (|| true).
RUN apt-get update && \
    (apt-get install -y --no-install-recommends libheif-plugin-aom || true) && \
    (apt-get install -y --no-install-recommends libheif-plugin-x265 || true) && \
    (apt-get install -y --no-install-recommends libx265-206 || \
     apt-get install -y --no-install-recommends libx265-199 || true) && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8000"]

