#!/bin/bash

# Este script está diseñado para ser seguro en un servidor compartido.
# Solo afectará a los recursos definidos en el docker-compose.yml actual.

# --- Mensajes de confirmación ---

echo "⚠️  ATENCIÓN: Este script va a borrar **solo** los contenedores, redes y volúmenes de su aplicación actual."
echo "⚠️  WARNING: This script will delete **only** the containers, networks, and volumes of your current application."
echo "Esto liberará el espacio usado por la aplicación sin afectar otros servicios de Docker en el servidor."
echo "This will free up space used by the application without affecting other Docker services on the server."

read -p "¿Quieres continuar? (s/N) / Do you want to continue? (y/N): " confirm1

# --- Primera confirmación ---

if [[ "$confirm1" != "s" && "$confirm1" != "S" && "$confirm1" != "y" && "$confirm1" != "Y" ]]; then
  echo "❌ Cancelado por el usuario."
  echo "❌ Canceled by user."
  exit 1
fi

echo "" # Salto de línea para claridad
echo "⚠️  Esta es la segunda y última confirmación. La acción es irreversible para su aplicación."
echo "⚠️  This is the second and final confirmation. This action is irreversible for your application."
read -p "¿Estás absolutamente seguro? Escribe 'erease' para continuar: " confirm2

# --- Segunda confirmación ---

if [[ "$confirm2" != "erease" ]]; then
  echo "❌ Cancelado por el usuario."
  echo "❌ Canceled by user."
  exit 1
fi


echo "🛑 Deteniendo y eliminando contenedores, redes y volúmenes de la aplicación actual..."
# Este comando borra solo los recursos definidos en el docker-compose.yml de este directorio
docker compose down -v --rmi local

# NOTA IMPORTANTE: Se eliminan los comandos 'docker image prune' y 'docker system prune'
# para evitar tocar recursos de otras aplicaciones.

echo "🔨 Construyendo imágenes desde cero..."
# Se usa --force-recreate para garantizar que los cambios de código se apliquen
docker compose build --no-cache

echo "🚀 Levantando servicios en segundo plano..."
docker compose up -d --force-recreate

echo "✅ Todo listo. Use 'docker compose ps' para ver el estado de los contenedores."
