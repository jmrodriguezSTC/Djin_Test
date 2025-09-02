import psutil
import wmi
import time
import logging
import configparser
import os

# --- Configuración inicial del logger ---
# Configura el logger para escribir en un archivo y en la consola
# Esta parte se queda fuera del bucle porque no debe re-configurarse
config_logger = configparser.ConfigParser()
try:
    config_logger.read('config.ini')
    nombre_archivo_log = config_logger.get('AGENTE', 'nombre_archivo_log', fallback='monitoreo.log')
except Exception as e:
    print(f"Error al leer el nombre del archivo de log. Usando valor por defecto. Error: {e}")
    nombre_archivo_log = 'monitoreo.log'
    
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

def obtener_metricas_wmi():
    """
    Recopila métricas específicas de Windows usando la biblioteca wmi.
    """
    metricas_wmi = {}
    try:
        # Conexión a WMI
        c = wmi.WMI()
        
        # Obtener información de la placa base
        for board in c.Win32_BaseBoard():
            metricas_wmi['placa_base_fabricante'] = board.Manufacturer
            metricas_wmi['placa_base_producto'] = board.Product
        
        # Obtener estado de un servicio específico (por ejemplo, 'Spooler')
        for service in c.Win32_Service(Name="Spooler"):
            metricas_wmi['estado_servicio_spooler'] = service.State
            
        # Ejemplo: Obtener información de la tarjeta de red
        for interface in c.Win32_NetworkAdapterConfiguration(IPEnabled=True):
            metricas_wmi['tarjeta_red_descripcion'] = interface.Description
            metricas_wmi['tarjeta_red_ip'] = interface.IPAddress[0] if interface.IPAddress else "N/A"
            break
        
        # Ejemplo: Obtener el estado de la batería (solo para laptops)
        try:
            for battery in c.Win32_Battery():
                metricas_wmi['bateria_porcentaje'] = f"{battery.EstimatedChargeRemaining}%"
                metricas_wmi['bateria_estado'] = battery.BatteryStatus
                break
        except wmi.WMIError:
            metricas_wmi['bateria_porcentaje'] = "N/A"
            metricas_wmi['bateria_estado'] = "N/A"
            
        # Ejemplo: Obtener la temperatura de la CPU
        try:
            for temp_sensor in c.Win32_TemperatureProbe():
                metricas_wmi['cpu_temperatura_celsius'] = temp_sensor.CurrentReading / 10
                break
        except wmi.WMIError:
            metricas_wmi['cpu_temperatura_celsius'] = "N/A"

    except Exception as e:
        logging.error(f"Error al obtener métricas de WMI: {e}")
        return None
        
    return metricas_wmi

def obtener_lista_procesos():
    """
    Lista los procesos en ejecución y retorna su nombre y PID.
    """
    procesos = []
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            procesos.append({'pid': proc.pid, 'name': proc.name()})
    except Exception as e:
        logging.error(f"Error al listar procesos: {e}")
    return procesos

def main():
    """
    Función principal del agente de monitoreo.
    """
    logging.info("Agente de monitoreo de Windows iniciado.")
    
    while True:
        # Lee la configuración dentro del bucle para que sea dinámica
        config_runtime = configparser.ConfigParser()
        try:
            config_runtime.read('config.ini')
            intervalo_monitoreo = config_runtime.getint('AGENTE', 'intervalo_monitoreo', fallback=5)
        except Exception as e:
            logging.error(f"Error al leer la configuración en tiempo de ejecución. Usando valores por defecto. Error: {e}")
            intervalo_monitoreo = 5
            
        # Obtiene métricas del sistema
        metricas_sistema = obtener_metricas_sistema()
        
        # Obtiene métricas de WMI
        metricas_wmi = obtener_metricas_wmi()

        # Obtiene la lista de procesos
        lista_procesos = obtener_lista_procesos()
        
        if metricas_sistema and metricas_wmi:
            # Crea y registra un mensaje con las métricas del sistema y WMI
            mensaje_sistema = (
                f"CPU: {metricas_sistema['cpu_percent']}% | "
                f"RAM: {metricas_sistema['memoria_percent']}% ({metricas_sistema['memoria_usada_gb']}/{metricas_sistema['memoria_total_gb']} GB) | "
                f"Disco C: {metricas_sistema['disco_percent']}% ({metricas_sistema['disco_usado_gb']}/{metricas_sistema['disco_total_gb']} GB) | "
                f"Red (Bytes): Enviados={metricas_sistema['red_bytes_enviados']}, Recibidos={metricas_sistema['red_bytes_recibidos']}"
            )
            logging.info(mensaje_sistema)
            
            mensaje_wmi = (
                f"WMI: Placa Base={metricas_wmi.get('placa_base_producto', 'N/A')} | "
                f"Servicio Spooler={metricas_wmi.get('estado_servicio_spooler', 'N/A')} | "
                f"Tarjeta de red={metricas_wmi.get('tarjeta_red_descripcion', 'N/A')} ({metricas_wmi.get('tarjeta_red_ip', 'N/A')}) | "
                f"Batería={metricas_wmi.get('bateria_porcentaje', 'N/A')} (Estado: {metricas_wmi.get('bateria_estado', 'N/A')}) | "
                f"Temperatura CPU={metricas_wmi.get('cpu_temperatura_celsius', 'N/A')}°C"
            )
            logging.info(mensaje_wmi)
        
            # Loguea la lista de procesos según la condición de CPU
            if metricas_sistema['cpu_percent'] > 95:
                logging.warning(f"ALERTA: Alto uso de CPU! Procesos en ejecución ({len(lista_procesos)} total):")
                # Limita la salida a 10 procesos para evitar logs demasiado grandes
                for i, proc in enumerate(lista_procesos[:10]):
                    logging.warning(f"  - PID: {proc['pid']} | Nombre: {proc['name']}")
            else:
                logging.info(f"Número de procesos en ejecución: {len(lista_procesos)}")

        # Espera el intervalo de tiempo antes de la siguiente recolección
        time.sleep(intervalo_monitoreo)

if __name__ == "__main__":
    main()