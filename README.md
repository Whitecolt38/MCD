# ------------------------------------------- English -------------------------------------------

# MCD - Media Convert & Download

This project is a **multimedia file converter and downloader** (images, videos, 3D models, etc.), packaged with **Docker Compose**.  
It includes a web API with a graphical interface and background workers to perform the conversions.

---

## 🖥️ Help Scripts

To facilitate stack management without having to remember long Docker Compose commands, the repository includes two scripts:

- **`start.sh`** → starts the containers in the background and displays their status.

```bash
./start.sh
```

---

## 🚀 Main Services

- **Redis** → Task queue and cache.  
- **MinIO** → S3-compatible storage for storing and serving the results.  
- **API (FastAPI)** → Application entry point, exposes REST endpoints and the web interface.  
- **Worker (Celery)** → Processes conversion and download tasks in the background.  

---

## 📂 Repository Structure

```
.
├── docker-compose.yml   # Orchestrates all services
├── mc/                  # MinIO client (mc) and utilities
└── srv/                 # Source code for the API and workers
```

---

## ⚙️ Requirements

- **Docker** ≥ 20.10  
- **Docker Compose** ≥ v2  

---

## ▶️ Getting Started

1. Clone the repository:

```bash
git clone https://gitlab.mtknowledge.com/software/mcd.git
cd mcd
```

---

## 🔃 Restart

⚠️ **WARNING**  
The program contains the script `start_BASE.sh`, which will delete all current containers and volumes.  
This script is more for freeing up space than for starting.  

If you want to bring the container back up without losing anything, we recommend using `start.sh`.

---

# ------------------------------------------- Spanish -------------------------------------------

# MCD - Media Convert & Download

Este proyecto es un **convertidor y descargador de archivos multimedia** (imágenes, vídeos, modelos 3D, etc.), empaquetado con **Docker Compose**.  
Incluye API web con interfaz gráfica y workers en segundo plano para realizar las conversiones.

---

## 🖥️ Scripts de ayuda

Para facilitar la gestión del stack sin recordar comandos largos de Docker Compose, el repositorio incluye dos scripts:

- **`start.sh`** → levanta los contenedores en segundo plano y muestra su estado.

```bash
./start.sh
```

---

## 🚀 Servicios principales

- **Redis** → Cola de tareas y caché.  
- **MinIO** → Almacenamiento S3 compatible para guardar y servir los resultados.  
- **API (FastAPI)** → Punto de entrada de la aplicación, expone endpoints REST y la interfaz web.  
- **Worker (Celery)** → Procesa las tareas de conversión y descarga en segundo plano.  

---

## 📂 Estructura del repositorio

```
.
├── docker-compose.yml   # Orquesta todos los servicios
├── mc/                  # Cliente de MinIO (mc) y utilidades
└── srv/                 # Código fuente de la API y workers
```

---

## ⚙️ Requisitos

- **Docker** ≥ 20.10  
- **Docker Compose** ≥ v2  

---

## ▶️ Puesta en marcha

1. Clona el repositorio:

```bash
git clone https://gitlab.mtknowledge.com/software/mcd.git
cd mcd
```

---

## 🔃 Reinicio

⚠️ **ADVERTENCIA**  
El programa contiene el script `start_BASE.sh`, que borrará todos los contenedores y volúmenes actuales.  
Este script está pensado más para liberar espacio que para iniciar.  

En caso de querer volver a levantar el contenedor sin perder nada, recomendamos usar `start.sh`.
