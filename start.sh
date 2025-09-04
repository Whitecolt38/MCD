#!/bin/bash
# Script para levantar el stack de MCD

cd "$(dirname "$0")" || exit 1

echo ">>> Levantando contenedores de MCD..."
docker compose up -d

echo ">>> Contenedores en ejecución:"
docker compose ps
