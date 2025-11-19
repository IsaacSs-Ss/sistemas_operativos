# sistema de archivos
================================================================================
MANUAL DE USUARIO - SISTEMA DE SINCRONIZACIÓN P2P (MODO ESPEJO)
================================================================================

1. DESCRIPCIÓN GENERAL
----------------------
Este sistema permite mantener dos carpetas sincronizadas en tiempo real entre 
diferentes sistemas operativos (Windows y Linux) a través de una red local. 
Cualquier archivo creado, modificado o eliminado en un equipo se reflejará 
automáticamente en el otro.

2. REQUISITOS PREVIOS
---------------------
- Python 3.8 o superior instalado.
- Conexión a la misma red local (Wi-Fi o Ethernet).
- Firewall configurado para permitir conexiones en puertos 5000 (TCP) y 5005 (UDP).

3. INSTRUCCIONES DE INSTALACIÓN
-------------------------------
El sistema es "autocontenido". No requiere instalación compleja.

1. Copie la carpeta del proyecto en el equipo.
2. Ejecute el archivo principal:
   - En Windows: Doble clic en 'main.py' o ejecute `python main.py` en terminal.
   - En Linux: Ejecute `python3 main.py` en terminal.
3. El sistema instalará automáticamente las dependencias necesarias (watchdog) 
   en el primer inicio.

4. USO DEL SISTEMA
------------------
A. INICIO
   Al abrir el programa, verá una ventana con el estado "BUSCANDO COMPAÑERO..." 
   en color naranja. El sistema busca automáticamente al otro equipo en la red.
   
B. CONEXIÓN
   Cuando el indicador cambie a VERDE ("CONECTADO: [IP]"), el sistema está listo.

C. SINCRONIZACIÓN
   1. Haga clic en el botón "Abrir Carpeta Espejo".
   2. Arrastre archivos (imágenes, textos, PDFs) a esta carpeta.
   3. Observe cómo aparecen en el otro equipo instantáneamente.
   4. La bitácora en la ventana mostrará el historial de transferencias.

D. NOTAS IMPORTANTES
   - El sistema ignora carpetas vacías; solo sincroniza archivos.
   - No edite el mismo archivo en ambos equipos al mismo tiempo (riesgo de conflicto).

5. SOLUCIÓN DE PROBLEMAS
------------------------
- ESTADO "BUSCANDO" ETERNO: Verifique que ambos equipos tengan IP en el mismo 
  rango (haga ping) y desactive temporalmente el Firewall.
- ERROR DE PERMISOS: Ejecute el script como Administrador (Windows) o con sudo (Linux).
