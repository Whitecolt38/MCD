# srv/beat_config.py (MODIFICADO)

from datetime import timedelta

CELERY_BEAT_SCHEDULE = {
    # Tarea 1: Limpieza de Resultados Antiguos (Redis)
    "celery_cleanup_old_results": {
        "task": "celery.backend_cleanup",
        "schedule": timedelta(days=1), # Sigue siendo diario
        "args": [],
    },
    
    # Tarea 2: Limpieza Profunda de MinIO (Archivos Viejos)
    "minio_deep_cleanup": {
        "task": "worker.minio_deep_cleanup_task", 
        
        # === CAMBIO CLAVE AQUÍ ===
        # Se ejecuta una vez al día.
        "schedule": timedelta(days=1), 
        # =========================
        
        # Argumento: Borrar objetos con más de 7 días (por ejemplo).
        # Este valor (7) aún se puede ajustar si necesitas que los archivos 
        # desaparezcan más rápido (ej: [3] para 3 días).
        "args": [1], 
    },
}