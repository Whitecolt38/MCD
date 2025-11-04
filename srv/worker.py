import os, uuid, shutil, tempfile, subprocess 
from celery import Celery 
import boto3 
# from urllib.parse import urlparse # Ya no se necesita 
from botocore.exceptions import ClientError 
from typing import List 
import re 
import glob # Se añade para buscar el archivo final de yt-dlp 

# ====== Config ====== 
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0") 
MINIO_URL = os.getenv("MINIO_URL", "http://minio:9000") 
MINIO_KEY = os.getenv("MINIO_ACCESS_KEY", "minio") 
MINIO_SEC = os.getenv("MINIO_SECRET_KEY", "minio12345") 
BUCKET = os.getenv("MINIO_BUCKET", "jobs") 
# PUBLIC_URL ya no se usa, porque la descarga es via API 
TASK_TIMEOUT_SECS = int(os.getenv("TASK_TIMEOUT_SECS", "900")) # 15 min 

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

# ====== Utils: Versión SEGURA de run ====== 
def run(cmd: List[str]) -> str: 
    """Ejecuta comando (lista de argumentos) y devuelve salida. Evita shell=True.""" 
    # shell=False es el valor por defecto y es seguro 
    p = subprocess.run( 
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
        text=True, timeout=TASK_TIMEOUT_SECS 
    ) 
    if p.returncode != 0: 
        # Mostramos el comando tal cual para el log 
        raise RuntimeError(f"cmd failed ({p.returncode}) -> {' '.join(cmd)}\n--- LOG ---\n{p.stdout}") 
    return p.stdout 

# ====== Dependencias ====== 
def check_dependencies(): 
    """ 
    Verifica que las dependencias externas críticas (como FFmpeg) estén disponibles. 
    FFmpeg es necesario para fusionar audio y video descargados por yt-dlp. 
    """ 
    if not shutil.which("ffmpeg"): 
        # En caso de que falle, el log de error será muy claro 
        raise EnvironmentError( 
            "La dependencia FFmpeg no está instalada o no está en el PATH. " 
            "FFmpeg es OBLIGATORIO para fusionar streams de video/audio en 'download_task'." 
        ) 

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
        "jpg": ["-auto-orient", "-strip", "-colorspace", "sRGB", "-interlace", "Plane", "-quality", "90"], 
        "jpeg": ["-auto-orient", "-strip", "-colorspace", "sRGB", "-interlace", "Plane", "-quality", "90"], 
        "png": ["-auto-orient", "-strip", "-define", "png:compression-level=9"], 
        "bmp": ["-auto-orient"], 
        "tiff": ["-auto-orient"], 
        "webp": ["-auto-orient", "-strip", "-define", "webp:method=6", "-quality", "90"], 
        "avif": ["-auto-orient", "-strip", "-define", "heic:speed=4", "-quality", "50"], 
        "heic": ["-auto-orient", "-strip", "-quality", "90"], 
        "heif": ["-auto-orient", "-strip", "-quality", "90"], 
        "jp2": ["-auto-orient", "-strip", "-quality", "35"], 
        "psd": ["-auto-orient"], 
        "exr": ["-auto-orient", "-colorspace", "RGB"], 
        "gif": ["-auto-orient"], 
    } 

    if t == "ico": 
        # EXCEPCIÓN CONTROLADA para ICO, usando shell=True solo aquí 
        cmd_shell = ( 
            f'{IM} ' 
            f'( "{input_path}" -resize 16x16 ) ' 
            f'( "{input_path}" -resize 32x32 ) ' 
            f'( "{input_path}" -resize 48x48 ) ' 
            f'( "{input_path}" -resize 64x64 ) ' 
            f'"{out_path}"' 
        ) 
        p = subprocess.run( 
            cmd_shell, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
            text=True, timeout=TASK_TIMEOUT_SECS 
        ) 
        if p.returncode != 0: 
            raise RuntimeError(f"cmd failed ({p.returncode}) -> {cmd_shell}\n--- LOG ---\n{p.stdout}") 

    else: 
        args_list = per_fmt.get(t, []) 
        # Pasamos como lista: [IM, arg1, arg2, input_path, out_path] 
        cmd = [IM] + args_list + [input_path, out_path] 
        run(cmd) 

