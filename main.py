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
# Gestor de SQLite
from sqlite.main_sqlite import DBManager
# Gestor de Parquet con DuckDB
from main_duckdb import ParquetManager
# Libreria de obtención de metricas
# Gestor de Psutil, WMI y OHM
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
        self.monitor_interval = 60
        self.open_hardware_monitor_handle = None
        # Variables para los gestores
        self.db_manager = None
        self.parquet_manager = None
        self.parquet_retention_minutes = 60 # Tiempo de retención por defecto

    def SvcStop(self):
        """
        Detiene el servicio y notifica al sistema.
        """
        self.is_running = False
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        # Cierra la conexión de la base de datos usando el Singleton
        if self.db_manager:
            self.db_manager.close_connection()

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
        Bucle principal del agente de monitoreo, ahora con gestión de Parquet.
        """
        self.load_config()
        self.setup_logging()

        logging.info("Agente de monitoreo de Windows iniciado.")

        # Obtiene la ruta base para los archivos de datos
        base_dir = _find_dir()
        db_path = os.path.join(base_dir, "data", self.db_file_name)
        dll_path = os.path.join(base_dir, "libs", "ohm", "OpenHardwareMonitorLib.dll")
        
        # --- Configuración DuckDB/Parquet ---
        parquet_dir = os.path.join(base_dir, "data", "metricas")
        # Obtiene la instancia del Singleton para Parquet.
        self.parquet_manager = ParquetManager(parquet_dir)
        # Se establece el tiempo de retención (puede cargarse desde config.ini si se implementa allí)
        self.parquet_manager.set_retention(self.parquet_retention_minutes)
        # --- Fin Configuración DuckDB/Parquet ---

        # Obtiene la instancia del Singleton de SQLite.
        self.db_manager = DBManager(db_path)

        # Inicializar el handle de OpenHardwareMonitor una sola vez
        try:
            self.open_hardware_monitor_handle = initialize_openhardwaremonitor(dll_path)
        except Exception as e:
            logging.error(f"Error al inicializar OpenHardwareMonitor: {e}")
            self.open_hardware_monitor_handle = None
            
        # Al iniciar, asegurar que las tablas existen
        db_manager.create_table()
        db_manager.create_machine_info_table()

        # MODIFICACIÓN: Intentar vaciar la cola inmediatamente después de iniciar,
        # en caso de que existan datos de una ejecución previa interrumpida.
        db_manager.process_queue()

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
                    
                    # Almacena las métricas en SQLite
                    self.db_manager.insert_metrics(metricas_combinadas)
                    self.db_manager.upsert_machine_info(metricas_combinadas)
                    
                    # --- Guardar a Parquet y Limpiar ---
                    if self.parquet_manager:
                        # 1. Guardar la métrica actual como archivo Parquet
                        self.parquet_manager.save_metrics_to_parquet(metricas_combinadas)
                        
                        # 2. Limpiar archivos Parquet antiguos (de más de 1 hora/60 minutos)
                        self.parquet_manager.clean_old_parquet_files()

                    # Adecuación de algunos datos
                    cpu_percent = metricas_combinadas.get('cpu_percent') or metricas_combinadas.get('cpu_load_percent') or 0
                    ram_percent = metricas_combinadas.get('memoria_percent') or metricas_combinadas.get('ram_load_percent') or 0
                    ram_used = metricas_combinadas.get('memoria_usada_gb') or metricas_combinadas.get('ram_load_used_gb') or 0
                    ram_free = metricas_combinadas.get('memoria_libre_gb') or metricas_combinadas.get('ram_load_free_gb') or 0
                    disk_percent = metricas_combinadas.get('disco_percent') or metricas_combinadas.get('hdd_used_gb') or 0

                    # Crea y registra un mensaje con las métricas combinadas
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
                    # Looging las metricas
                    logging.info(mensaje)

                    # Lógica para combinar la Placa Base
                    placa_base_fabricante = metricas_combinadas.get('placa_base_fabricante', 'Desconocido')
                    placa_base_producto = metricas_combinadas.get('placa_base_producto', 'Desconocido')
                    # Formato: Fabricante - Producto. Se elimina el separador si ambos son 'Desconocido'.
                    if placa_base_fabricante == 'Desconocido' and placa_base_producto == 'Desconocido':
                        placa_base_combined = 'Desconocido'
                    else:
                        placa_base_combined = f"{placa_base_fabricante} - {placa_base_producto}".replace("Desconocido - ", "").replace(" - Desconocido", "")
                    # Crea el mensaje de información de la maquina
                    mensaje_info = (
                        f"Hostname: {metricas_combinadas.get('hostname', 'N/A')}"
                        f" | User: {metricas_combinadas.get('username', 'N/A')}"
                        f" | OS Name: {metricas_combinadas.get('os_name', 'Desconocido')}"
                        f" | Motherboard Name: {placa_base_combined}"
                        f" | Processor Name: {metricas_combinadas.get('procesador_nombre', 'Desconocido')}"
                        f" - Cores: Logical: {metricas_combinadas.get('procesador_nucleos_logicos', 'N/A')}"
                        f" / Physical: {metricas_combinadas.get('procesador_nucleos_fisicos', 'N/A')}"
                        f" | OS Last Bot Up Time: {metricas_combinadas.get('os_last_boot_up_time', 'Desconocido')}"
                    )
                    # Looging las metricas info
                    logging.info(mensaje_info)

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
            self.monitor_interval = config.getint('AGENTE', 'intervalo_monitoreo', fallback=60)
            self.log_file_name = config.get('AGENTE', 'nombre_archivo_log', fallback='agente_monitoreo.log')
            self.db_file_name = config.get('AGENTE', 'nombre_archivo_db', fallback='monitor_data.db')
            # Se podría añadir la configuración de retención aquí si fuera necesario
            # self.parquet_retention_minutes = config.getint('DUCKDB', 'retencion_minutos', fallback=60)
        except Exception as e:
            # En caso de error, usa valores por defecto
            self.monitor_interval = 60
            self.log_file_name = "agente_monitoreo.log"
            self.db_file_name = "monitoreo.db"
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
