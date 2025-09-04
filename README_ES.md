# MCD - Media Convert & Download

Este proyecto es un **convertidor y descargador de archivos multimedia** (imágenes, vídeos, modelos 3D, etc.), empaquetado con **Docker Compose**.  
Incluye API web con interfaz gráfica y workers en segundo plano para realizar las conversiones.

---

## 🖥️ Scripts de ayuda

Para facilitar la gestión del stack sin recordar comandos largos de Docker Compose, el repositorio incluye dos scripts:

- **`start.sh`** → levanta los contenedores en segundo plano y muestra su estado.  
  ```bash
  ./start.sh

---

## 🚀 Servicios principales

- **Redis** → Cola de tareas y caché.  
- **MinIO** → Almacenamiento S3 compatible para guardar y servir los resultados.  
- **API (FastAPI)** → Punto de entrada de la aplicación, expone endpoints REST y la interfaz web.  
- **Worker (Celery)** → Procesa las tareas de conversión y descarga en background.

---

## 📂 Estructura del repositorio

.
├── docker-compose.yml # Orquesta todos los servicios
├── mc/ # Cliente de MinIO (mc) y utilidades
└── srv/ # Código fuente de la API y workers

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
