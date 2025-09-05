// static/app.js

// ===== Utilidades generales =====
const $ = (s) => document.querySelector(s);

// Navegación entre vistas (expuestas en window porque las llama el HTML)
window.showSection = function showSection(which) {
  $("#menu")?.classList.add("hidden");
  $("#convertSection")?.classList.add("hidden");
  $("#downloaderSection")?.classList.add("hidden");

  if (which === "convert") {
    $("#convertSection")?.classList.remove("hidden");
  }
  if (which === "downloader") {
    $("#downloaderSection")?.classList.remove("hidden");
    if (typeof window.fillQuality === "function") window.fillQuality();
    const url = $("#urlInput");
    if (url) url.focus();
  }

  if (typeof window.resetForms === "function") window.resetForms();
};

window.backToMenu = function backToMenu() {
  if (typeof window.resetForms === "function") window.resetForms();
  $("#convertSection")?.classList.add("hidden");
  $("#downloaderSection")?.classList.add("hidden");
  $("#menu")?.classList.remove("hidden");
};

// ===== Catálogos (coinciden con tu HTML) =====
const MAP = {
  image: {
    exts: [
      "jpg","jpeg","png","webp","gif","bmp","tif","tiff",
      "heic","heif","ico","svg","avif","psd","exr","jp2",
      "jfi","jif","jfif","jpe"
    ],
    targets: ["jpg","png","webp","avif","gif","bmp","tiff","ico","svg","heic","heif","psd","exr","jp2"],
  },
  video: {
    exts: ["mp4","mov","mkv","avi","webm","m4v","mpeg","mpg","ts","3gp","3g2","ogv","flv"],
    targets: ["mp4","webm","mkv","mov","avi","m4v","mpeg","mpg","ts","3gp","3g2","ogv","flv","gif"],
  },
  mesh: {
    exts: ["stl","obj","glb","gltf","fbx","ply","3ds","dae","off","x","3mf","plyb"],
    targets: ["glb","gltf","obj","stl","ply","plyb","fbx","3mf","3ds","dae","x","off"],
  },
};

// Sets para detección de carpeta
const IMG_EXT = new Set(["jpg","jpeg","png","webp","avif","bmp","tif","tiff","ico","psd","exr","jp2","heic","heif","gif","svg"]);
const VID_EXT = new Set(["mp4","webm","mkv","mov","avi","m4v","mpeg","mpg","ts","3gp","3g2","ogv","flv"]);
const AUD_EXT = new Set(["mp3","m4a","aac","opus","ogg","wav","flac"]);

const getExt = (n) => (n.includes(".") ? n.split(".").pop().toLowerCase() : "");
const kindOfExt = (ext) => {
  if (IMG_EXT.has(ext)) return "image";
  if (VID_EXT.has(ext)) return "video";
  if (AUD_EXT.has(ext)) return "audio";
  return null;
};
const detectKindByExt = (ext) => {
  for (const k of Object.keys(MAP)) if (MAP[k].exts.includes(ext)) return k;
  return null;
};

// ===== Referencias DOM (convertidor) =====
const fileInput   = $("#file");
const fileBadge   = $("#fileBadge");
const optionsBox  = $("#options");
const targetsBox  = $("#targets");
const prog        = $("#prog");
const status      = $("#status");
const download    = $("#download");

// Carpeta
const toggleDir        = $("#toggleDir");
const dirWrap          = $("#dirWrap");
const singleWrap       = $("#singleWrap");
const dirInput         = $("#dirInput");
const folderInfo       = $("#folderInfo");
const folderTargets    = $("#folderTargets");
const folderTarget     = $("#folderTarget");
const btnConvertFolder = $("#btnConvertFolder");
const batchLog         = $("#batchLog");
const batchProg        = $("#batchProg");   // barra de progreso de carpeta
const batchLinks       = $("#batchLinks");  // contenedor de enlaces por archivo

let completedForZip = [];                   // 👈 importante: declarar con let/const
if (batchLinks) batchLinks.innerHTML = "";

// ===== Render de selector de formato destino (archivo único) =====
function renderSelect(kind, list) {
  targetsBox.innerHTML = "";
  const wrap = document.createElement("div");
  wrap.className = "flex flex-wrap items-center gap-3";

  const sel = document.createElement("select");
  sel.className = "select select-bordered";
  sel.id = `${kind}Target`;
  list.forEach((fmt) => {
    const o = document.createElement("option");
    o.value = fmt;
    o.textContent = fmt.toUpperCase();
    sel.appendChild(o);
  });

  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "btn btn-primary";
  btn.textContent = "Convertir";
  btn.onclick = () => window.startConvert(kind, sel.value);

  wrap.appendChild(sel);
  wrap.appendChild(btn);
  targetsBox.appendChild(wrap);
  optionsBox.classList.remove("hidden");
}

