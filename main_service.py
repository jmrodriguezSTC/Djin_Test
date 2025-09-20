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
import threading
import pythoncom
import psutil
import wmi
import clr # Se necesita la biblioteca 'pythonnet'
from db_manager import DBManager
from datetime import datetime

# Importar win32timezone para asegurar que cx_Freeze lo empaquete
try:
    import win32timezone
except ImportError:
    pass

# Se necesitan estos dos archivos en la misma carpeta del script
# 1. OpenHardwareMonitorLib.dll
# 2. El script principal (main_service.py)

def _find_dir(path):
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
        self.log_file_name = "monitoreo.log"
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
        
        # Obtiene la instancia del Singleton. Esto crea la conexión la primera vez.
        db_path = os.path.join(_find_dir("monitoreo.db"), "monitoreo.db")
        db_manager = DBManager(db_path)

        # Inicializar el handle de OpenHardwareMonitor una sola vez
        try:
            self.open_hardware_monitor_handle = self.initialize_openhardwaremonitor()
        except Exception as e:
            logging.error(f"Error al inicializar OpenHardwareMonitor: {e}")
            self.open_hardware_monitor_handle = None

        while self.is_running:
            try:
                # Inicializar COM para que WMI funcione en el hilo del servicio
                pythoncom.CoInitialize()
                
                # Obtiene métricas del sistema
                metricas_sistema = self.obtener_metricas_sistema()
                # Obtiene métricas de WMI
                metricas_wmi = self.obtener_metricas_wmi()
                # Obtiene la lista de procesos
                lista_procesos = self.obtener_lista_procesos()

                if metricas_sistema and metricas_wmi:
                    # Combinamos ambos diccionarios
                    metricas_combinadas = {**metricas_sistema, **metricas_wmi}
                    metricas_combinadas['timestamp'] = datetime.now().isoformat()
                    
                    # Almacena las métricas usando la instancia Singleton
                    db_manager.insert_metrics(metricas_combinadas)

                    # Crea y registra un mensaje con las métricas del sistema
                    mensaje_sistema = (
                        f"CPU: {metricas_sistema['cpu_percent']}%, Cores: Logical[{metricas_sistema['cpu_core_logical']}] Physical[{metricas_sistema['cpu_core_physical']}], Freq: Current[{metricas_sistema['cpu_freq_current_mhz']:.2f}Mhz], Min[{metricas_sistema['cpu_freq_min_mhz']:.2f}Mhz], Max[{metricas_sistema['cpu_freq_max_mhz']:.2f}Mhz] | "
                        f"RAM: {metricas_sistema['memoria_percent']}% ({metricas_sistema['memoria_usada_gb']}/{metricas_sistema['memoria_total_gb']} GB, Free:{metricas_sistema['memoria_libre_gb']} GB) | "
                        f"Swap: {metricas_sistema['swap_percent']}% ({metricas_sistema['swap_usado_gb']}/{metricas_sistema['swap_total_gb']} GB) | "
                        f"Disco C: {metricas_sistema['disco_percent']}% ({metricas_sistema['disco_usado_gb']}/{metricas_sistema['disco_total_gb']} GB, Free:{metricas_sistema['disco_libre_gb']} GB) | "
                        f"Red (Bytes): Enviados={metricas_sistema['red_bytes_enviados']}, Recibidos={metricas_sistema['red_bytes_recibidos']}"
                    )
                    
                    logging.info(mensaje_sistema)
                    
                    # Crea y registra un mensaje con las métricas de WMI
                    mensaje_wmi = (
                        f"WMI: OS={metricas_wmi.get('os_name', 'N/A')}, Arquitecture:{metricas_wmi.get('os_architecture', 'N/A')}, Serial Number:{metricas_wmi.get('os_serial_number', 'N/A')}, Last Boost:{metricas_wmi.get('os_last_boot_up_time', 'N/A')} | "
                        f"Placa Base={metricas_wmi.get('placa_base_producto', 'N/A')}, Fabricante:{metricas_wmi.get('placa_base_fabricante', 'N/A')}, Serial Number:{metricas_wmi.get('placa_base_numero_serie', 'N/A')} | "
                        f"Procesador={metricas_wmi.get('procesador_nombre', 'N/A')},Cores: Logical={metricas_wmi.get('procesador_nucleos_logicos', 'N/A')}, Physical={metricas_wmi.get('procesador_nucleos_fisicos', 'N/A')} | "
                        f"Batería={metricas_wmi.get('bateria_porcentaje', 'N/A')} (Estado: {metricas_wmi.get('bateria_estado', 'N/A')})"
                    )

                    # Añadir la temperatura del CPU al mensaje si está disponible
                    # if 'cpu_temperatura_celsius' in metricas_wmi:
                    #     mensaje_wmi += f" | Temperatura CPU: {metricas_wmi['cpu_temperatura_celsius']}°C"
                    
                    logging.info(mensaje_wmi)
                
                    # Loguea la lista de procesos según la condición de CPU
                    if metricas_sistema['cpu_percent'] > 95:
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
        Carga la configuración desde config.ini.
        """
        config = configparser.ConfigParser()
        try:
            current_dir = _find_dir("config.ini")
            config_path = os.path.join(current_dir, "config.ini")
            config.read(config_path)
            self.monitor_interval = config.getint('AGENTE', 'intervalo_monitoreo', fallback=5)
            self.log_file_name = config.get('AGENTE', 'nombre_archivo_log', fallback='monitoreo.log')
        except Exception as e:
            # En caso de error, usa valores por defecto
            self.monitor_interval = 5
            self.log_file_name = "monitoreo.log"
            logging.error(f"Error al leer la configuración. Usando valores por defecto. Error: {e}")

    def setup_logging(self):
        """
        Configura el logger del servicio.
        """
        log_path = os.path.join(_find_dir("monitoreo.log"), self.log_file_name)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path)
            ]
        )

    def initialize_openhardwaremonitor(self):
        """
        Inicializa OpenHardwareMonitor llamando directamente a la DLL.
        """
        try:
            dll_path = os.path.join(_find_dir("OpenHardwareMonitorLib.dll"), "OpenHardwareMonitorLib.dll")
            clr.AddReference(dll_path)
            from OpenHardwareMonitor import Hardware
            handle = Hardware.Computer()
            handle.CPUEnabled = True
            handle.Open()
            return handle
        except Exception as e:
            logging.error(f"No se pudo inicializar OpenHardwareMonitor. Error: {e}")
            return None

    def obtener_cpu_temperatura_dll(self):
        """
        Obtiene la temperatura de la CPU usando la DLL de OpenHardwareMonitor.
        """
        if not self.open_hardware_monitor_handle:
            return None
        
        try:
            handle = self.open_hardware_monitor_handle
            handle.CPUEnabled = True
            handle.Open()
            
            for i in handle.Hardware:
                if i.HardwareType.ToString() == 'CPU':
                    i.Update()
                    for sensor in i.Sensors:
                        if sensor.SensorType.ToString() == 'Temperature' and sensor.Value is not None:
                            return round(float(sensor.Value), 2)
        except Exception as e:
            logging.error(f"Error al obtener temperatura con OpenHardwareMonitor DLL: {e}")
        
        return None

    def obtener_metricas_sistema(self):
        """
        Recopila métricas clave del sistema usando la biblioteca psutil.
        """
        metricas = {}
        try:
            metricas['cpu_percent'] = psutil.cpu_percent(interval=1)
            metricas['cpu_core_logical'] = psutil.cpu_count(logical=True)
            metricas['cpu_core_physical'] = psutil.cpu_count(logical=False)
            metricas['cpu_freq_current_mhz'] = psutil.cpu_freq().current if psutil.cpu_freq() else None
            metricas['cpu_freq_min_mhz'] = psutil.cpu_freq().min if psutil.cpu_freq() else None
            metricas['cpu_freq_max_mhz'] = psutil.cpu_freq().max if psutil.cpu_freq() else None
            metricas['cpu_times_user'] = psutil.cpu_times().user
            metricas['cpu_times_system'] = psutil.cpu_times().system
            metricas['cpu_times_idle'] = psutil.cpu_times().idle
            memoria = psutil.virtual_memory()
            metricas['memoria_total_gb'] = round(memoria.total / (1024 ** 3), 2)
            metricas['memoria_usada_gb'] = round(memoria.used / (1024 ** 3), 2)
            metricas['memoria_libre_gb'] = round(memoria.available / (1024 ** 3), 2)
            metricas['memoria_percent'] = memoria.percent
            swap = psutil.swap_memory()
            metricas['swap_total_gb'] = round(swap.total / (1024 ** 3), 2)
            metricas['swap_usado_gb'] = round(swap.used / (1024 ** 3), 2)
            metricas['swap_percent'] = swap.percent
            current_mountpoint = os.path.abspath(os.sep)
            disco = psutil.disk_usage(current_mountpoint)
            metricas['disco_total_gb'] = round(disco.total / (1024 ** 3), 2)
            metricas['disco_usado_gb'] = round(disco.used / (1024 ** 3), 2)
            metricas['disco_libre_gb'] = round(disco.free / (1024 ** 3), 2)
            metricas['disco_percent'] = disco.percent
            red = psutil.net_io_counters()
            metricas['red_bytes_enviados'] = red.bytes_sent
            metricas['red_bytes_recibidos'] = red.bytes_recv

        except Exception as e:
            logging.error(f"Error al obtener métricas del sistema: {e}")
            return None
        return metricas

    def obtener_cpu_temperatura(self):
        """
        Intenta obtener la temperatura de la CPU usando diferentes métodos en un orden de prioridad.
        1. OpenHardwareMonitor DLL (nuevo)
        2. psutil
        3. WMI (MSAcpi_ThermalZoneTemperature)
        """
        
        # Intento 1: OpenHardwareMonitor DLL
        temp_dll = self.obtener_cpu_temperatura_dll()
        if temp_dll is not None:
            return temp_dll
        logging.info("La temperatura no se pudo obtener con la DLL de OpenHardwareMonitor.")

        # Intento 2: psutil
        try:
            if hasattr(psutil, 'sensors_temperatures'):
                temps = psutil.sensors_temperatures()
                if 'coretemp' in temps:
                    for entry in temps['coretemp']:
                        if 'cpu' in entry.label.lower() or 'package id' in entry.label.lower():
                            return round(entry.current, 2)
            logging.info("La temperatura no se pudo obtener con psutil.")
        except Exception as e:
            logging.error(f"Error al obtener temperatura con psutil: {e}")

        # Intento 3: WMI con MSAcpi_ThermalZoneTemperature
        try:
            c = wmi.WMI()
            for temp_sensor in c.MSAcpi_ThermalZoneTemperature():
                temp_celsius = (temp_sensor.CurrentTemperature / 10) - 273.15
                return round(temp_celsius, 2)
            logging.info("La temperatura no se pudo obtener con WMI.")
        except Exception as e:
            logging.error(f"Error al obtener temperatura con WMI: {e}")

        # Aquí ya no incluimos los namespaces de WMI para OpenHardwareMonitor/LibreHardwareMonitor
        # porque la llamada directa a la DLL es más fiable y ya se intentó.

        return None

    def obtener_metricas_wmi(self):
        """
        Recopila métricas específicas de Windows usando la biblioteca wmi.
        """
        metricas_wmi = {}
        try:
            c = wmi.WMI()
            # Métrica: Operatoring System
            try:
                os_info = c.Win32_OperatingSystem()[0]
                metricas_wmi['os_name'] = os_info.Caption
                metricas_wmi['os_architecture'] = os_info.OSArchitecture
                metricas_wmi['os_serial_number'] = os_info.SerialNumber
                metricas_wmi['os_last_boot_up_time'] = os_info.LastBootUpTime.split('.')[0]
            except Exception as e:
                logging.error(f"Error al obtener métrica de sistema operativo: {e}")
                pass

            # Métrica: Placa Base
            try:
                board = c.Win32_BaseBoard()[0]
                metricas_wmi['placa_base_fabricante'] = board.Manufacturer
                metricas_wmi['placa_base_producto'] = board.Product
                metricas_wmi['placa_base_numero_serie'] = board.SerialNumber
            except Exception as e:
                logging.error(f"Error al obtener métrica de placa base: {e}")
                pass

            # Métrica: Procesador
            try:
                cpu_info = c.Win32_Processor()[0]
                metricas_wmi['procesador_nombre'] = cpu_info.Name.strip()
                metricas_wmi['procesador_nucleos_logicos'] = cpu_info.NumberOfLogicalProcessors
                metricas_wmi['procesador_nucleos_fisicos'] = cpu_info.NumberOfCores
            except Exception as e:
                logging.error(f"Error al obtener métrica de procesador: {e}")
                pass

            # Métrica: estado de la batería
            try:
                for battery in c.Win32_Battery():
                    metricas_wmi['bateria_porcentaje'] = f"{battery.EstimatedChargeRemaining}%"
                    metricas_wmi['bateria_estado'] = battery.BatteryStatus
                    break
            except Exception as e:
                logging.error(f"Error al obtener métrica de batería: {e}")
                pass

            # Métrica: tarjeta de red y dirección IP
            # try:
            #     for interface in c.Win32_NetworkAdapterConfiguration(IPEnabled=True):
            #         metricas_wmi['tarjeta_red_descripcion'] = interface.Description
            #         metricas_wmi['tarjeta_red_ip'] = interface.IPAddress[0] if interface.IPAddress else "N/A"
            #         break
            # except Exception as e:
            #     logging.error(f"Error al obtener métrica de tarjeta de red: {e}")
            #     pass
            
            # Obtener la temperatura de la CPU
            # temp = self.obtener_cpu_temperatura()
            # if temp is not None:
            #     metricas_wmi['cpu_temperatura_celsius'] = temp

        except Exception as e:
            logging.error(f"Error al obtener métricas de WMI: {e}")
            return None
        return metricas_wmi

    def obtener_lista_procesos(self):
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

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(PythonMonitorService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(PythonMonitorService)