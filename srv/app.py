import uuid, os, tempfile
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from worker import convert_task, download_task

app = FastAPI(title="Media Convert & Fetch")

# ==== CONVERSIÓN DE ARCHIVOS ====
@app.post("/convert")
async def convert(file: UploadFile = File(...),
                  kind: str = Form(...),       # "video" | "image" | "mesh"
                  target: str = Form(...)):    # ej: "webm" | "png" | "glb"
    suffix = os.path.splitext(file.filename)[1]
    tmpdir = tempfile.mkdtemp()
    inpath = os.path.join(tmpdir, f"in{suffix}")
    with open(inpath, "wb") as f:
        f.write(await file.read())
    task = convert_task.delay(inpath, kind, target)
    return {"task_id": task.id}

# ==== DESCARGA POR URL (video/audio) ====
@app.post("/fetch")
async def fetch(url: str = Form(...),
                kind: str = Form(...),      # "video" | "audio"
                quality: str = Form(...)):  # ver opciones en frontend
    task = download_task.delay(url, kind, quality)
    return {"task_id": task.id}

@app.get("/status/{task_id}")
def status(task_id: str):
    from worker import celery
    a = celery.AsyncResult(task_id)
    if a.successful():
        return JSONResponse({"state": a.state, "result": a.result})
    return {"state": a.state, "info": str(a.info)}

# estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")
@app.get("/")
async def root():
    return FileResponse("static/index.html")