// ===== Convertidor (archivo único) =====
window.startConvert = async function startConvert(kind, target) {
  const f = fileInput?.files?.[0];
  if (!f) return alert("Selecciona un archivo primero");

  prog?.classList.remove("hidden");
  if (status) status.textContent = "Subiendo archivo…";
  if (download) download.innerHTML = "";

  const fd = new FormData();
  fd.append("file", f);
  fd.append("kind", kind);
  fd.append("target", target);

  try {
    const r = await fetch("/convert", { method: "POST", body: fd });
    const { task_id } = await r.json();

    if (status) status.textContent = "Procesando…";
    const poll = setInterval(async () => {
      const s = await fetch("/status/" + task_id).then((x) => x.json());
      if (status) status.textContent = "Estado: " + s.state;

      if (s.state === "SUCCESS") {
        clearInterval(poll);
        prog?.classList.add("hidden");
        const url = s.result?.download_url;
        if (download)
          download.innerHTML = url
            ? `<a class="btn btn-success" target="_blank" href="${url}">Descargar archivo</a>`
            : "Terminado sin URL.";
      }
      if (s.state === "FAILURE") {
        clearInterval(poll);
        prog?.classList.add("hidden");
        if (status) status.textContent = "Error: " + (s.info || "Fallo");
      }
    }, 1500);
  } catch (e) {
    prog?.classList.add("hidden");
    if (status) status.textContent = "Error: " + e.message;
  }
};

// Al seleccionar archivo, auto-detecta tipo y muestra targets
fileInput?.addEventListener("change", () => {
  if (status) status.textContent = "";
  if (download) download.innerHTML = "";
  prog?.classList.add("hidden");
  targetsBox.innerHTML = "";

  const f = fileInput.files?.[0];
  if (!f) {
    fileBadge?.classList.add("hidden");
    return;
  }
  const ext = getExt(f.name);
  const kind = detectKindByExt(ext);
  if (!kind) {
    if (fileBadge) {
      fileBadge.textContent = `Tipo no soportado: .${ext}`;
      fileBadge.classList.remove("hidden");
    }
    optionsBox?.classList.add("hidden");
    return;
  }
  if (fileBadge) {
    fileBadge.textContent = `Detectado: ${kind.toUpperCase()} (.${ext})`;
    fileBadge.classList.remove("hidden");
  }
  renderSelect(kind, MAP[kind].targets);
});

// ===== Carpeta: toggle archivo/carpeta =====
toggleDir?.addEventListener("change", () => {
  const dir = toggleDir.checked;
  dirWrap?.classList.toggle("hidden", !dir);
  singleWrap?.classList.toggle("hidden", dir);
  // limpiar estados
  if (batchLog) batchLog.textContent = "";
  if (folderInfo) folderInfo.textContent = "";
  folderTargets?.classList.add("hidden");
  if (folderTarget) folderTarget.innerHTML = "";
  if (batchProg) { batchProg.classList.add("hidden"); batchProg.value = 0; }
  if (batchLinks) batchLinks.innerHTML = "";
});

// Carpeta: analizar selección y poblar targets
dirInput?.addEventListener("change", () => {
  if (batchLog) batchLog.textContent = "";
  if (folderInfo) folderInfo.textContent = "";
  folderTargets?.classList.add("hidden");
  if (folderTarget) folderTarget.innerHTML = "";
  if (batchProg) { batchProg.classList.add("hidden"); batchProg.value = 0; }
  if (batchLinks) batchLinks.innerHTML = "";

  const files = Array.from(dirInput.files || []);
  if (!files.length) {
    if (folderInfo) folderInfo.textContent = "No hay archivos en la carpeta.";
    return;
  }

  const kinds = new Set(files.map((f) => kindOfExt(getExt(f.name))));
  kinds.delete(null);
  if (kinds.size !== 1) {
    if (folderInfo) folderInfo.textContent = "Todos los archivos deben ser del mismo tipo (imagen, vídeo o audio).";
    return;
  }
  const kind = [...kinds][0];
  if (folderInfo) folderInfo.textContent = `Detectado: ${kind.toUpperCase()} (${files.length} archivo(s))`;

  const list = MAP[kind]?.targets || [];
  if (!list.length) {
    if (folderInfo) folderInfo.textContent += " · No hay formatos de destino.";
    return;
  }

  list.forEach((fmt) => {
    const o = document.createElement("option");
    o.value = fmt;
    o.textContent = fmt.toUpperCase();
    folderTarget?.appendChild(o);
  });
  folderTargets?.classList.remove("hidden");
});

