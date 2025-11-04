FROM python:3.11-slim
ENV DEBIAN_FRONTEND=noninteractive

# Base: FFmpeg + ImageMagick + delegados principales
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
        git && \
    # Instalación opcional de plugins HEIF/AVIF
    apt-get install -y --no-install-recommends libheif-plugin-aom || true && \
    apt-get install -y --no-install-recommends libheif-plugin-x265 || true && \
    apt-get install -y --no-install-recommends libx265-206 || \
    apt-get install -y --no-install-recommends libx265-199 || true && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Verificación de FFmpeg
RUN which ffmpeg || (echo "ERROR: FFmpeg no se encontró en el PATH. La construcción fallará." && exit 1)

WORKDIR /app

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt yt-dlp

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]