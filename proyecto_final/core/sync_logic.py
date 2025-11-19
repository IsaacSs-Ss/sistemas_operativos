import threading

# --- CONTROL DE ESTADO (SEMÁFORO) ---
# Si es True, significa que estamos escribiendo un archivo que vino de la red.
# El monitor local debe ignorar estos cambios.
_bloqueo_red = False
_lock = threading.Lock()

def marcar_inicio_escritura_red():
    """Activa el bloqueo: Estamos recibiendo datos de fuera."""
    global _bloqueo_red
    with _lock:
        _bloqueo_red = True

def marcar_fin_escritura_red():
    """Desactiva el bloqueo: Ya terminamos de escribir."""
    global _bloqueo_red
    with _lock:
        _bloqueo_red = False

def esta_bloqueado():
    """Devuelve True si el sistema está ocupado recibiendo datos."""
    with _lock:
        return _bloqueo_red