# srv/app.py
import os, uuid, tempfile
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from worker import convert_task, download_task

app = FastAPI(title="Media Convert & Fetch")

SHARED_DIR = os.getenv("SHARED_DIR", "/shared")  # << volumen compartido

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

    task = convert_task.delay(inpath, kind, target)  # pasamos ruta absoluta en /shared
    return {"task_id": task.id}

@app.post("/fetch")
async def fetch(url: str = Form(...),
                kind: str = Form(...),      # "video" | "audio"
                quality: str = Form(...)):  # "best" | "1080p" ... o "256k"/"128k"
    task = download_task.delay(url, kind, quality)
    return {"task_id": task.id}

@app.get("/status/{task_id}")
def status(task_id: str):
    from worker import celery
    a = celery.AsyncResult(task_id)
    if a.successful():
        return JSONResponse({"state": a.state, "result": a.result})
    return {"state": a.state, "info": str(a.info)}

app.mount("/static", StaticFiles(directory="static"), name="static")
@app.get("/")
async def root():
    return FileResponse("static/index.html")
