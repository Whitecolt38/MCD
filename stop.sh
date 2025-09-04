#!/bin/bash
# Script para detener el stack de MCD

cd "$(dirname "$0")" || exit 1

echo ">>> Deteniendo contenedores de MCD..."
docker compose down
