import socket
import threading
import json
import os
import struct
import time
from core import sync_logic

# Configuración por defecto
UDP_PORT = 5005
TCP_PORT = 5000
BUFFER_SIZE = 4096

class NetworkManager:
    def __init__(self, carpeta_espejo, log_callback):
        self.carpeta_espejo = carpeta_espejo
        self.log = log_callback  # Función para escribir en la GUI
        self.peer_ip = None
        self.my_ip = self.obtener_mi_ip()
        self.running = True

    def obtener_mi_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    # --- AUTO DESCUBRIMIENTO (UDP) ---
    def iniciar_discovery(self):
        # Hilo que grita "AQUI ESTOY"
        threading.Thread(target=self._udp_beacon, daemon=True).start()
        # Hilo que escucha "DONDE ESTAS"
        threading.Thread(target=self._udp_listener, daemon=True).start()

    def _udp_beacon(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        msg = f"SYNC_HELLO:{self.my_ip}".encode()
        while self.running and self.peer_ip is None:
            sock.sendto(msg, ('<broadcast>', UDP_PORT))
            time.sleep(2)

    def _udp_listener(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', UDP_PORT))
        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                msg = data.decode()
                if msg.startswith("SYNC_HELLO:") and addr[0] != self.my_ip:
                    ip_remota = msg.split(":")[1]
                    if self.peer_ip != ip_remota:
                        self.peer_ip = ip_remota
                        self.log(f"[RED] Conectado con {self.peer_ip}")
            except:
                pass

    # --- SERVIDOR TCP (RECIBIR ARCHIVOS) ---
    def iniciar_servidor(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('0.0.0.0', TCP_PORT))
        server.listen(5)
        self.log(f"[RED] Escuchando en puerto {TCP_PORT}...")
        threading.Thread(target=self._accept_clients, args=(server,), daemon=True).start()

    def _accept_clients(self, server):
        while self.running:
            client, addr = server.accept()
            threading.Thread(target=self._handle_client, args=(client,), daemon=True).start()

    def _handle_client(self, client):
        try:
            # 1. Recibir tamaño del JSON de metadatos
            raw_msglen = self._recvall(client, 4)
            if not raw_msglen: return
            msglen = struct.unpack('>I', raw_msglen)[0]

            # 2. Recibir JSON
            raw_json = self._recvall(client, msglen)
            metadata = json.loads(raw_json.decode())
            
            accion = metadata['accion']
            rel_path = metadata['path']
            ruta_final = os.path.join(self.carpeta_espejo, rel_path)

            # ACTIVAR BLOQUEO
            sync_logic.marcar_inicio_escritura_red()

            if accion == 'ELIMINAR':
                if os.path.exists(ruta_final):
                    os.remove(ruta_final)
                    self.log(f"[ESPEJO] Eliminado remoto: {rel_path}")
            
            elif accion in ['CREAR', 'MODIFICAR']:
                # Recibir contenido del archivo
                tamano_archivo = metadata['size']
                # Asegurar directorios
                os.makedirs(os.path.dirname(ruta_final), exist_ok=True)
                
                recibido = 0
                with open(ruta_final, 'wb') as f:
                    while recibido < tamano_archivo:
                        chunk = client.recv(min(tamano_archivo - recibido, BUFFER_SIZE))
                        if not chunk: break
                        f.write(chunk)
                        recibido += len(chunk)
                self.log(f"[ESPEJO] Recibido: {rel_path}")

        except Exception as e:
            self.log(f"[ERROR] Fallo al recibir: {e}")
        finally:
            # LIBERAR BLOQUEO
            sync_logic.marcar_fin_escritura_red()
            client.close()

    def _recvall(self, sock, n):
        data = b''
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet: return None
            data += packet
        return data

    # --- CLIENTE TCP (ENVIAR CAMBIOS) ---
    def enviar_cambio(self, accion, ruta_absoluta_archivo):
        if not self.peer_ip:
            return # No hay nadie conectado

        try:
            rel_path = os.path.relpath(ruta_absoluta_archivo, self.carpeta_espejo)
            size = 0
            if accion != 'ELIMINAR':
                size = os.path.getsize(ruta_absoluta_archivo)

            metadata = {
                "accion": accion,
                "path": rel_path,
                "size": size
            }
            json_data = json.dumps(metadata).encode()
            
            # Empaquetar tamaño del header + header + archivo
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.peer_ip, TCP_PORT))
            
            # Enviar Longitud del JSON (4 bytes) + JSON
            s.sendall(struct.pack('>I', len(json_data)) + json_data)
            
            # Enviar contenido si no es eliminar
            if accion != 'ELIMINAR':
                with open(ruta_absoluta_archivo, 'rb') as f:
                    while True:
                        data = f.read(BUFFER_SIZE)
                        if not data: break
                        s.sendall(data)
            
            s.close()
            self.log(f"[ENVIADO] {accion}: {rel_path}")
            
        except Exception as e:
            self.log(f"[ERROR] Fallo enviando {rel_path}: {e}")