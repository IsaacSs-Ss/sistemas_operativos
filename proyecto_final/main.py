import sys
import subprocess
import os
import threading
import datetime
import platform

# --- 1. AUTO-INSTALACIÓN DE DEPENDENCIAS ---
def install_dependencies():
    """Verifica e instala librerías necesarias automáticamente."""
    required = {'watchdog'}
    try:
        import watchdog
    except ImportError:
        print("[SISTEMA] Instalando librería 'watchdog'...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'watchdog'])
        print("[SISTEMA] Instalación completada. Reiniciando script...")
        os.execv(sys.executable, ['python'] + sys.argv)

install_dependencies()

# --- IMPORTACIONES DEL NÚCLEO ---
import tkinter as tk
from tkinter import scrolledtext
from core.network_manager import NetworkManager
from core.file_monitor import iniciar_monitor

# --- CONFIGURACIÓN ---
CARPETA_SYNC = os.path.abspath("carpeta_espejo")
ARCHIVO_LOG = "bitacora_sincronizacion.log"

class SyncApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Sincronizador Distribuido - {platform.system()}")
        self.root.geometry("600x450")
        
        # Asegurar carpeta
        if not os.path.exists(CARPETA_SYNC):
            os.makedirs(CARPETA_SYNC)

        # --- INTERFAZ ---
        # 1. Panel de Estado
        top_frame = tk.Frame(root, bg="#ddd", pady=10)
        top_frame.pack(fill=tk.X)
        
        self.lbl_ip = tk.Label(top_frame, text="Iniciando red...", bg="#ddd", font=("Arial", 10))
        self.lbl_ip.pack(side=tk.LEFT, padx=10)
        
        self.lbl_status = tk.Label(top_frame, text="Estado: DESCONECTADO", fg="red", bg="#ddd", font=("Arial", 10, "bold"))
        self.lbl_status.pack(side=tk.RIGHT, padx=10)

        # 2. Área de Logs
        self.txt_log = scrolledtext.ScrolledText(root, state='disabled', height=15)
        self.txt_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 3. Botones
        btn_frame = tk.Frame(root, pady=10)
        btn_frame.pack(fill=tk.X)
        
        tk.Button(btn_frame, text="Abrir Carpeta Espejo", command=self.abrir_carpeta, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Salir", command=root.quit, bg="#f44336", fg="white").pack(side=tk.RIGHT, padx=10)

        # --- INICIO DE SERVICIOS ---
        self.log_gui("Sistema iniciado.")
        
        # Instanciar Gestor de Red
        self.net_manager = NetworkManager(CARPETA_SYNC, self.log_gui)
        self.lbl_ip.config(text=f"Mi IP: {self.net_manager.my_ip}")
        
        # Iniciar Servidor y Discovery
        self.net_manager.iniciar_servidor()
        self.net_manager.iniciar_discovery()
        
        # Iniciar Monitor de Archivos (Watchdog)
        self.observer = iniciar_monitor(CARPETA_SYNC, self.net_manager)
        
        # Tarea periódica para actualizar estado en la GUI
        self.check_connection_status()

    def log_gui(self, mensaje):
        """Escribe en la GUI y en el archivo de bitácora."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        texto_final = f"[{timestamp}] {mensaje}"
        
        # 1. Escribir en GUI (Thread-safe usando after)
        self.root.after(0, lambda: self._insert_log(texto_final))
        
        # 2. Escribir en Archivo (Bitácora Persistente)
        try:
            with open(ARCHIVO_LOG, "a", encoding="utf-8") as f:
                f.write(texto_final + "\n")
        except Exception as e:
            print(f"Error escribiendo bitácora: {e}")

    def _insert_log(self, texto):
        self.txt_log.config(state='normal')
        self.txt_log.insert(tk.END, texto + "\n")
        self.txt_log.see(tk.END)
        self.txt_log.config(state='disabled')

    def check_connection_status(self):
        """Revisa si ya encontramos al compañero."""
        if self.net_manager.peer_ip:
            self.lbl_status.config(text=f"CONECTADO: {self.net_manager.peer_ip}", fg="green")
        else:
            self.lbl_status.config(text="BUSCANDO COMPAÑERO...", fg="orange")
        
        # Revisar cada 2 segundos
        self.root.after(2000, self.check_connection_status)

    def abrir_carpeta(self):
        path = CARPETA_SYNC
        if platform.system() == "Windows":
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open", path])

if __name__ == "__main__":
    root = tk.Tk()
    app = SyncApp(root)
    root.mainloop()