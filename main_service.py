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

# Bibliotecas de monitoreo
import psutil
import wmi

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
        self.monitor_interval = 30

    def SvcStop(self):
        """
        Detiene el servicio y notifica al sistema.
        """
        self.is_running = False
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

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
        
        while self.is_running:
            try:
                # Obtiene métricas del sistema
                metricas_sistema = self.obtener_metricas_sistema()
                # Obtiene métricas de WMI
                metricas_wmi = self.obtener_metricas_wmi()
                # Obtiene la lista de procesos
                lista_procesos = self.obtener_lista_procesos()

                if metricas_sistema and metricas_wmi:
                    # Crea y registra un mensaje con las métricas del sistema
                    mensaje_sistema = (
                        f"CPU: {metricas_sistema['cpu_percent']}% | "
                        f"RAM: {metricas_sistema['memoria_percent']}% ({metricas_sistema['memoria_usada_gb']}/{metricas_sistema['memoria_total_gb']} GB) | "
                        f"Disco C: {metricas_sistema['disco_percent']}% ({metricas_sistema['disco_usado_gb']}/{metricas_sistema['disco_total_gb']} GB) | "
                        f"Red (Bytes): Enviados={metricas_sistema['red_bytes_enviados']}, Recibidos={metricas_sistema['red_bytes_recibidos']}"
                    )
                    logging.info(mensaje_sistema)
                    
                    # Crea y registra un mensaje con las métricas de WMI
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
            except Exception as e:
                logging.error(f"Error en el bucle principal: {e}")

            time.sleep(self.monitor_interval)

    def load_config(self):
        """
        Carga la configuración desde config.ini.
        """
        config = configparser.ConfigParser()
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
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
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.log_file_name)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path)
            ]
        )

    def obtener_metricas_sistema(self):
        """
        Recopila métricas clave del sistema usando la biblioteca psutil.
        """
        metricas = {}
        try:
            metricas['cpu_percent'] = psutil.cpu_percent(interval=1)
            memoria = psutil.virtual_memory()
            metricas['memoria_total_gb'] = round(memoria.total / (1024 ** 3), 2)
            metricas['memoria_usada_gb'] = round(memoria.used / (1024 ** 3), 2)
            metricas['memoria_percent'] = memoria.percent
            disco = psutil.disk_usage('C:')
            metricas['disco_total_gb'] = round(disco.total / (1024 ** 3), 2)
            metricas['disco_usado_gb'] = round(disco.used / (1024 ** 3), 2)
            metricas['disco_percent'] = disco.percent
            red = psutil.net_io_counters()
            metricas['red_bytes_enviados'] = red.bytes_sent
            metricas['red_bytes_recibidos'] = red.bytes_recv
        except Exception as e:
            logging.error(f"Error al obtener métricas del sistema: {e}")
            return None
        return metricas

    def obtener_metricas_wmi(self):
        """
        Recopila métricas específicas de Windows usando la biblioteca wmi.
        """
        metricas_wmi = {}
        try:
            c = wmi.WMI()
            for board in c.Win32_BaseBoard():
                metricas_wmi['placa_base_fabricante'] = board.Manufacturer
                metricas_wmi['placa_base_producto'] = board.Product
            for service in c.Win32_Service(Name="Spooler"):
                metricas_wmi['estado_servicio_spooler'] = service.State
            try:
                for interface in c.Win32_NetworkAdapterConfiguration(IPEnabled=True):
                    metricas_wmi['tarjeta_red_descripcion'] = interface.Description
                    metricas_wmi['tarjeta_red_ip'] = interface.IPAddress[0] if interface.IPAddress else "N/A"
                    break
            except wmi.WMIError:
                pass
            try:
                for battery in c.Win32_Battery():
                    metricas_wmi['bateria_porcentaje'] = f"{battery.EstimatedChargeRemaining}%"
                    metricas_wmi['bateria_estado'] = battery.BatteryStatus
                    break
            except wmi.WMIError:
                pass
            try:
                for temp_sensor in c.Win32_TemperatureProbe():
                    metricas_wmi['cpu_temperatura_celsius'] = temp_sensor.CurrentReading / 10
                    break
            except wmi.WMIError:
                pass
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
