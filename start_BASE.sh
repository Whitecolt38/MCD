#!/bin/bash
# Script para iniciar la app MCD desde cero, seguro y controlado

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
        # Obtener nombres de contenedores ajenos correctamente
        ALIEN_CONTAINER_NAMES=$(echo "$CLEAN_ALIEN_IDS" | xargs -r -n1 docker inspect --format '{{.Name}}' | sed 's/^\/\|$/ /g')
        echo "🚨 ERROR DE SEGURIDAD: ¡Contenedores ajenos detectados!"
        echo "El script ha sido CANCELADO para evitar daños."
        echo "Contenedores ajenos detectados ($ALIEN_CONTAINER_COUNT):"
        echo "$ALIEN_CONTAINER_NAMES"
        exit 1
    fi
fi

# --- 2. CONFIRMACIÓN DEL USUARIO ---
PROJECT_CONTAINERS=$(docker ps --filter "name=${PROJECT_NAME}-" --format "{{.Names}}")
if [[ -n "$PROJECT_CONTAINERS" ]]; then
    echo "Contenedores del proyecto detectados:"
    echo "$PROJECT_CONTAINERS"
    echo ""
    read -p "⚠️  Se van a eliminar y recrear TODOS los contenedores del proyecto desde cero. ¿Desea continuar? (s/n) " CONFIRM
    if [[ "$CONFIRM" != "s" && "$CONFIRM" != "S" ]]; then
        echo "Operación cancelada por el usuario."
        exit 0
    fi
fi

# --- 3. ELIMINAR CONTENEDORES DEL PROYECTO ---
PROJECT_IDS=$(docker ps -a --filter "name=${PROJECT_NAME}-" -q)
if [[ -n "$PROJECT_IDS" ]]; then
    echo ">>> Deteniendo contenedores del proyecto..."
    docker stop $PROJECT_IDS > /dev/null 2>&1
    echo ">>> Eliminando contenedores del proyecto..."
    docker rm $PROJECT_IDS > /dev/null 2>&1
fi

# --- 4. LEVANTAR EL STACK DESDE CERO ---
echo ">>> Levantando contenedores de MCD desde cero..."
docker compose up -d

echo ">>> Contenedores en ejecución:"
docker compose ps
