import sys
import subprocess
import os
import time
import datetime
import platform
import tkinter as tk
from tkinter import messagebox, scrolledtext

# --- 1. VERIFICACIÓN DE INTEGRIDAD DEL SISTEMA ---
def verificar_integridad():
    """Revisa que no falten archivos vitales del sistema antes de arrancar."""
    archivos_vitales = [
        "core/__init__.py",
        "core/network_manager.py",
        "core/file_monitor.py",
        "core/sync_logic.py"
    ]
    
    faltantes = []
    for archivo in archivos_vitales:
        if not os.path.exists(archivo):
            faltantes.append(archivo)
            
    if faltantes:
        root = tk.Tk()
        root.withdraw() # Ocultar ventana principal temporal
        mensaje = "ERROR CRÍTICO: El sistema está dañado.\n\nFaltan los siguientes archivos vitales:\n"
        mensaje += "\n".join([f"- {f}" for f in faltantes])
        mensaje += "\n\nPor favor, restaura la carpeta 'core' o vuelve a generar el proyecto."
        messagebox.showerror("Error de Integridad", mensaje)
        sys.exit(1)

# Ejecutamos la verificación ANTES de importar nada de 'core'
verificar_integridad()

# --- 2. AUTO-INSTALACIÓN DE DEPENDENCIAS ---
def install_dependencies():
    """Verifica e instala librerías necesarias automáticamente."""
    try:
        import watchdog
    except ImportError:
        print("[SISTEMA] La librería 'watchdog' no está instalada.")
        print("[SISTEMA] Instalando automáticamente, por favor espere...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'watchdog'])
            print("[SISTEMA] Instalación completada. Reiniciando script...")
            time.sleep(1)
            os.execv(sys.executable, ['python'] + sys.argv)
        except Exception as e:
            print(f"[ERROR] No se pudo instalar watchdog: {e}")
            sys.exit(1)

install_dependencies()

# --- 3. IMPORTACIONES DEL NÚCLEO (Solo si pasó la verificación) ---
# Ahora es seguro importar porque sabemos que los archivos existen
try:
    from core.network_manager import NetworkManager
    from core.file_monitor import iniciar_monitor
except Exception as e:
    tk.messagebox.showerror("Error de Importación", f"Error al cargar módulos del núcleo:\n{e}")
    sys.exit(1)

# --- CONFIGURACIÓN ---
CARPETA_SYNC = os.path.abspath("carpeta_espejo")
ARCHIVO_LOG = "bitacora_sincronizacion.log"

class SyncApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Sincronizador Distribuido - {platform.system()}")
        self.root.geometry("650x500")
        
        # Asegurar carpeta espejo
        if not os.path.exists(CARPETA_SYNC):
            try:
                os.makedirs(CARPETA_SYNC)
            except OSError as e:
                messagebox.showerror("Error", f"No se pudo crear la carpeta espejo:\n{e}")
                root.destroy()
                return

        # --- DISEÑO DE INTERFAZ ---
        # Estilos
        bg_color = "#f0f0f0"
        self.root.configure(bg=bg_color)

        # 1. Encabezado y Estado
        header_frame = tk.Frame(root, bg="#333", pady=10)
        header_frame.pack(fill=tk.X)
        
        self.lbl_title = tk.Label(header_frame, text="SISTEMA ESPEJO P2P", fg="white", bg="#333", font=("Segoe UI", 12, "bold"))
        self.lbl_title.pack(side=tk.TOP)

        status_frame = tk.Frame(root, bg=bg_color, pady=5)
        status_frame.pack(fill=tk.X, padx=10)

        self.lbl_ip = tk.Label(status_frame, text="Iniciando red...", bg=bg_color, font=("Segoe UI", 10))
        self.lbl_ip.pack(side=tk.LEFT)
        
        self.lbl_status = tk.Label(status_frame, text="⚫ DESCONECTADO", fg="gray", bg=bg_color, font=("Segoe UI", 10, "bold"))
        self.lbl_status.pack(side=tk.RIGHT)

        # 2. Área de Logs (Bitácora Visual)
        log_frame = tk.LabelFrame(root, text="Bitácora de Eventos en Tiempo Real", bg=bg_color, padx=5, pady=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.txt_log = scrolledtext.ScrolledText(log_frame, state='disabled', height=15, font=("Consolas", 9))
        self.txt_log.pack(fill=tk.BOTH, expand=True)

        # 3. Controles
        btn_frame = tk.Frame(root, bg=bg_color, pady=10)
        btn_frame.pack(fill=tk.X)
        
        tk.Button(btn_frame, text="📂 Abrir Carpeta Espejo", command=self.abrir_carpeta, bg="#2196F3", fg="white", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15, pady=5).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="❌ Salir", command=self.cerrar_app, bg="#F44336", fg="white", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15, pady=5).pack(side=tk.RIGHT, padx=10)

        # --- INICIO DE SERVICIOS ---
        self.log_gui("Validación de sistema correcta.")
        self.log_gui("Iniciando servicios de sincronización...")
        
        try:
            # Instanciar Gestor de Red
            self.net_manager = NetworkManager(CARPETA_SYNC, self.log_gui)
            self.lbl_ip.config(text=f"Mi IP: {self.net_manager.my_ip}")
            
            # Iniciar Servidor y Discovery
            self.net_manager.iniciar_servidor()
            self.net_manager.iniciar_discovery()
            
            # Iniciar Monitor de Archivos (Watchdog)
            self.observer = iniciar_monitor(CARPETA_SYNC, self.net_manager)
            self.log_gui(f"Monitor activo en: {CARPETA_SYNC}")
            
            # Tarea periódica para actualizar estado en la GUI
            self.check_connection_status()
            
        except Exception as e:
            messagebox.showerror("Error Fatal", f"No se pudieron iniciar los servicios:\n{e}")
            self.log_gui(f"ERROR FATAL: {e}")

    def log_gui(self, mensaje):
        """Escribe en la GUI y en el archivo de bitácora."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        texto_final = f"[{timestamp}] {mensaje}"
        
        # 1. Escribir en GUI (Thread-safe)
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
            self.lbl_status.config(text=f"🟢 CONECTADO: {self.net_manager.peer_ip}", fg="green")
        else:
            self.lbl_status.config(text="🟠 BUSCANDO COMPAÑERO...", fg="orange")
        
        # Revisar cada 2 segundos de forma recursiva
        self.root.after(2000, self.check_connection_status)

    def abrir_carpeta(self):
        path = CARPETA_SYNC
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin": # macOS
                subprocess.Popen(["open", path])
            else: # Linux
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            self.log_gui(f"Error al abrir carpeta: {e}")

    def cerrar_app(self):
        if messagebox.askokcancel("Salir", "¿Detener la sincronización y salir?"):
            # Aquí se podrían detener los hilos limpiamente si fuera necesario
            self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = SyncApp(root)
    root.mainloop()