# Versión segura de upload: solo devuelve la clave, ahora con sanitización del nombre. 
def upload(path: str) -> str: 
    ensure_bucket() 
    # 1. Obtener el nombre original del archivo 
    filename = os.path.basename(path) 
    
    # 2. Sanear el nombre del archivo para que sea seguro en MinIO/S3 y URLs. 
    # Reemplazar caracteres que NO son alfanuméricos, ni guiones bajos, ni puntos, ni guiones por "_". 
    safe_filename = re.sub(r'[^\w\.\-\_]', '_', filename) 
    
    # 3. Construir la clave usando el nombre sanitizado 
    key = f"{uuid.uuid4().hex}/{safe_filename}" 
    
    s3.upload_file(path, BUCKET, key) 
    # Ya NO se genera ni se devuelve la URL pre-firmada. 
    return key 

# ====== Tareas ====== 
@celery.task(bind=True) 
def convert_task(self, input_path: str, kind: str, target: str): 
    tmpdir = tempfile.mkdtemp() 
    try: 
        base = os.path.splitext(os.path.basename(input_path))[0] 
        t_raw = (target or "").strip().lower() 
        ALIASES = { 
            "jpeg": "jpg", 
            "tif": "tiff", 
        } 
        t = ALIASES.get(t_raw, t_raw) 
        out = os.path.join(tmpdir, f"{base}.{t}") 
        log = "" # Inicializamos el log 

        if kind == "video": 
            enc_str = { 
                "mp4": '-c:v libx264 -preset veryfast -crf 23 -c:a aac -b:a 128k', 
                "m4v": '-c:v libx264 -preset veryfast -crf 23 -c:a aac -b:a 128k', 
                "mov": '-c:v libx264 -preset veryfast -crf 23 -c:a aac -b:a 160k', 
                "webm": '-c:v libvpx-vp9 -b:v 0 -crf 30 -c:a libopus', 
                "mkv": '-c:v libx264 -preset veryfast -crf 23 -c:a aac -b:a 128k', 
                "avi": '-c:v mpeg4 -qscale:v 5 -c:a libmp3lame -q:a 4', 
                "mpeg": '-c:v mpeg2video -qscale:v 4 -c:a mp2 -b:a 192k', 
                "mpg": '-c:v mpeg2video -qscale:v 4 -c:a mp2 -b:a 192k', 
                "ts":  '-c:v libx264 -preset veryfast -crf 23 -c:a aac -bsf:v h264_mp4toannexb -f mpegts', 
                "3gp": '-c:v libx264 -profile:v baseline -level 3.0 -vf scale=w=640:h=-2 -c:a aac -b:a 96k', 
                "3g2": '-c:v libx264 -profile:v baseline -level 3.0 -vf scale=w=640:h=-2 -c:a aac -b:a 96k', 
                "ogv": '-c:v libtheora -q:v 7 -c:a libvorbis -q:a 5', 
                "flv": '-c:v flv -q:v 7 -c:a libmp3lame -q:a 4' 
            } 

            if t == "gif": 
                palette = os.path.join(tmpdir, "palette.png") 
                
                # Comando 1: generar paleta (lista de argumentos) 
                cmd1 = ["ffmpeg", "-y", "-i", input_path, "-vf", "fps=12,scale=iw:-1:flags=lanczos,palettegen", palette] 
                run(cmd1) 

                # Comando 2: convertir (lista de argumentos) 
                cmd2 = ["ffmpeg", "-y", "-i", input_path, "-i", palette, "-lavfi", "fps=12,scale=iw:-1:flags=lanczos [x]; [x][1:v] paletteuse", "-loop", "0", out] 
                log = run(cmd2) 
                
            elif t in enc_str: 
                # Convertimos la cadena de opciones en una lista 
                enc_list = enc_str[t].split() 
                
                # Comando: [ffmpeg, -y, -i, input_path, opciones..., out] 
                cmd = ["ffmpeg", "-y", "-i", input_path] + enc_list + [out] 
                log = run(cmd) 
            else: 
                raise ValueError("formato de video no soportado") 

        elif kind == "image": 
            vips_ok = {"jpg", "jpeg", "png", "webp", "avif"} 
            IM = _im_bin() 

            if t in vips_ok: 
                
                # VIPS 
                if t in ("jpg", "jpeg"): 
                    cmd_vips = ["vips", "copy", input_path, f"{out}[Q=82]"] 
                    cmd_im  = [IM, input_path, "-auto-orient", "-strip", "-colorspace", "sRGB", "-interlace", "Plane", "-quality", "82", out] 
                elif t == "png": 
                    cmd_vips = ["vips", "copy", input_path, f"{out}[compression=9]"] 
                    cmd_im  = [IM, input_path, "-auto-orient", "-strip", "-define", "png:compression-level=9", out] 
                elif t == "webp": 
                    cmd_vips = ["vips", "copy", input_path, f"{out}[Q=82]"] 
                    cmd_im  = [IM, input_path, "-auto-orient", "-strip", "-define", "webp:method=6", "-quality", "82", out] 
                elif t == "avif": 
                    cmd_vips = ["vips", "copy", input_path, f"{out}[Q=60,effort=5]"] 
                    cmd_im  = [IM, input_path, "-auto-orient", "-strip", "-define", "heic:speed=4", "-quality", "60", out] 
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
                convert_image_im(input_path, out, t) # esta función llama a run 

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
                # Este caso sigue requiriendo ejecución de script de Python, 
                # que es más seguro que shell injection. 
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
                cmd = ["freecadcmd", fc_script] # MODO SEGURO 
                log = run(cmd) 
            elif t in assimp_map: 
                # MODO SEGURO 
                cmd = ["assimp", "export", input_path, out, "-f", assimp_map[t]] 
                log = run(cmd) 
            elif t in ("blend","step","iges","dxf","dwg"): 
                raise ValueError("BLEND/STEP/IGES/DXF/DWG requieren Blender/FreeCAD/ODA (pendiente).") 
            else: 
                raise ValueError("formato 3D no soportado") 
        else: 
            raise ValueError("kind inválido") 

        file_key = upload(out) # Ahora devuelve la clave 
        return {"file_key": file_key, "log": log} # Cambiamos 'download_url' por 'file_key' 
    finally: 
        shutil.rmtree(tmpdir, ignore_errors=True) 
        try: 
            os.remove(input_path) 
        except Exception: 
            pass 

