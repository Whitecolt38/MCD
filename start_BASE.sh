#!/bin/bash

# --- Mensajes de confirmación ---

echo "⚠️  ATENCIÓN: Este script va a borrar contenedores, imágenes y volúmenes antiguos de Docker."
echo "⚠️  WARNING: This script will delete old Docker containers, images, and volumes."
echo "Esto liberará espacio pero eliminará datos persistentes anteriores."
echo "This will free up space but will remove previous persistent data."

read -p "¿Quieres continuar? (s/N) / Do you want to continue? (y/N): " confirm1

# --- Primera confirmación ---

if [[ "$confirm1" != "s" && "$confirm1" != "S" && "$confirm1" != "y" && "$confirm1" != "Y" ]]; then
  echo "❌ Cancelado por el usuario."
  echo "❌ Canceled by user."
  exit 1
fi

echo "" # Salto de línea para claridad
echo "⚠️  Esta es la segunda y última confirmación. La acción es irreversible."
echo "⚠️  This is the second and final confirmation. This action is irreversible."
read -p "¿Estás absolutamente seguro? Escribe 'borrar' para continuar: " confirm2

# --- Segunda confirmación ---

if [[ "$confirm2" != "erease" ]]; then
  echo "❌ Cancelado por el usuario."
  echo "❌ Canceled by user."
  exit 1
fi


echo "🛑 Deteniendo y eliminando contenedores, redes y volúmenes antiguos..."
docker compose down -v

echo "🧹 Eliminando imágenes antiguas no usadas..."
docker image prune -a -f

echo "🧽 Limpiando cachés, redes y volúmenes huérfanos..."
docker system prune -f --volumes

echo "🔨 Construyendo imágenes desde cero..."
docker compose build --no-cache

echo "🚀 Levantando servicios en segundo plano..."
docker compose up -d

echo "✅ Todo listo. Usa 'docker compose ps' para ver el estado de los contenedores."
