import os, uuid, shutil, tempfile, subprocess
from celery import Celery
import boto3
from urllib.parse import urlparse
from botocore.exceptions import ClientError  # 👈 añadido

# ====== Config ======
REDIS_URL  = os.getenv("REDIS_URL", "redis://redis:6379/0")
MINIO_URL  = os.getenv("MINIO_URL", "http://minio:9000")
MINIO_KEY  = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SEC  = os.getenv("MINIO_SECRET_KEY", "minio12345")
BUCKET     = os.getenv("MINIO_BUCKET", "jobs")
PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL")      # ej: http://TU_IP:9000
TASK_TIMEOUT_SECS = int(os.getenv("TASK_TIMEOUT_SECS", "900"))  # 15 min

# ====== Celery & S3 ======
celery = Celery("worker", broker=REDIS_URL, backend=REDIS_URL)
s3 = boto3.client(
    "s3",
    endpoint_url=MINIO_URL,
    aws_access_key_id=MINIO_KEY,
    aws_secret_access_key=MINIO_SEC,
)

# ====== Ensure bucket ======
def ensure_bucket():
    try:
        s3.head_bucket(Bucket=BUCKET)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code in ("404", "NoSuchBucket", "NotFound"):
            s3.create_bucket(Bucket=BUCKET)
        else:
            raise

# ====== Utils ======
# ====== Helpers IM/FFmpeg para imágenes ======
def _im_bin():
    # En Debian IM7 trae "magick"; en otros, "convert"
    return "magick" if shutil.which("magick") else "convert"

def convert_image_im(input_path: str, out_path: str, ext: str):
    """Conversión con ImageMagick para todos los formatos de imagen."""
    IM = _im_bin()
    t = ext.lower()

    # Argumentos por formato
    per_fmt = {
        "jpg":  ["-auto-orient", "-strip", "-colorspace", "sRGB", "-interlace", "Plane", "-quality", "90"],
        "jpeg": ["-auto-orient", "-strip", "-colorspace", "sRGB", "-interlace", "Plane", "-quality", "90"],
        "png":  ["-auto-orient", "-strip", "-define", "png:compression-level=9"],
        "bmp":  ["-auto-orient"],
        "tiff": ["-auto-orient"],
        "webp": ["-auto-orient", "-strip", "-define", "webp:method=6", "-quality", "90"],
        "avif": ["-auto-orient", "-strip", "-define", "heic:speed=4", "-quality", "50"],
        "heic": ["-auto-orient", "-strip", "-quality", "90"],
        "heif": ["-auto-orient", "-strip", "-quality", "90"],
        "jp2":  ["-auto-orient", "-strip", "-quality", "35"],
        "psd":  ["-auto-orient"],
        "exr":  ["-auto-orient", "-colorspace", "RGB"],  # evita perfiles raros
        "gif":  ["-auto-orient"],                        # imagen estática
        # ico lo tratamos aparte (multi-res)
    }

    if t == "ico":
        # ICO multi-tamaño: 16/32/48/64
        cmd = (
            f'{IM} '
            f'( "{input_path}" -resize 16x16 ) '
            f'( "{input_path}" -resize 32x32 ) '
            f'( "{input_path}" -resize 48x48 ) '
            f'( "{input_path}" -resize 64x64 ) '
            f'"{out_path}"'
        )
    else:
        args = " ".join(per_fmt.get(t, []))
        cmd = f'{IM} "{input_path}" {args} "{out_path}"'

    run(cmd)

def run(cmd: str) -> str:
    """Ejecuta comando y devuelve salida; lanza excepción si RC != 0."""
    p = subprocess.run(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, timeout=TASK_TIMEOUT_SECS
    )
    if p.returncode != 0:
        raise RuntimeError(f"cmd failed ({p.returncode}) -> {cmd}\n--- LOG ---\n{p.stdout}")
    return p.stdout

def upload(path: str) -> str:
    ensure_bucket()
    key = f"{uuid.uuid4().hex}/{os.path.basename(path)}"
    s3.upload_file(path, BUCKET, key)
    url = s3.generate_presigned_url(
        "get_object", Params={"Bucket": BUCKET, "Key": key}, ExpiresIn=21600
    )
    if PUBLIC_URL:
        ep = urlparse(MINIO_URL)
        url = url.replace(f"{ep.scheme}://{ep.netloc}", PUBLIC_URL)
    return url

