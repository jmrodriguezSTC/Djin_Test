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
from sqlite.main_sqlite import DBManager
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
        # Cierra la conexión de la base de datos usando el Singleton
        db_manager = DBManager()
        db_manager.close_connection()

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
        db_path = os.path.join(base_dir, "data", "monitoreo.db")
        dll_path = os.path.join(base_dir, "libs", "ohm", "OpenHardwareMonitorLib.dll")

        # Obtiene la instancia del Singleton. Esto crea la conexión la primera vez.
        db_manager = DBManager(db_path)

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

                    # Almacena las métricas usando la instancia Singleton
                    db_manager.insert_metrics(metricas_combinadas)
                    db_manager.upsert_machine_info(metricas_combinadas)

                    # Crea y registra un mensaje con las métricas de psutil
                    mensaje_psutil = (
                        f"CPU: {metricas_psutil['cpu_percent']}%, Cores: Logical[{metricas_psutil['cpu_core_logical']}] Physical[{metricas_psutil['cpu_core_physical']}], Freq: Current[{metricas_psutil['cpu_freq_current_mhz']:.2f}Mhz], Min[{metricas_psutil['cpu_freq_min_mhz']:.2f}Mhz], Max[{metricas_psutil['cpu_freq_max_mhz']:.2f}Mhz] | "
                        f"RAM: {metricas_psutil['memoria_percent']}% ({metricas_psutil['memoria_usada_gb']}/{metricas_psutil['memoria_total_gb']} GB, Free:{metricas_psutil['memoria_libre_gb']} GB) | "
                        f"Swap: {metricas_psutil['swap_percent']}% ({metricas_psutil['swap_usado_gb']}/{metricas_psutil['swap_total_gb']} GB) | "
                        f"Disco C: {metricas_psutil['disco_percent']}% ({metricas_psutil['disco_usado_gb']}/{metricas_psutil['disco_total_gb']} GB, Free:{metricas_psutil['disco_libre_gb']} GB) | "
                        f"Red (Bytes): Enviados={metricas_psutil['red_bytes_enviados']}, Recibidos={metricas_psutil['red_bytes_recibidos']}"
                    )
                    
                    logging.info(mensaje_psutil)

                    # Crea y registra un mensaje con las métricas de WMI
                    mensaje_wmi = (
                        f"WMI: OS={metricas_wmi.get('os_name', 'N/A')}, Arquitecture:{metricas_wmi.get('os_architecture', 'N/A')}, Serial Number:{metricas_wmi.get('os_serial_number', 'N/A')}, Last Boost:{metricas_wmi.get('os_last_boot_up_time', 'N/A')} | "
                        f"Placa Base={metricas_wmi.get('placa_base_producto', 'N/A')}, Fabricante:{metricas_wmi.get('placa_base_fabricante', 'N/A')}, Serial Number:{metricas_wmi.get('placa_base_numero_serie', 'N/A')} | "
                        f"Procesador={metricas_wmi.get('procesador_nombre', 'N/A')},Cores: Logical={metricas_wmi.get('procesador_nucleos_logicos', 'N/A')}, Physical={metricas_wmi.get('procesador_nucleos_fisicos', 'N/A')} | "
                        f"Batería={metricas_wmi.get('bateria_porcentaje', 'N/A')}% (Estado: {metricas_wmi.get('bateria_estado', 'N/A')})"
                    )
                    
                    logging.info(mensaje_wmi)

                    # Crea y registra un mensaje con las métricas de OHM
                    mensaje_ohm = (
                        f"OHM CPU: {metricas_ohm.get('cpu_name', 'N/A')}, Load:{metricas_ohm.get('cpu_load_percent', 'N/A')} %, Power: Package:{metricas_ohm.get('cpu_power_package_watts', 'N/A')} W, Cores:{metricas_ohm.get('cpu_power_cores_watts', 'N/A')} W, Bus Speed:{metricas_ohm.get('cpu_clocks_mhz', 'N/A')} Mhz, Temperature:{metricas_ohm.get('cpu_temperatura_celsius', 'N/A')} ºC | "
                        f"Memory: {metricas_ohm.get('ram_name', 'N/A')}, {metricas_ohm.get('ram_load_percent', 'N/A')} %, Used:{metricas_ohm.get('ram_load_used_gb', 'N/A')} GB, Free:{metricas_ohm.get('ram_load_free_gb', 'N/A')} GB | "
                        f"Disco Duro: {metricas_ohm.get('hdd_name', 'N/A')}, Used:{metricas_ohm.get('hdd_used_gb', 'N/A')} %"
                    )

                    logging.info(mensaje_ohm)

                    # Loguea la lista de procesos según la condición de CPU
                    if metricas_psutil['cpu_percent'] > 95:
                        logging.warning(f"ALERTA: Alto uso de CPU! Procesos en ejecución ({len(lista_procesos)} total):")
                        # Limita la salida a 10 procesos para evitar logs demasiado grandes
                        for i, proc in enumerate(lista_procesos[:10]):
                            logging.warning(f"  - PID: {proc['pid']} | Nombre: {proc['name']}")
                    else:
                        logging.info(f"Número de procesos en ejecución: {len(lista_procesos)}")
            except Exception as e:
                logging.error(f"Error en el bucle principal: {e}")
            finally:
                pythoncom.CoUninitialize()

            time.sleep(self.monitor_interval)

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
