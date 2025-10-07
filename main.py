import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import logging
import os
import configparser
import time
import sys
import pythoncom
from datetime import datetime
# Importaciones de los módulos creados
# CAMBIO: Usar DuckDBManager en lugar de DBManager de SQLite
from main_duckdb import DuckDBManager
from libs.psutil.main_psutil import (
    obtener_metricas_psutil,
    obtener_lista_procesos
)
from libs.wmi.main_wmi import obtener_metricas_wmi
from libs.ohm.main_ohm import (
    initialize_openhardwaremonitor,
    obtener_metricas_ohm
)

# Importar win32timezone para asegurar que cx_Freeze lo empaquete
try:
    import win32timezone
except ImportError:
    pass

def _find_dir():
    """
    Función auxiliar para encontrar la ruta de un archivo,
    útil para los ejecutables empaquetados.
    """
    if getattr(sys, "frozen", False):
        # Estamos en un ejecutable de cx_Freeze
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

class PythonMonitorService(win32serviceutil.ServiceFramework):
    """
    Clase que implementa el servicio de monitoreo de Windows.
    """
    _svc_name_ = "PMA_v1.0"
    _svc_display_name_ = "Python Monitor Agent"
    _svc_description_ = "An agent to monitor system resources using Python and save the metrics to a log file."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.is_running = True
        self.log_file_name = "agente_monitoreo.log"
        self.monitor_interval = 5
        self.open_hardware_monitor_handle = None

    def SvcStop(self):
        """
        Detiene el servicio y notifica al sistema.
        """
        self.is_running = False
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        # CAMBIO: Llamar al método de limpieza de la instancia DuckDBManager
        DuckDBManager.close_instance() 

    def SvcDoRun(self):
        """
        Lógica principal del servicio.
        """
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_display_name_, "")
        )
        self.main_loop()

    def main_loop(self):
        """
        Bucle principal del agente de monitoreo.
        """
        self.load_config()
        self.setup_logging()

        logging.info("Agente de monitoreo de Windows iniciado.")

        # Obtiene la ruta base para los archivos de datos
        base_dir = _find_dir()
        
        # db_path ya no se usa, pero base_dir es necesario para el DuckDBManager
        dll_path = os.path.join(base_dir, "libs", "ohm", "OpenHardwareMonitorLib.dll")

        # CAMBIO: Obtiene la instancia de DuckDBManager usando el directorio base
        db_manager = DuckDBManager(base_dir)

        # Inicializar el handle de OpenHardwareMonitor una sola vez
        try:
            self.open_hardware_monitor_handle = initialize_openhardwaremonitor(dll_path)
        except Exception as e:
            logging.error(f"Error al inicializar OpenHardwareMonitor: {e}")
            self.open_hardware_monitor_handle = None

        while self.is_running:
            try:
                # Inicializar COM para que WMI funcione en el hilo del servicio
                pythoncom.CoInitialize()

                # Obtiene métricas del sistema
                metricas_psutil = obtener_metricas_psutil()
                # Obtiene métricas de WMI
                metricas_wmi = obtener_metricas_wmi()
                # Obtiene métricas de OHM
                metricas_ohm = obtener_metricas_ohm(self.open_hardware_monitor_handle)
                # Obtiene la lista de procesos
                lista_procesos = obtener_lista_procesos()

                if metricas_psutil and metricas_wmi and metricas_ohm:
                    # Combinamos ambos diccionarios
                    metricas_combinadas = {**metricas_psutil, **metricas_wmi, **metricas_ohm}
                    metricas_combinadas['timestamp'] = datetime.now().isoformat()
                    metricas_combinadas['hostname'] = socket.gethostname()

                    # Almacena las métricas usando la instancia Singleton (ahora en Parquet)
                    db_manager.insert_metrics(metricas_combinadas)
                    db_manager.upsert_machine_info(metricas_combinadas)

                    cpu_percent = metricas_combinadas.get('cpu_percent') or metricas_combinadas.get('cpu_freq_current_mhz') or 0
                    ram_percent = metricas_combinadas.get('memoria_percent') or metricas_combinadas.get('ram_load_percent') or 0
                    ram_used = metricas_combinadas.get('memoria_usada_gb') or metricas_combinadas.get('ram_load_used_gb') or 0
                    ram_free = metricas_combinadas.get('memoria_libre_gb') or metricas_combinadas.get('ram_load_free_gb') or 0
                    disk_percent = metricas_combinadas.get('disco_percent') or metricas_combinadas.get('hdd_used_gb') or 0

                    # Crea y registra un mensaje con las métricas combinadas (logueo sin cambios)
                    mensaje = (
                        f"Hostname: {metricas_combinadas.get('hostname', 'N/A')}"
                        f" | User: {metricas_combinadas.get('username', 'N/A')}"
                        f" | CPU %: {cpu_percent}"
                        f" | CPU MHz: {metricas_combinadas.get('cpu_freq_current_mhz', 0)}"
                        f" | CPU Bus MHz: {metricas_combinadas.get('cpu_clocks_mhz', 0)}"
                        f" | RAM %: {ram_percent}"
                        f" | RAM Used GB: {ram_used}"
                        f" | RAM Total GB: {metricas_combinadas.get('memoria_total_gb', 0)}"
                        f" | RAM free GB: {ram_free}"
                        f" | Disco %: {disk_percent}"
                        f" | Disco Used GB: {metricas_combinadas.get('disco_usado_gb', 0)}"
                        f" | Disco Total GB: {metricas_combinadas.get('disco_total_gb', 0)}"
                        f" | Disco Free GB: {metricas_combinadas.get('disco_libre_gb', 0)}"
                        f" | SWAP %: {metricas_combinadas.get('swap_percent', 0)}"
                        f" | SWAP Used GB: {metricas_combinadas.get('swap_usado_gb', 0)}"
                        f" | SWAP Total GB: {metricas_combinadas.get('swap_total_gb', 0)}"
                        f" | Red Bytes: Sent: {metricas_combinadas.get('red_bytes_enviados', 0)} - Recv: {metricas_combinadas.get('red_bytes_recibidos', 0)}"
                        f" | CPU ºC: {metricas_combinadas.get('cpu_temperatura_celsius', 0)}"
                        f" | Battery %: {metricas_combinadas.get('bateria_porcentaje', 0)}"
                        f" | CPU W: {metricas_combinadas.get('cpu_power_package_watts', 0)}"
                        f" | CPU Core W: {metricas_combinadas.get('cpu_power_cores_watts', 0)}"
                        f" | CPU Core W: {metricas_combinadas.get('cpu_clocks_mhz', 0)}"
                    )

                    logging.info(mensaje)

                    # Se omiten los logs detallados que estaban comentados para mantener la concisión
                
            except Exception as e:
                logging.error(f"Error en el bucle principal: {e}")
            finally:
                pythoncom.CoUninitialize()

            win32event.WaitForSingleObject(self.hWaitStop, int(self.monitor_interval * 1000))


    def load_config(self):
        """
        Carga la configuración desde configs/config.ini.
        """
        config = configparser.ConfigParser()
        try:
            base_dir = _find_dir()
            config_path = os.path.join(base_dir, "configs", "config.ini")
            config.read(config_path)
            self.monitor_interval = config.getint('AGENTE', 'intervalo_monitoreo', fallback=5)
            self.log_file_name = config.get('AGENTE', 'nombre_archivo_log', fallback='agente_monitoreo.log')
        except Exception as e:
            # En caso de error, usa valores por defecto
            self.monitor_interval = 5
            self.log_file_name = "agente_monitoreo.log"
            logging.error(f"Error al leer la configuración. Usando valores por defecto. Error: {e}")

    def setup_logging(self):
        """
        Configura el logger del servicio.
        """
        base_dir = _find_dir()
        log_path = os.path.join(base_dir, "data", self.log_file_name)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path)
            ]
        )

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(PythonMonitorService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(PythonMonitorService)