# ====== Tareas ======
@celery.task(bind=True)
def convert_task(self, input_path: str, kind: str, target: str):
    tmpdir = tempfile.mkdtemp()
    try:
        base = os.path.splitext(os.path.basename(input_path))[0]
        # Normaliza el formato de salida (quita espacios, pasa a minúsculas y resuelve alias)
        t_raw = (target or "").strip().lower()
        ALIASES = {
            "jpeg": "jpg",
            "tif":  "tiff",
        }
        t = ALIASES.get(t_raw, t_raw)
        out = os.path.join(tmpdir, f"{base}.{t}")

        if kind == "video":
            enc = {
                "mp4":  '-c:v libx264 -preset veryfast -crf 23 -c:a aac -b:a 128k',
                "m4v":  '-c:v libx264 -preset veryfast -crf 23 -c:a aac -b:a 128k',
                "mov":  '-c:v libx264 -preset veryfast -crf 23 -c:a aac -b:a 160k',
                "webm": '-c:v libvpx-vp9 -b:v 0 -crf 30 -c:a libopus',
                "mkv":  '-c:v libx264 -preset veryfast -crf 23 -c:a aac -b:a 128k',
                "avi":  '-c:v mpeg4 -qscale:v 5 -c:a libmp3lame -q:a 4',
                "mpeg": '-c:v mpeg2video -qscale:v 4 -c:a mp2 -b:a 192k',
                "mpg":  '-c:v mpeg2video -qscale:v 4 -c:a mp2 -b:a 192k',
                "ts":   '-c:v libx264 -preset veryfast -crf 23 -c:a aac -bsf:v h264_mp4toannexb -f mpegts',
                "3gp":  '-c:v libx264 -profile:v baseline -level 3.0 -vf scale=w=640:h=-2 -c:a aac -b:a 96k',
                "3g2":  '-c:v libx264 -profile:v baseline -level 3.0 -vf scale=w=640:h=-2 -c:a aac -b:a 96k',
                "ogv":  '-c:v libtheora -q:v 7 -c:a libvorbis -q:a 5',
                "flv":  '-c:v flv -q:v 7 -c:a libmp3lame -q:a 4'
            }
            if t == "gif":
                palette = os.path.join(tmpdir, "palette.png")
                _ = run(f'ffmpeg -y -i "{input_path}" -vf "fps=12,scale=iw:-1:flags=lanczos,palettegen" "{palette}"')
                cmd = f'ffmpeg -y -i "{input_path}" -i "{palette}" -lavfi "fps=12,scale=iw:-1:flags=lanczos [x]; [x][1:v] paletteuse" -loop 0 "{out}"'
            elif t in enc:
                cmd = f'ffmpeg -y -i "{input_path}" {enc[t]} "{out}"'
            else:
                raise ValueError("formato de video no soportado")
            log = run(cmd)

        elif kind == "image":
            # Formatos que intentamos primero con VIPS por rendimiento
            vips_ok = {"jpg", "jpeg", "png", "webp", "avif"}

            if t in vips_ok:
                IM = _im_bin()
                if t in ("jpg", "jpeg"):
                    cmd_vips = f'vips copy "{input_path}" "{out}"[Q=82]'
                    cmd_im   = f'{IM} "{input_path}" -auto-orient -strip -colorspace sRGB -interlace Plane -quality 82 "{out}"'
                elif t == "png":
                    cmd_vips = f'vips copy "{input_path}" "{out}"[compression=9]'
                    cmd_im   = f'{IM} "{input_path}" -auto-orient -strip -define png:compression-level=9 "{out}"'
                elif t == "webp":
                    cmd_vips = f'vips copy "{input_path}" "{out}"[Q=82]'
                    cmd_im   = f'{IM} "{input_path}" -auto-orient -strip -define webp:method=6 -quality 82 "{out}"'
                elif t == "avif":
                    cmd_vips = f'vips copy "{input_path}" "{out}"[Q=60,effort=5]'
                    cmd_im   = f'{IM} "{input_path}" -auto-orient -strip -define heic:speed=4 -quality 60 "{out}"'
                else:
                    raise ValueError("formato de imagen no soportado")

                # VIPS primero; si falla, fallback a ImageMagick
                try:
                    log = run(cmd_vips)
                except Exception as e_vips:
                    try:
                        log = f"[vips failed]\n{e_vips}\n\n[trying ImageMagick]\n" + run(cmd_im)
                    except Exception as e_im:
                        raise RuntimeError(f"Imagen: falló vips e ImageMagick:\n{e_vips}\n\n{e_im}")

            # Resto de formatos (IM directo)
            elif t in {"bmp", "tiff", "ico", "psd", "exr", "jp2", "heic", "heif", "gif"}:
                convert_image_im(input_path, out, t)
                log = f"ImageMagick -> {t}"

            # SVG como salida no tiene sentido (vector real). Solo usar SVG como entrada.
            elif t == "svg":
                raise ValueError("SVG como salida no soportado (solo entrada).")

            else:
                raise ValueError("formato de imagen no soportado")


        elif kind == "mesh":
            assimp_map = {
                "obj":"obj","stl":"stl","ply":"ply","plyb":"plyb","fbx":"fbx",
                "3ds":"3ds","dae":"collada","x":"x","off":"off",
                "gltf":"gltf2","glb":"glb2",
            }
            if t == "3mf":
                fc_script = os.path.join(tmpdir, "export_3mf.py")
                with open(fc_script, "w") as fcs:
                    fcs.write(f"""
import Mesh, FreeCAD as App
doc = App.newDocument()
m = Mesh.Mesh()
m.read(r"{input_path}")
obj = doc.addObject("Mesh::Feature","Mesh")
obj.Mesh = m
doc.recompute()
Mesh.export([obj], r"{out}")
print("OK")
""")
                cmd = f'freecadcmd "{fc_script}"'
                log = run(cmd)
            elif t in assimp_map:
                cmd = f'assimp export "{input_path}" "{out}" -f {assimp_map[t]}'
                log = run(cmd)
            elif t in ("blend","step","iges","dxf","dwg"):
                raise ValueError("BLEND/STEP/IGES/DXF/DWG requieren Blender/FreeCAD/ODA (pendiente).")
            else:
                raise ValueError("formato 3D no soportado")
        else:
            raise ValueError("kind inválido")

        url = upload(out)
        return {"download_url": url, "log": log}
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
        try:
            os.remove(input_path)
        except Exception:
            pass

