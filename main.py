import psutil
import time
import logging
import configparser
import os

# --- Configuración inicial ---
# Lee la configuración desde el archivo config.ini
config = configparser.ConfigParser()
try:
    config.read('config.ini')
    intervalo_monitoreo = config.getint('AGENTE', 'intervalo_monitoreo', fallback=5)
    nombre_archivo_log = config.get('AGENTE', 'nombre_archivo_log', fallback='monitoreo.log')
except Exception as e:
    print(f"Error al leer el archivo de configuración. Usando valores por defecto. Error: {e}")
    intervalo_monitoreo = 5
    nombre_archivo_log = 'monitoreo.log'

# Configura el logger para escribir en un archivo y en la consola
ruta_log = os.path.join(os.getcwd(), nombre_archivo_log)
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(ruta_log),
        logging.StreamHandler()
    ]
)

def obtener_metricas_sistema():
    """
    Recopila métricas clave del sistema usando la biblioteca psutil.
    """
    metricas = {}
    try:
        # Uso de CPU
        metricas['cpu_percent'] = psutil.cpu_percent(interval=1)
        
        # Uso de memoria
        memoria = psutil.virtual_memory()
        metricas['memoria_total_gb'] = round(memoria.total / (1024 ** 3), 2)
        metricas['memoria_usada_gb'] = round(memoria.used / (1024 ** 3), 2)
        metricas['memoria_percent'] = memoria.percent
        
        # Uso de disco
        disco = psutil.disk_usage('C:')
        metricas['disco_total_gb'] = round(disco.total / (1024 ** 3), 2)
        metricas['disco_usado_gb'] = round(disco.used / (1024 ** 3), 2)
        metricas['disco_percent'] = disco.percent
        
        # Actividad de red
        red = psutil.net_io_counters()
        metricas['red_bytes_enviados'] = red.bytes_sent
        metricas['red_bytes_recibidos'] = red.bytes_recv
        
    except Exception as e:
        logging.error(f"Error al obtener métricas del sistema: {e}")
        return None
    
    return metricas

def main():
    """
    Función principal del agente de monitoreo.
    """
    logging.info("Agente de monitoreo de Windows iniciado.")
    logging.info(f"El agente monitoreará el sistema cada {intervalo_monitoreo} segundos.")
    logging.info(f"Las métricas se guardarán en el archivo: {ruta_log}")
    
    while True:
        metricas = obtener_metricas_sistema()
        if metricas:
            # Crea un mensaje de registro con las métricas
            mensaje = (
                f"CPU: {metricas['cpu_percent']}% | "
                f"RAM: {metricas['memoria_percent']}% ({metricas['memoria_usada_gb']}/{metricas['memoria_total_gb']} GB) | "
                f"Disco C: {metricas['disco_percent']}% ({metricas['disco_usado_gb']}/{metricas['disco_total_gb']} GB) | "
                f"Red (Bytes): Enviados={metricas['red_bytes_enviados']}, Recibidos={metricas['red_bytes_recibidos']}"
            )
            logging.info(mensaje)
        
        # Espera el intervalo de tiempo antes de la siguiente recolección
        time.sleep(intervalo_monitoreo)

if __name__ == "__main__":
    main()