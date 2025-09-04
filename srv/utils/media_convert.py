# srv/utils/media_convert.py
import os
import shlex
import subprocess
from pathlib import Path

IMAGE_EXTS = {"jpg","jpeg","png","bmp","tif","tiff","webp","heic","heif","avif","psd","exr","jp2","ico","gif"}
VIDEO_EXTS = {"mp4","webm","mkv","mov","avi","m4v","mpeg","mpg","ts","3gp","3g2","ogv","flv","gif"}  # gif animado

def _run(cmd: list[str]):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed:\n{' '.join(shlex.quote(c) for c in cmd)}\n\n{proc.stderr.strip()}"
        )
    return proc

# -------------------- IMAGEN (ImageMagick) --------------------
def _im_convert(src_path: str, dst_path: str, out_ext: str):
    out_ext = out_ext.lower()
    per_fmt = {
        "jpg":  ["-colorspace", "sRGB", "-strip", "-interlace", "Plane", "-quality", "90"],
        "jpeg": ["-colorspace", "sRGB", "-strip", "-interlace", "Plane", "-quality", "90"],
        "png":  ["-strip"],
        "bmp":  [],
        "tiff": [],
        "webp": ["-define", "webp:method=6", "-quality", "90"],
        "avif": ["-define", "heic:speed=4", "-quality", "50"],
        "heic": ["-quality", "90"],
        "heif": ["-quality", "90"],
        "jp2":  ["-quality", "35"],
        "psd":  [],
        "exr":  ["-colorspace", "RGB"],
        "ico":  ["(", src_path, "-resize", "16x16", ")",
                 "(", src_path, "-resize", "32x32", ")",
                 "(", src_path, "-resize", "48x48", ")",
                 "(", src_path, "-resize", "64x64", ")"],
        "gif":  []
    }
    args = per_fmt.get(out_ext, [])
    cmd = ["convert"] + ([src_path] if out_ext != "ico" else []) + args + [dst_path]
    _run(cmd)
    if not os.path.exists(dst_path) or os.path.getsize(dst_path) == 0:
        raise RuntimeError("Salida de imagen vacía o no creada")

# -------------------- VÍDEO (FFmpeg) --------------------
def _ffmpeg_convert(src_path: str, dst_path: str, out_ext: str):
    out_ext = out_ext.lower()
    PRESETS = {
        "mp4":  ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
                 "-c:a", "aac", "-b:a", "128k"],
        "m4v":  ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
                 "-c:a", "aac", "-b:a", "128k"],
        "mov":  ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
                 "-c:a", "aac", "-b:a", "160k"],
        "webm": ["-c:v", "libvpx-vp9", "-crf", "33", "-b:v", "0", "-row-mt", "1",
                 "-c:a", "libopus", "-b:a", "128k"],
        "mkv":  ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                 "-c:a", "aac", "-b:a", "160k"],
        "avi":  ["-c:v", "mpeg4", "-qscale:v", "4", "-c:a", "libmp3lame", "-b:a", "192k"],
        "mpeg": ["-c:v", "mpeg2video", "-qscale:v", "2", "-c:a", "mp2", "-b:a", "192k"],
        "mpg":  ["-c:v", "mpeg2video", "-qscale:v", "2", "-c:a", "mp2", "-b:a", "192k"],
        "ts":   ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                 "-c:a", "aac", "-b:a", "160k", "-muxrate", "6M", "-f", "mpegts"],
        "3gp":  ["-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-pix_fmt", "yuv420p",
                 "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:a", "aac", "-b:a", "96k"],
        "3g2":  ["-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-pix_fmt", "yuv420p",
                 "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:a", "aac", "-b:a", "96k"],
        "ogv":  ["-c:v", "libtheora", "-q:v", "7", "-c:a", "libvorbis", "-q:a", "4"],
        "flv":  ["-c:v", "flv1", "-qscale:v", "5", "-c:a", "libmp3lame", "-b:a", "128k"],
        "gif":  None,
    }
    if out_ext == "gif":
        palette = str(Path(dst_path).with_suffix(".palette.png"))
        _run(["ffmpeg", "-y", "-i", src_path,
              "-vf", "fps=12,scale=iw:-1:flags=lanczos,palettegen=reserve_transparent=1",
              palette])
        _run(["ffmpeg", "-y", "-i", src_path, "-i", palette,
              "-lavfi", "fps=12,scale=iw:-1:flags=lanczos [x]; [x][1:v] paletteuse",
              "-loop", "0", dst_path])
        try: os.remove(palette)
        except Exception: pass
        return

    opts = PRESETS.get(out_ext)
    if not opts:
        raise ValueError(f"Formato de vídeo no soportado: {out_ext}")

    cmd = ["ffmpeg", "-y", "-i", src_path] + opts + [dst_path]
    _run(cmd)
    if not os.path.exists(dst_path) or os.path.getsize(dst_path) == 0:
        raise RuntimeError("Salida de vídeo vacía o no creada")

# -------------------- API ÚNICA --------------------
def media_convert(src_path: str, out_ext: str) -> str:
    out_ext = out_ext.lower()
    dst_path = str(Path(src_path).with_suffix("." + out_ext))
    if out_ext in IMAGE_EXTS:
        _im_convert(src_path, dst_path, out_ext)
    elif out_ext in VIDEO_EXTS:
        _ffmpeg_convert(src_path, dst_path, out_ext)
    else:
        raise ValueError(f"Extensión de salida no soportada: {out_ext}")
    return dst_path