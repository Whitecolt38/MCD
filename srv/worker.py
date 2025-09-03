import os, uuid, shutil, tempfile, subprocess
from celery import Celery
import boto3
from urllib.parse import urlparse

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

# ====== Utils ======
def run(cmd: str) -> str:
    p = subprocess.run(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, timeout=TASK_TIMEOUT_SECS
    )
    if p.returncode != 0:
        raise RuntimeError(f"cmd failed ({p.returncode}) -> {cmd}\n--- LOG ---\n{p.stdout}")
    return p.stdout

def upload(path: str) -> str:
    key = f"{uuid.uuid4().hex}/{os.path.basename(path)}"
    s3.upload_file(path, BUCKET, key)
    url = s3.generate_presigned_url(
        "get_object", Params={"Bucket": BUCKET, "Key": key}, ExpiresIn=21600
    )
    if PUBLIC_URL:
        ep = urlparse(MINIO_URL)
        url = url.replace(f"{ep.scheme}://{ep.netloc}", PUBLIC_URL)
    return url

# ====== Tasks ======
@celery.task(bind=True)
def convert_task(self, input_path: str, kind: str, target: str):
    tmpdir = tempfile.mkdtemp()
    try:
        base = os.path.splitext(os.path.basename(input_path))[0]
        t = target.lower()
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
            if t in ("jpg", "jpeg"):
                cmd_vips = f'vips copy "{input_path}" "{out}"[Q=82]'
                IM = "magick" if shutil.which("magick") else "convert"
                cmd_im = f'{IM} "{input_path}" -auto-orient -strip -quality 82 "{out}"'
            elif t == "png":
                cmd_vips = f'vips copy "{input_path}" "{out}"[compression=9]'
                IM = "magick" if shutil.which("magick") else "convert"
                cmd_im = f'{IM} "{input_path}" -auto-orient -strip -define png:compression-level=9 "{out}"'
            elif t == "webp":
                cmd_vips = f'vips copy "{input_path}" "{out}"[Q=82]'
                IM = "magick" if shutil.which("magick") else "convert"
                cmd_im = f'{IM} "{input_path}" -auto-orient -strip -quality 82 "{out}"'
            elif t == "avif":
                cmd_vips = f'vips copy "{input_path}" "{out}"[Q=60,effort=5]'
                IM = "magick" if shutil.which("magick") else "convert"
                cmd_im = f'{IM} "{input_path}" -auto-orient -strip -quality 60 "{out}"'
            else:
                raise ValueError("formato de imagen no soportado")
            try:
                log = run(cmd_vips)
            except Exception as e_vips:
                try:
                    log = f"[vips failed]\n{e_vips}\n\n[trying ImageMagick]\n" + run(cmd_im)
                except Exception as e_im:
                    raise RuntimeError(f"Imagen: falló vips e ImageMagick:\n{e_vips}\n\n{e_im}")

        elif kind == "mesh":
            assimp_map = {
                "obj":"obj","stl":"stl","ply":"ply","plyb":"plyb","fbx":"fbx",
                "3ds":"3ds","dae":"collada","x":"x","off":"off",
                "gltf":"gltf2","glb":"glb2",
            }
            if t == "3mf":
                # Export fiable con FreeCAD headless (si está instalado)
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
            if quality == "best":
                fmt = 'bv*+ba/best'
            else:
                # ej: "720p" -> 720
                h = ''.join(ch for ch in quality if ch.isdigit()) or "720"
                fmt = f'bestvideo[height<={h}]+bestaudio/best[height<={h}]'
            cmd = f'yt-dlp -f "{fmt}" -o "{out_tmpl}" --no-playlist "{url}"'

        elif kind == "audio":
            # usamos extracción a mp3; --audio-quality usa escala VBR 0(mejor)-9
            if quality == "best":
                aq = "0"; ppa = ""
            elif quality == "256k":
                aq = "0"; ppa = '--postprocessor-args "-b:a 256k"'
            elif quality == "128k":
                aq = "5"; ppa = '--postprocessor-args "-b:a 128k"'
            else:
                aq = "0"; ppa = ""
            cmd = (
                f'yt-dlp -f "bestaudio/best" -x --audio-format mp3 --audio-quality {aq} '
                f'{ppa} -o "{out_tmpl}" --no-playlist "{url}"'
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
