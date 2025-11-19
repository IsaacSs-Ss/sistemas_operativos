import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from core import sync_logic

class MonitorHandler(FileSystemEventHandler):
    def __init__(self, network_manager):
        self.net = network_manager

    def procesar(self, evento, accion):
        # FILTRO CRÍTICO: Si estamos bloqueados por escritura de red, IGNORAR.
        if sync_logic.esta_bloqueado():
            return
            
        if evento.is_directory:
            return

        # Esperar un poco por si el archivo está siendo escrito por el SO
        time.sleep(0.1)
        self.net.enviar_cambio(accion, evento.src_path)

    def on_created(self, event):
        self.procesar(event, "CREAR")

    def on_modified(self, event):
        self.procesar(event, "MODIFICAR")

    def on_deleted(self, event):
        self.procesar(event, "ELIMINAR")

def iniciar_monitor(ruta, network_manager):
    event_handler = MonitorHandler(network_manager)
    observer = Observer()
    observer.schedule(event_handler, ruta, recursive=True)
    observer.start()
    return observer