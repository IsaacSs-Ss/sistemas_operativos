import sys
import subprocess
import os
import time
import datetime
import platform
import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog

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
        # Creamos una mini root temporal para mostrar el error
        root = tk.Tk()
        root.withdraw() 
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
try:
    from core.network_manager import NetworkManager
    from core.file_monitor import iniciar_monitor
except Exception as e:
    tk.messagebox.showerror("Error de Importación", f"Error al cargar módulos del núcleo:\n{e}")
    sys.exit(1)

# --- CONFIGURACIÓN GLOBAL ---
CARPETA_SYNC = os.path.abspath("carpeta_espejo")
ARCHIVO_LOG = "bitacora_sincronizacion.log"

class SyncApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Sincronizador Distribuido - {platform.system()}")
        self.root.geometry("680x550")
        
        # Asegurar carpeta espejo
        if not os.path.exists(CARPETA_SYNC):
            try:
                os.makedirs(CARPETA_SYNC)
            except OSError as e:
                messagebox.showerror("Error", f"No se pudo crear la carpeta espejo:\n{e}")
                root.destroy()
                return

        # --- DISEÑO DE INTERFAZ ---
        bg_color = "#f0f0f0"
        self.root.configure(bg=bg_color)

        # 1. Encabezado
        header_frame = tk.Frame(root, bg="#2c3e50", pady=15)
        header_frame.pack(fill=tk.X)
        
        self.lbl_title = tk.Label(header_frame, text="SISTEMA ESPEJO P2P", fg="white", bg="#2c3e50", font=("Segoe UI", 14, "bold"))
        self.lbl_title.pack(side=tk.TOP)

        # 2. Panel de Estado
        status_frame = tk.Frame(root, bg=bg_color, pady=10)
        status_frame.pack(fill=tk.X, padx=10)

        self.lbl_ip = tk.Label(status_frame, text="Obteniendo IP...", bg=bg_color, font=("Segoe UI", 10))
        self.lbl_ip.pack(side=tk.LEFT)
        
        self.lbl_status = tk.Label(status_frame, text="⚫ DESCONECTADO", fg="gray", bg=bg_color, font=("Segoe UI", 10, "bold"))
        self.lbl_status.pack(side=tk.RIGHT)

        # 3. Área de Logs
        log_label = tk.Label(root, text="Bitácora de Eventos en Tiempo Real:", bg=bg_color, anchor="w")
        log_label.pack(fill=tk.X, padx=10, pady=(10, 0))

        log_frame = tk.Frame(root, bg=bg_color)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.txt_log = scrolledtext.ScrolledText(log_frame, state='disabled', height=15, font=("Consolas", 9))
        self.txt_log.pack(fill=tk.BOTH, expand=True)

        # 4. Barra de Controles
        btn_frame = tk.Frame(root, bg="#e0e0e0", pady=10)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Botón Abrir Carpeta
        tk.Button(btn_frame, text="📂 Abrir Carpeta", command=self.abrir_carpeta, 
                  bg="#2196F3", fg="white", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15).pack(side=tk.LEFT, padx=10)
        
        # Botón Conexión Manual (SOLUCIÓN FIREWALL)
        tk.Button(btn_frame, text="🔗 Conexión Manual", command=self.conectar_manual, 
                  bg="#FF9800", fg="white", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15).pack(side=tk.LEFT, padx=10)

        # Botón Salir
        tk.Button(btn_frame, text="❌ Salir", command=self.cerrar_app, 
                  bg="#F44336", fg="white", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15).pack(side=tk.RIGHT, padx=10)

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
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        texto_final = f"[{timestamp}] {mensaje}"
        
        # GUI Update (asegura ejecución en hilo principal)
        self.root.after(0, lambda: self._insert_log(texto_final))
        
        # Archivo Log
        try:
            with open(ARCHIVO_LOG, "a", encoding="utf-8") as f:
                f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d')} {texto_final}\n")
        except:
            pass

    def _insert_log(self, texto):
        self.txt_log.config(state='normal')
        self.txt_log.insert(tk.END, texto + "\n")
        self.txt_log.see(tk.END)
        self.txt_log.config(state='disabled')

    def check_connection_status(self):
        """Revisa el estado de la conexión."""
        if self.net_manager.peer_ip:
            self.lbl_status.config(text=f"🟢 CONECTADO CON: {self.net_manager.peer_ip}", fg="green")
        else:
            self.lbl_status.config(text="🟠 BUSCANDO COMPAÑERO...", fg="orange")
        
        # Se llama a sí misma cada 2 segundos
        self.root.after(2000, self.check_connection_status)

    def conectar_manual(self):
        """Permite al usuario forzar la IP si el autodescubrimiento falla por Firewall."""
        ip_sugerida = "192.168.XXX.XXX"
        # Sugerir la IP contraria según el SO (basado en tus pruebas)
        if platform.system() == "Windows":
            ip_sugerida = "192.168.116.132" # IP de Ubuntu
        else:
            ip_sugerida = "192.168.116.131" # IP de Windows

        target_ip = simpledialog.askstring("Conexión Manual", 
                                         "Si el estado sigue 'BUSCANDO...', el Firewall puede estar bloqueando la red.\n\n"
                                         "Ingresa la IP del OTRO equipo:",
                                         initialvalue=ip_sugerida,
                                         parent=self.root)
        
        if target_ip:
            self.net_manager.peer_ip = target_ip
            self.log_gui(f"⚠️ Conexión forzada manualmente a: {target_ip}")
            messagebox.showinfo("Conectado", f"Objetivo fijado en {target_ip}.\nIntenta crear un archivo ahora.")
            # Actualizamos etiqueta inmediatamente
            self.lbl_status.config(text=f"🟢 CONECTADO (MANUAL): {target_ip}", fg="green")

    def abrir_carpeta(self):
        path = CARPETA_SYNC
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            self.log_gui(f"Error al abrir carpeta: {e}")

    def cerrar_app(self):
        if messagebox.askokcancel("Salir", "¿Detener la sincronización y salir?"):
            self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = SyncApp(root)
    root.mainloop()