# --- 
# ## Funciones de Descarga (yt-dlp) 
# --- 

# ====== Descargas evitando HLS (m3u8) ====== 
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36' 
# BASE_YTDLP ahora se maneja como lista de argumentos 
BASE_YTDLP_ARGS = ['yt-dlp', '--no-playlist', '-N', '4', '-R', '10', '--retry-sleep', '1', '--user-agent', UA] 

@celery.task(bind=True) 
def download_task(self, url: str, kind: str, quality: str): 
    tmpdir = tempfile.mkdtemp() 
    try: 
        # 1. VERIFICAR DEPENDENCIAS CRÍTICAS 
        check_dependencies() 

        if not any(url.startswith(p) for p in ("http://", "https://")): 
            raise ValueError("URL no válida") 

        # yt-dlp guarda el archivo final sin extensión .part si la descarga fue exitosa 
        out_tmpl = f'{tmpdir}/%(title).70s.%(ext)s' 
        
        args = [] 
        if kind == "video": 
            if quality == "best": 
                # Si es 'best', queremos la mejor calidad, que siempre requiere fusión (video+audio) 
                fmt = 'bestvideo[protocol!=m3u8][ext=mp4]+bestaudio[protocol!=m3u8][ext=m4a]/best' 
            else: 
                # Si es una calidad específica (ej. 720p), buscamos ese video + el mejor audio 
                h = ''.join(ch for ch in quality if ch.isdigit()) or "720" 
                # Intentar buscar la mejor resolución disponible sin m3u8 para ese límite de altura (h) 
                fmt = f'bestvideo[height<={h}][protocol!=m3u8][ext=mp4]+bestaudio[protocol!=m3u8][ext=m4a]/best[height<={h}]' 
            
            args = ( 
                BASE_YTDLP_ARGS + 
                ['-f', fmt] + 
                # CAMBIO 1: --recode-video fuerza fusión y post-procesamiento. 
                ['--recode-video', 'mp4'] + 
                # CAMBIO 3: Argumentos del post-procesador unidos 
                ['--postprocessor-args', '-strict -2'] + 
                # CAMBIO 2: -o y out_tmpl se unen para evitar interpretación como URL 
                [f'-o{out_tmpl}', url] 
            ) 

        elif kind == "audio": 
            fmt = 'ba[protocol!=m3u8][ext=m4a]/bestaudio' 
            if quality == "best": 
                aq = "0"; ppa = [] 
            elif quality == "256k": 
                aq = "0"; ppa = ['--postprocessor-args', '-b:a 256k'] 
            elif quality == "128k": 
                aq = "5"; ppa = ['--postprocessor-args', '-b:a 128k'] 
            else: 
                aq = "0"; ppa = [] 
                
            args = ( 
                BASE_YTDLP_ARGS + 
                ['-f', fmt] + 
                # Se usa --extract-audio para obtener solo audio y convertirlo a mp3 
                ['--extract-audio', '--audio-format', 'mp3', '--audio-quality', aq] + 
                ppa + 
                # CAMBIO 2: -o y out_tmpl se unen para evitar interpretación como URL 
                [f'-o{out_tmpl}', url] 
            ) 

        else: 
            raise ValueError("kind inválido (usa 'video' o 'audio')") 
            
        log = run(args) 

        # Buscar el archivo final. Buscamos cualquier archivo que no sea un archivo temporal (.part) 
        # o un archivo generado por yt-dlp para archivos separados. 
        files = glob.glob(os.path.join(tmpdir, "*")) 
        
        # Filtramos archivos temporales o de streams separados (.f***) 
        final_files = [f for f in files if not (f.endswith('.part') or re.search(r'\.f\d+\.', f))] 
        
        if not final_files: 
            raise RuntimeError(f"No se generó el archivo de salida final después de la descarga/fusión. Log de yt-dlp:\n{log}") 

        file_key = upload(final_files[0]) # Usamos el primer archivo encontrado 
        return {"file_key": file_key, "log": log} 

    finally: 
        shutil.rmtree(tmpdir, ignore_errors=True) 
        # No se elimina input_path aquí porque esta tarea no lo usa (es una descarga) 
# ==================================================================== 
# ====== Tarea de Limpieza (Debe ir al final de worker.py) ====== 
# ==================================================================== 

@celery.task 
def clean_up_file(file_key: str): 
    """ 
    Elimina un archivo (objeto) de MinIO usando su clave (key). 
    
    file_key es el identificador único devuelto por la función upload(). 
    """ 
    if not file_key: 
        print("clean_up_file: Clave de archivo vacía, saltando.") 
        return 

    try: 
        # La función delete_object necesita el Bucket y la Key. 
        s3.delete_object(Bucket=BUCKET, Key=file_key) 
        print(f"🗑️ Archivo de MinIO eliminado: {BUCKET}/{file_key}") 
    except ClientError as e: 
        # 404/NoSuchKey indica que el archivo ya no existe, lo cual está bien. 
        code = e.response.get("Error", {}).get("Code") 
        if code in ("404", "NoSuchKey"): 
            print(f"clean_up_file: El archivo {file_key} ya no existe, ignorando.") 
        else: 
            # Re-lanzamos cualquier otro error grave. 
            raise 
    except Exception as e: 
        print(f"clean_up_file: Error desconocido al intentar eliminar {file_key}: {e}") 