# ====== Descargas evitando HLS (m3u8) ======
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
BASE_YTDLP = f'yt-dlp --no-playlist -N 4 -R 10 --retry-sleep 1 --user-agent "{UA}"'

@celery.task(bind=True)
def download_task(self, url: str, kind: str, quality: str):
    """
    kind: "video" | "audio"
    quality:
      - video: "best", "1080p", "720p", "480p", "360p"
      - audio: "best", "256k", "128k"
    """
    tmpdir = tempfile.mkdtemp()
    try:
        if not any(url.startswith(p) for p in ("http://", "https://")):
            raise ValueError("URL no válida")

        out_tmpl = f'{tmpdir}/%(title).70s.%(ext)s'

        if kind == "video":
            # Evitar HLS (m3u8) y preferir MP4/M4A
            if quality == "best":
                fmt = 'bv*[protocol!=m3u8][ext=mp4]+ba[protocol!=m3u8][ext=m4a]/bv*[protocol!=m3u8]+ba/best'
            else:
                h = ''.join(ch for ch in quality if ch.isdigit()) or "720"
                fmt = f'bv*[height<={h}][protocol!=m3u8][ext=mp4]+ba[protocol!=m3u8][ext=m4a]/best[height<={h}]'
            cmd = (
                f'{BASE_YTDLP} -f "{fmt}" '
                f'--merge-output-format mp4 '
                f'-o "{out_tmpl}" "{url}"'
            )

        elif kind == "audio":
            # Preferir M4A y evitar HLS; exportar MP3 con calidad solicitada
            fmt = 'ba[protocol!=m3u8][ext=m4a]/bestaudio'
            if quality == "best":
                aq = "0"; ppa = ""
            elif quality == "256k":
                aq = "0"; ppa = '--postprocessor-args "-b:a 256k"'
            elif quality == "128k":
                aq = "5"; ppa = '--postprocessor-args "-b:a 128k"'
            else:
                aq = "0"; ppa = ""
            cmd = (
                f'{BASE_YTDLP} -f "{fmt}" -x --audio-format mp3 --audio-quality {aq} '
                f'{ppa} -o "{out_tmpl}" "{url}"'
            )

        else:
            raise ValueError("kind inválido (usa 'video' o 'audio')")

        log = run(cmd)

        files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir)]
        if not files:
            raise RuntimeError("No se generó ningún archivo")

        url_out = upload(files[0])
        return {"download_url": url_out, "log": log}

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)