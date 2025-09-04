# MCD - Media Convert & Download

This project is a **multimedia file converter and downloader** (images, videos, 3D models, etc.), packaged with **Docker Compose**.
It includes a web API with a graphical interface and background workers to perform the conversions.

---

## 🖥️ Help Scripts

To facilitate stack management without having to remember long Docker Compose commands, the repository includes two scripts:

- **`start.sh`** → starts the containers in the background and displays their status.
```bash ./start.sh
./start.sh

---

## 🚀 Main Services

- **Redis** → Task queue and cache.
- **MinIO** → S3-compatible storage for storing and serving the results.
- **API (FastAPI)** → Application entry point, exposes REST endpoints and the web interface.
- **Worker (Celery)** → Processes conversion and download tasks in the background.

---

## 📂 Repository Structure

.
├── docker-compose.yml # Orchestrates all services
├── mc/ # MinIO client (mc) and utilities
└── srv/ # Source code for the API and workers

---

## ⚙️ Requirements

- **Docker** ≥ 20.10
- **Docker Compose** ≥ v2

---

## ▶️ Getting Started

1. Clone the repository:
```bash Clone the repository: ```bash
git clone https://gitlab.mtknowledge.com/software/mcd.git
cd mcd
root@debian:/home/usuario/MCD# mv README.md README_ES.md
root@debian:/home/usuario/MCD# nano README_EN.md
root@debian:/home/usuario/MCD# nano README_ES.md
root@debian:/home/usuario/MCD# cat README_ES.md
# MCD - Media Convert & Download

This project is a **multimedia file converter and downloader** (images, videos, 3D models, etc.), packaged with **Docker Compose**.
It includes a web API with a graphical interface and background workers to perform the conversions.

---

## 🖥️ Help Scripts

To facilitate stack management without having to remember long Docker Compose commands, the repository includes two scripts:

- **`start.sh`** → starts the containers in the background and displays their status.
```bash ./start.sh
./start.sh

---

## 🚀 Main Services

- **Redis** → Task queue and cache.
- **MinIO** → S3-compatible storage for storing and serving the results.
- **API (FastAPI)** → Application entry point, exposes REST endpoints and the web interface.
- **Worker (Celery)** → Processes conversion and download tasks in the background.

---

## 📂 Repository Structure

.
├── docker-compose.yml # Orchestrates all services
├── mc/ # MinIO client (mc) and utilities
└── srv/ # Source code for the API and workers

---

## ⚙️ Requirements

- **Docker** ≥ 20.10
- **Docker Compose** ≥ v2

---

## ▶️ Getting Started

1. Clone the repository:
```bash Clone the repository: ```bash
git clone https://gitlab.mtknowledge.com/software/mcd.git
cd mcd

## 🔃 Restart
!!⚠️WARNING!!
The program contains the script "start_BASE.sh," which will delete all current containers and volumes. This script is more for freeing up space than for starting.
If you want to bring the container back up without losing anything, we recommend using "start.sh".