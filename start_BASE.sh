#!/bin/bash
# Script agresivo para iniciar la app MCD desde cero de forma segura y verbose

cd "$(dirname "$0")" || exit 1

# --- 1. CONFIGURACIÓN Y CHEQUEO DE SEGURIDAD ---
PROJECT_NAME=$(basename "$(pwd)" | tr '[:upper:]' '[:lower:]')

TMP_PROJ_IDS=$(mktemp)
TMP_ALL_RUNNING_IDS=$(mktemp)

# Contenedores del proyecto
docker ps --filter "name=${PROJECT_NAME}-" -q | sed '/^$/d' > "$TMP_PROJ_IDS"
# Todos los contenedores en ejecución
docker ps -q | sed '/^$/d' > "$TMP_ALL_RUNNING_IDS"

# Detectar contenedores ajenos
ALIEN_CONTAINER_IDS=$(grep -v -f "$TMP_PROJ_IDS" -x "$TMP_ALL_RUNNING_IDS")

trap "rm -f $TMP_PROJ_IDS $TMP_ALL_RUNNING_IDS" EXIT

if [[ -n "$ALIEN_CONTAINER_IDS" ]]; then
    CLEAN_ALIEN_IDS=$(echo "$ALIEN_CONTAINER_IDS" | sed '/^$/d')
    ALIEN_CONTAINER_COUNT=$(echo "$CLEAN_ALIEN_IDS" | wc -l)

    if [[ "$ALIEN_CONTAINER_COUNT" -gt 0 ]]; then
        ALIEN_CONTAINER_NAMES=$(echo "$CLEAN_ALIEN_IDS" | xargs -r -n1 docker inspect --format '{{.Name}}' | sed 's/^\/\|$/ /g')
        echo "🚨 ERROR DE SEGURIDAD: ¡Contenedores ajenos detectados!"
        echo "El script ha sido CANCELADO para evitar daños."
        echo "Contenedores ajenos detectados ($ALIEN_CONTAINER_COUNT):"
        echo "$ALIEN_CONTAINER_NAMES"
        exit 1
    fi
fi

# --- 2. CONFIRMACIONES ---
echo "⚠️  ATENCIÓN: Este script eliminará **todos los contenedores, redes y volúmenes** de la aplicación actual y reconstruirá todo desde cero."
read -p "¿Quieres continuar? (s/N): " confirm1
if [[ "$confirm1" != "s" && "$confirm1" != "S" ]]; then
    echo "❌ Cancelado por el usuario."
    exit 1
fi

echo "⚠️  Segunda confirmación: esta acción es irreversible para su aplicación."
read -p "Escribe 'erease' para continuar: " confirm2
if [[ "$confirm2" != "erease" ]]; then
    echo "❌ Cancelado por el usuario."
    exit 1
fi

# --- 3. ELIMINAR RECURSOS DE LA APP (VERBOSE) ---
echo "🛑 Deteniendo y eliminando contenedores, redes y volúmenes de la aplicación..."
docker compose down -v --rmi local

# --- 4. RECONSTRUIR IMÁGENES Y LEVANTAR CONTENEDORES (VERBOSE) ---
echo "🔨 Construyendo imágenes desde cero..."
docker compose build --no-cache

echo "🚀 Levantando servicios en segundo plano..."
docker compose up -d --force-recreate

echo "✅ Todo listo. Use 'docker compose ps' para ver el estado de los contenedores."
