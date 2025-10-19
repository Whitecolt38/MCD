# srv/app.py
import os, uuid
import io
import boto3
from botocore.exceptions import ClientError
from fastapi.responses import StreamingResponse
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from worker import convert_task, download_task

app = FastAPI(title="Media Convert & Fetch")

SHARED_DIR = os.getenv("SHARED_DIR", "/shared") # volumen compartido entre api y worker

# Cliente interno de MinIO (solo para la API)
MINIO_URL  = os.getenv("MINIO_URL", "http://minio:9000")
MINIO_KEY  = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SEC  = os.getenv("MINIO_SECRET_KEY", "minio12345")
BUCKET     = os.getenv("MINIO_BUCKET", "jobs")

s3_client = boto3.client(
    "s3",
    endpoint_url=MINIO_URL,
    aws_access_key_id=MINIO_KEY,
    aws_secret_access_key=MINIO_SEC
)
# --- catálogos para clasificar por extensión (mismo criterio que frontend) ---
IMG_EXT = {"jpg","jpeg","png","webp","avif","bmp","tif","tiff","ico","psd","exr","jp2","heic","heif","gif","svg"}
VID_EXT = {"mp4","webm","mkv","mov","avi","m4v","mpeg","mpg","ts","3gp","3g2","ogv","flv"}
AUD_EXT = {"mp3","m4a","aac","opus","ogg","wav","flac"}

def classify_by_name(name: str) -> str:
    ext = (os.path.splitext(name)[1][1:] or "").lower()
    if ext in IMG_EXT: return "image"
    if ext in VID_EXT: return "video"
    if ext in AUD_EXT: return "audio"
    return "unknown"

# ====================== ENDPOINTS ======================

@app.post("/convert")
async def convert(file: UploadFile = File(...),
                  kind: str = Form(...),
                  target: str = Form(...)):
    # carpeta de trabajo dentro de /shared (visible por api y worker)
    jobdir = os.path.join(SHARED_DIR, uuid.uuid4().hex)
    os.makedirs(jobdir, exist_ok=True)

    suffix = os.path.splitext(file.filename)[1]
    inpath = os.path.join(jobdir, f"in{suffix}")
    with open(inpath, "wb") as f:
        f.write(await file.read())

    task = convert_task.delay(inpath, kind, target) # ruta absoluta en /shared
    return {"task_id": task.id}

@app.post("/api/convert/batch")
async def convert_batch(
    files: List[UploadFile] = File(...),
    kind: str = Form(...),  # "image" | "video" | "audio"
    target: str = Form(...), # extensión destino (jpg, mp4, etc.)
):
    if not files:
        raise HTTPException(status_code=400, detail="No se recibió ningún archivo")

    # Validación: todos del mismo tipo (por extensión de nombre)
    kinds = { classify_by_name(f.filename) for f in files }
    kinds.discard("unknown")
    if len(kinds) != 1 or kind not in kinds:
        raise HTTPException(status_code=400, detail="Todos los archivos deben ser del mismo tipo (imagen / video / audio)")

    # Guardar todos en un jobdir dentro de /shared
    jobdir = os.path.join(SHARED_DIR, uuid.uuid4().hex)
    os.makedirs(jobdir, exist_ok=True)

    tasks = []
    for f in files:
        # preserva nombre base
        inpath = os.path.join(jobdir, os.path.basename(f.filename))
        # asegura subdirs si vienen con webkitRelativePath
        os.makedirs(os.path.dirname(inpath), exist_ok=True)
        with open(inpath, "wb") as w:
            w.write(await f.read())
        # lanza una tarea por archivo
        t = convert_task.delay(inpath, kind, target)
        tasks.append({"name": os.path.basename(f.filename), "task_id": t.id})

    # no borramos jobdir: el worker leerá esos archivos y ya limpia lo suyo
    return {"tasks": tasks}

@app.post("/fetch")
async def fetch(url: str = Form(...),
                kind: str = Form(...),      # "video" | "audio"
                quality: str = Form(...)):  # "best" | "1080p"... o "256k"/"128k"
    task = download_task.delay(url, kind, quality)
    return {"task_id": task.id}

@app.get("/status/{task_id}")
def status(task_id: str):
    from worker import celery
    a = celery.AsyncResult(task_id)
    if a.successful():
        # *** CORRECCIÓN DE SEGURIDAD AQUÍ ***
        # El worker ahora devuelve 'file_key' en lugar de 'download_url'
        if "file_key" in a.result:
            # Construimos la URL de descarga segura usando el endpoint de la API
            file_key = a.result["file_key"]
            download_url = f"/api/download/{file_key}"
            # Devolvemos el resultado con la URL segura y la clave (opcional)
            return JSONResponse({"state": a.state, "result": {"download_url": download_url, "file_key": file_key}})
        
        # Caso por si el worker devuelve otro tipo de resultado (o el antiguo)
        return JSONResponse({"state": a.state, "result": a.result})
        
    return {"state": a.state, "info": str(a.info)}

# estáticos y raíz
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

# ====================== NUEVO ENDPOINT DE DESCARGA ======================

@app.get("/api/download/{key:path}")
async def download_file(key: str):
    """
    Descarga archivos desde MinIO vía API sin exponer la URL interna.
    key: la ruta relativa que devuelve la función 'upload' en worker.py
    """
    try:
        file_obj = io.BytesIO()
        s3_client.download_fileobj(BUCKET, key, file_obj)
        file_obj.seek(0)
        filename = key.split("/")[-1]
        return StreamingResponse(
            file_obj,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except ClientError:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