// Carpeta: lanzar batch (con barra + enlaces de descarga)
btnConvertFolder?.addEventListener("click", async () => {
  if (batchLog) batchLog.textContent = "";
  if (batchLinks) batchLinks.innerHTML = "";

  const files = Array.from(dirInput.files || []);
  if (!files.length) {
    if (batchLog) batchLog.textContent = "Selecciona una carpeta con archivos.";
    return;
  }

  const kinds = new Set(files.map((f) => kindOfExt(getExt(f.name))));
  kinds.delete(null);
  if (kinds.size !== 1) {
    if (batchLog) batchLog.textContent = "Todos los archivos deben ser del mismo tipo.";
    return;
  }
  const kind = [...kinds][0];
  const target = folderTarget?.value;
  if (!target) {
    if (batchLog) batchLog.textContent = "Elige un formato de salida.";
    return;
  }

  const fd = new FormData();
  fd.append("kind", kind);
  fd.append("target", target);
  files.forEach((f) => fd.append("files", f, f.webkitRelativePath || f.name));

  // UI
  if (status) status.textContent = "Lanzando tareas…";
  if (download) download.innerHTML = "";
  prog?.classList.add("hidden");
  if (batchProg) { batchProg.classList.remove("hidden"); batchProg.value = 0; batchProg.max = files.length; }

  try {
    const res = await fetch("/api/convert/batch", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Error al lanzar el batch");

    const tasks = data.tasks || [];
    if (batchLog)
      batchLog.textContent = "Tareas lanzadas:\n" + tasks.map((t) => `- ${t.name}: ${t.task_id}`).join("\n");

    if (status) status.textContent = "Procesando… (0/" + tasks.length + ")";

    // Mapa id->nombre y set para no duplicar enlaces
    const nameById = Object.fromEntries(tasks.map(t => [t.task_id, t.name]));
    const shown = new Set();

    // Poll de progreso por número de tareas finalizadas
    const poll = setInterval(async () => {
      try {
        const states = await Promise.all(
          tasks.map(t =>
            fetch(`/status/${t.task_id}`).then(r => r.json()).catch(() => ({ state: "FAILURE" }))
          )
        );
        let done = 0;

        states.forEach((s, idx) => {
          const id = tasks[idx].task_id;
          if (s.state === "SUCCESS" || s.state === "FAILURE") done++;

          // Cuando una tarea termina con éxito por primera vez → añadimos botón
        //  if (s.state === "SUCCESS" && !shown.has(id) && s.result?.download_url && batchLinks) {
        //    shown.add(id);
        //    const a = document.createElement("a");
        //    a.href = s.result.download_url;
        //    a.target = "_blank";
        //    a.className = "btn btn-xs btn-success";
        //   a.textContent = "Descargar " + (nameById[id] || ("archivo_" + (idx+1)));
        //    batchLinks.appendChild(a);
        //  }
        });

        if (batchProg) batchProg.value = done;
        if (status) status.textContent = `Procesando… (${done}/${tasks.length})`;

        if (done >= tasks.length) {
  clearInterval(poll);
  if (status) status.textContent = "Completado.";

  // Único botón para descargar todo en ZIP
  if (batchLinks) {
    batchLinks.innerHTML = "";
    const zipBtn = document.createElement("button");
    zipBtn.className = "btn btn-success mt-2";
    zipBtn.textContent = "Descargar ZIP";
    zipBtn.onclick = async () => {
      if (typeof JSZip === "undefined") {
        alert("Falta JSZip en el index.html");
        return;
      }
      const zip = new JSZip();
      // Reconsultamos cada tarea para obtener su URL final
      for (const t of tasks) {
        const s2 = await fetch(`/status/${t.task_id}`).then(r => r.json());
        if (s2.state === "SUCCESS" && s2.result?.download_url) {
          const res = await fetch(s2.result.download_url);
          const blob = await res.blob();
          const base = t.name.replace(/\.[^.]+$/, "");
          const outName = `${base}.${(target || "").toLowerCase()}`;
          zip.file(outName, blob);
        }
      }
      const content = await zip.generateAsync({ type: "blob" });
      const dl = document.createElement("a");
      dl.href = URL.createObjectURL(content);
      dl.download = "carpeta_convertida.zip";
      document.body.appendChild(dl);
      dl.click();
      dl.remove();
    };
    batchLinks.appendChild(zipBtn);
  }
}
      } catch {
        // no rompas la UI si falla un poll
      }
    }, 1500);
  } catch (e) {
    if (status) status.textContent = "Error: " + e.message;
    if (batchProg) batchProg.classList.add("hidden");
  }
});

// ===== Downloader =====
const urlInput  = $("#urlInput");
const dlKind    = $("#dlKind");
const dlQuality = $("#dlQuality");
const prog2     = $("#prog2");
const status2   = $("#status2");
const download2 = $("#download2");

window.fillQuality = function fillQuality() {
  if (download2) download2.innerHTML = "";
  if (status2) status2.textContent = "";
  if (!dlQuality) return;

  dlQuality.innerHTML = "";
  if (dlKind?.value === "video") {
    ["best", "1080p", "720p", "480p", "360p"].forEach((q) => {
      const o = document.createElement("option");
      o.value = q;
      o.textContent = q;
      dlQuality.appendChild(o);
    });
  } else {
    [
      { v: "best", t: "best" },
      { v: "256k", t: "256 kbps" },
      { v: "128k", t: "128 kbps" },
    ].forEach(({ v, t }) => {
      const o = document.createElement("option");
      o.value = v;
      o.textContent = t;
      dlQuality.appendChild(o);
    });
  }
};

dlKind?.addEventListener("change", window.fillQuality);

window.startFetch = async function startFetch() {
  const url = urlInput?.value?.trim();
  if (!url) return alert("Pega una URL");

  prog2?.classList.remove("hidden");
  if (status2) status2.textContent = "Iniciando descarga…";
  if (download2) download2.innerHTML = "";

  const kind = dlKind?.value;
  const quality = dlQuality?.value;
  const fd = new FormData();
  fd.append("url", url);
  fd.append("kind", kind || "video");
  fd.append("quality", quality || "best");

  try {
    const r = await fetch("/fetch", { method: "POST", body: fd });
    const { task_id } = await r.json();

    if (status2) status2.textContent = "Descargando…";
    const poll = setInterval(async () => {
      const s = await fetch("/status/" + task_id).then((x) => x.json());
      if (status2) status2.textContent = "Estado: " + s.state;

      if (s.state === "SUCCESS") {
        clearInterval(poll);
        prog2?.classList.add("hidden");
        const u = s.result?.download_url;
        if (download2)
          download2.innerHTML = u
            ? `<a class="btn btn-success" target="_blank" href="${u}">Abrir/Descargar</a>`
            : "Terminado sin URL.";
      }
      if (s.state === "FAILURE") {
        clearInterval(poll);
        prog2?.classList.add("hidden");
        if (status2) status2.textContent = "Error: " + (s.info || "Fallo");
      }
    }, 1500);
  } catch (e) {
    prog2?.classList.add("hidden");
    if (status2) status2.textContent = "Error: " + e.message;
  }
};

// ===== Reset y atajos =====
window.resetForms = function resetForms() {
  // limpia file input
  const f = $("#file");
  if (f) f.value = "";

  // limpia URL
  const url = $("#urlInput");
  if (url) url.value = "";

  // restablece selects del bloque de descarga
  if (dlKind) dlKind.value = "video";
  if (typeof window.fillQuality === "function") window.fillQuality();
  if (dlQuality) dlQuality.value = "best";

  // limpia mensajes
  if (status) status.textContent = "";
  if (status2) status2.textContent = "";

  // limpia carpeta
  if (dirInput) dirInput.value = "";
  if (batchLog) batchLog.textContent = "";
  if (folderInfo) folderInfo.textContent = "";
  folderTargets?.classList.add("hidden");
  if (folderTarget) folderTarget.innerHTML = "";
  if (batchProg) { 
    batchProg.classList.add("hidden"); 
    batchProg.value = 0; 
  }

  // limpia descargas por carpeta
  completedForZip = [];
  if (batchLinks) batchLinks.innerHTML = "";
};


// Enter en campo URL dispara descarga
urlInput?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    if (typeof window.startFetch === "function") window.startFetch();
  }
});

// Inicializa calidades si entras directo al downloader
document.addEventListener("DOMContentLoaded", () => {
  if (typeof window.fillQuality === "function") window.fillQuality();
});
